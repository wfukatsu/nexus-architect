#!/usr/bin/env python3
"""Contract test for hooks/hooks.json and the once-per-tool-call guard.

Two things here are otherwise only observable in a live session:

* what hooks.json asks Claude Code for — matchers that name tools that still exist, the
  frontmatter validator filtered to reports/ by `if` (one handler per tool: an `if` rule matches
  one tool's calls), the recorder in the background after a tool call and waiting at Stop;
* that the copies of a hook the four plugins each register do the work once per tool call.

Exit 1 on failure.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
failures = 0
checks = 0


def check(label, condition, detail=""):
    global failures, checks
    checks += 1
    print("  [%s] %s%s" % ("ok" if condition else "FAIL", label,
                           " — " + str(detail) if detail and not condition else ""))
    if not condition:
        failures += 1


with open(os.path.join(HERE, "hooks.json"), encoding="utf-8") as fh:
    HOOKS = json.load(fh)["hooks"]

print("hooks.json")

post = HOOKS["PostToolUse"]
names = set()
for group in post:
    names |= set(group["matcher"].split("|"))
check("matchers name only tools that exist", names <= {"Write", "Edit", "Agent"}, sorted(names))


def handlers(script, event="PostToolUse"):
    return [(g.get("matcher", ""), h) for g in HOOKS[event] for h in g["hooks"]
            if script in h["command"]]


front = handlers("validate-frontmatter.sh")
check("the frontmatter validator is filtered to reports/ for each tool it matches",
      sorted(m for m, _ in front) == ["Edit", "Write"]
      and all(h.get("if") == "%s(**/reports/**)" % m for m, h in front), front)
mermaid = handlers("validate-mermaid.sh")
# It validates every Markdown file, wherever it is written, so it carries no path filter.
check("the Mermaid validator runs on every Write and Edit, unfiltered",
      [m for m, _ in mermaid] == ["Write|Edit"] and "if" not in mermaid[0][1], mermaid)
check("no validator runs in the background (exit 2 has to reach the model)",
      not any(h.get("async") for _, h in front + mermaid))
rec = handlers("record_token_usage.py")
check("the recorder follows Write, Edit and Agent in the background",
      [m for m, _ in rec] == ["Write|Edit|Agent"] and rec[0][1].get("async") is True, rec)
# `claude -p` kills a background hook still running at teardown; the turn-end firing is the one
# that flushes the pending bucket, so it has to finish.
check("the recorder waits at Stop and SubagentStop",
      all(len(handlers("record_token_usage.py", e)) == 1
          and not handlers("record_token_usage.py", e)[0][1].get("async")
          for e in ("Stop", "SubagentStop")))

print("One copy per tool call")

with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, TMPDIR=os.path.join(tmp, "t"))
    os.makedirs(env["TMPDIR"])
    reports = os.path.join(tmp, "reports")
    os.makedirs(reports)
    bad = os.path.join(reports, "bad.md")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("no frontmatter\n\n```mermaid\nnot-a-diagram\n```\n")

    def fire(script, tool_use_id, runner=("bash",), extra=None, env=env):
        event = {"hook_event_name": "PostToolUse", "tool_name": "Write",
                 "tool_input": {"file_path": bad}}
        if tool_use_id:
            event["tool_use_id"] = tool_use_id
        event.update(extra or {})
        return subprocess.run(list(runner) + [os.path.join(HERE, script)], env=env,
                              input=json.dumps(event), capture_output=True, text=True)

    for script in ("validate-frontmatter.sh", "validate-mermaid.sh"):
        codes = [fire(script, "toolu_A").returncode for _ in range(4)]
        check("%s: four copies of one call report once" % script, codes == [2, 0, 0, 0], codes)
        check("%s: the next call is validated again" % script,
              fire(script, "toolu_B").returncode == 2)
        codes = [fire(script, None).returncode for _ in range(2)]
        check("%s: without an id every copy runs" % script, codes == [2, 2], codes)
    check("an id cannot leave the marker directory",
          fire("validate-frontmatter.sh", "../../x").returncode == 2
          and sorted(os.listdir(tmp)) == ["reports", "t"], os.listdir(tmp))

    blocked = os.path.join(tmp, "blocked")
    with open(blocked, "w") as fh:          # a file where the directory would go: mkdir -p fails
        fh.write("")
    nowhere = dict(env, TMPDIR=os.path.join(blocked, "nested"))
    codes = [fire("validate-frontmatter.sh", "toolu_C", env=nowhere).returncode for _ in range(2)]
    check("with nowhere to write a marker every copy runs", codes == [2, 2], codes)

    # The recorder, on a project it is not inert for.
    proj = os.path.join(tmp, "proj")
    os.makedirs(os.path.join(proj, "work"))
    with open(os.path.join(proj, "work", "pipeline-progress.json"), "w") as fh:
        json.dump({"phases": {}}, fh)
    transcript = os.path.join(tmp, "transcript.jsonl")
    with open(transcript, "w") as fh:
        fh.write("")
    markers = os.path.join(env["TMPDIR"], "nexus-architect-hooks")
    ctx = {"cwd": proj, "transcript_path": transcript, "session_id": "s"}

    def recorder_markers():
        return sorted(n for n in os.listdir(markers) if n.startswith("record_token_usage-"))

    runs = [fire("record_token_usage.py", "toolu_R", ("python3",), ctx) for _ in range(3)]
    check("the recorder never fails the session", all(r.returncode == 0 for r in runs))
    check("the recorder claims one marker per tool call",
          recorder_markers() == ["record_token_usage-toolu_R"], recorder_markers())
    fire("record_token_usage.py", "toolu_S", ("python3",), dict(ctx, cwd=tmp))
    check("outside a pipeline project the recorder writes no marker",
          recorder_markers() == ["record_token_usage-toolu_R"], recorder_markers())

print()
print("%d check(s), %d failure(s)" % (checks, failures))
sys.exit(1 if failures else 0)
