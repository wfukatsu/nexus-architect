#!/usr/bin/env python3
"""The eval cases stay loadable, offline.

The evals run on demand and cost money (tools/eval-plugin.sh), so a case broken by a renamed skill
would go unnoticed until someone next paid for a run. This checks what can be checked without a model.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"

failures = []
checks = 0


def check(ok, message):
    global checks
    checks += 1
    if not ok:
        failures.append(message)


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, text
    head, sep, body = text[4:].partition("\n---\n")
    return (head, body) if sep else (None, text)


import json

with open(ROOT / ".claude-plugin" / "marketplace.json", encoding="utf-8") as fh:
    OWNED = {entry["name"]: {Path(skill).as_posix().removeprefix("./") for skill in entry["skills"]}
             for entry in json.load(fh)["plugins"]}

cases = sorted(p.parent for p in EVALS.rglob("prompt.md") if "results" not in p.parts)
check(cases, "no eval case found under evals/")
covered = set()

for case in cases:
    rel = case.relative_to(ROOT)
    head, body = frontmatter(case / "prompt.md")
    check(head is not None, f"{rel}/prompt.md has no frontmatter")
    check(body.strip() and "TODO" not in body, f"{rel}/prompt.md has no prompt")

    # tools/eval-plugin.sh runs a plugin's cases by tag; a case with no plugin tag never runs.
    tags = re.search(r"^tags:\s*\[(.*)\]", head or "", re.M)
    plugins = [t.strip() for t in (tags.group(1).split(",") if tags else []) if t.strip() in OWNED]
    check(len(plugins) == 1, f"{rel}/prompt.md: tag exactly one plugin, found {plugins}")
    covered.update(plugins)
    # The runner stages the plugin; a path written here would point the case somewhere else.
    check(not re.search(r"^plugins:", head or "", re.M), f"{rel}/prompt.md sets `plugins`")

    # The prompt is a user's request: it must not name the command it is meant to reach.
    check(not re.search(r"/(architect|scalardb|product|infra):", body),
          f"{rel}/prompt.md names a slash command")

    graders = sorted((case / "graders").glob("*.md"))
    check(graders, f"{rel} has no grader")
    for grader in graders:
        ghead, _ = frontmatter(grader)
        check(ghead and re.search(r"^type:\s*\S+", ghead, re.M), f"{grader.relative_to(ROOT)} has no type")
        if grader.name != "skill-fired.md":
            continue
        named = re.search(r'"([a-z]+):([a-z0-9-]+)(?:\(\?:([a-z0-9|-]+)\))?"\'\s*$', ghead or "", re.M)
        check(named, f"{grader.relative_to(ROOT)}: input_match names no `<plugin>:<skill>`")
        if named:
            plugin, stem, alternatives = named.groups()
            check(plugins == [plugin], f"{grader.relative_to(ROOT)}: expects {plugin}:, the case is tagged {plugins}")
            registered = {path.rsplit("/", 1)[-1] for path in OWNED.get(plugin, ())}
            # `migrate-(?:database|oracle)` — any of several skills is a right answer.
            for skill in ([stem + a for a in alternatives.split("|")] if alternatives else [stem]):
                check(skill in registered,
                      f"{grader.relative_to(ROOT)}: {plugin} registers no skill named {skill}")

check(covered == set(OWNED), f"no case for: {sorted(set(OWNED) - covered)}")

if failures:
    print(f"FAIL: {len(failures)} of {checks} checks")
    for message in failures:
        print(f"  - {message}")
    sys.exit(1)
print(f"PASS: {checks} checks over {len(cases)} eval cases")
