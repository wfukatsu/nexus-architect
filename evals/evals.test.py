#!/usr/bin/env python3
"""The eval cases stay loadable, offline.

`claude plugin eval` runs on demand and costs money, so a case broken by a renamed skill would go
unnoticed until someone next paid for a run. This checks what can be checked without a model.
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


cases = sorted(p.parent for p in EVALS.rglob("prompt.md") if "results" not in p.parts)
check(cases, "no eval case found under evals/")

for case in cases:
    rel = case.relative_to(ROOT)
    head, body = frontmatter(case / "prompt.md")
    check(head is not None, f"{rel}/prompt.md has no frontmatter")
    check(body.strip() and "TODO" not in body, f"{rel}/prompt.md has no prompt")

    # A path target finds no plugin here on its own (no plugin.json), and then nothing loads.
    plugins = re.search(r'^plugins:\s*\["([^"]+)"\]', head or "", re.M)
    check(plugins and (case / plugins.group(1)).resolve() == ROOT,
          f"{rel}/prompt.md: `plugins` must point at the repository root")

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
        named = re.search(r'\)\?([a-z0-9-]+)"\'\s*$', ghead or "", re.M)
        check(named, f"{grader.relative_to(ROOT)}: input_match names no skill")
        if named:
            check((ROOT / "skills" / named.group(1) / "SKILL.md").is_file(),
                  f"{grader.relative_to(ROOT)}: skills/{named.group(1)}/SKILL.md does not exist")

if failures:
    print(f"FAIL: {len(failures)} of {checks} checks")
    for message in failures:
        print(f"  - {message}")
    sys.exit(1)
print(f"PASS: {checks} checks over {len(cases)} eval cases")
