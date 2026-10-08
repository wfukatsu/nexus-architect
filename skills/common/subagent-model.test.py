#!/usr/bin/env python3
"""Contract test: every sub-agent call a skill spells out names its model.

A sub-agent does not inherit the model of the skill that spawned it and does not pick up the
`model` of a skill it invokes; with none on the call it runs on the user's sub-agent default
(measured on Claude Code v2.1.293 — skills/common/sub-agent-patterns.md § Always pass `model`).
The tier a phase is assigned therefore reaches its sub-agents only if each call states it.

Checked: every `subagent_type` in a SKILL.md is followed, in the same call, by a `model` equal to
that skill's own frontmatter `model`; the shared pattern library writes the placeholder
`{phase_model}` on every pattern; and an orchestrator runs its phases as sub-agents on the
manifest's model — the placeholder again, which only an orchestrator may write, since inline a
phase would run on the orchestrator's own model whatever tier it is assigned. Exit 1 on failure.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
failures = 0
checks = 0


def check(label, condition, detail=""):
    global failures, checks
    checks += 1
    print("  [%s] %s%s" % ("ok" if condition else "FAIL", label,
                           " — " + str(detail) if detail and not condition else ""))
    if not condition:
        failures += 1


# The call's model sits on the same line or the next one, in any of the corpus's three spellings
# (`model: "x"` in a block or in backticks, `model="x"` in the pattern library).
MODEL_AFTER = re.compile(r'subagent_type\s*[:=]\s*"[A-Za-z-]+"`?,\s*`?model\s*[:=]\s*"([^"]+)"')

# Skills that run other skills' phases. Their phase call takes its model from the manifest, so the
# placeholder is right there and wrong anywhere else.
ORCHESTRATORS = {os.path.join("skills", "pipeline", "SKILL.md")}

skills = []
for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "skills")):
    if "SKILL.md" in files:
        skills.append(os.path.join(dirpath, "SKILL.md"))

print("Sub-agent calls in skills")

missing, wrong, calls, phase_calls = [], [], 0, {}
for path in sorted(skills):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if "subagent_type" not in text:
        continue
    tier = re.search(r"^model:\s*(\w+)", text.split("---", 2)[1], re.M)
    rel = os.path.relpath(path, ROOT)
    for m in re.finditer(r"subagent_type", text):
        calls += 1
        line = text.count("\n", 0, m.start()) + 1
        found = MODEL_AFTER.match(text, m.start())
        if not found:
            missing.append("%s:%d" % (rel, line))
        elif found.group(1) == "{phase_model}" and rel in ORCHESTRATORS:
            phase_calls.setdefault(rel, []).append(line)
        elif not tier or found.group(1) != tier.group(1):
            wrong.append("%s:%d names %s, the skill is %s" % (
                rel, line, found.group(1), tier.group(1) if tier else "undeclared"))
check("the corpus spells out sub-agent calls (found %d)" % calls, calls > 0)
check("every call names a model", not missing, missing)
check("the model is the calling skill's own tier", not wrong, wrong)

print("Orchestrators")

for rel in sorted(ORCHESTRATORS):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        text = fh.read()
    check("%s runs its phases as sub-agents on the manifest's model" % rel, rel in phase_calls)
    check("%s tells the phase it cannot ask the user, and where an unasked question goes" % rel,
          "cannot ask the user" in text and "open-questions.md" in text and "`unasked`" in text)
    check("%s keeps the progress registry to itself" % rel,
          "Do not write this phase's entry in work/pipeline-progress.json" in text)

print("The shared pattern library")

with open(os.path.join(ROOT, "skills", "common", "sub-agent-patterns.md"), encoding="utf-8") as fh:
    patterns = fh.read()
starts = [m.start() for m in re.finditer(r"subagent_type", patterns)]
bare = [patterns.count("\n", 0, s) + 1 for s in starts
        if (MODEL_AFTER.match(patterns, s) or [None, None])[1] != "{phase_model}"]
check("every pattern passes {phase_model} (found %d)" % len(starts), starts and not bare, bare)

print()
print("%d check(s), %d failure(s)" % (checks, failures))
sys.exit(1 if failures else 0)
