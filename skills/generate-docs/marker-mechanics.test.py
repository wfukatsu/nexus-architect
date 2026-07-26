#!/usr/bin/env python3
"""Executable check of the /architect:generate-docs ownership-marker contract.

SKILL.md states the marker rules in prose; this asserts them as behaviour, so a
later edit to the skill cannot quietly break re-run safety.

    python3 skills/generate-docs/marker-mechanics.test.py            # embedded fixture
    python3 skills/generate-docs/marker-mechanics.test.py FILE.md    # a real README

Exit status 0 = all checks pass, 1 = at least one failed (same convention as
hooks/*.sh in CLI mode).
"""
import hashlib
import re
import sys

def _stable_from_skill():
    """Parse the stable key list from SKILL.md so the contract has one source.

    Falls back to the known list if SKILL.md is not present (e.g. the test file
    copied elsewhere), so the mechanics checks still run.
    """
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SKILL.md")
    fallback = {"overview", "build-and-run", "configuration", "layout", "api",
                "operations", "traceability", "findings"}
    try:
        text = open(path).read()
    except OSError:
        return fallback
    m = re.search(r"Section keys are stable \(([^)]+)\)", text)
    if not m:
        raise AssertionError(
            "SKILL.md no longer contains the 'Section keys are stable (...)' "
            "sentence — update this parser together with the contract")
    keys = set(re.findall(r"`([a-z-]+)`", m.group(1)))
    if not keys:
        raise AssertionError("parsed an empty stable key list from SKILL.md")
    return keys


STABLE = _stable_from_skill()

BEGIN = "<!-- nexus:begin:{k} -->"
END = "<!-- nexus:end:{k} -->"

FIXTURE = """# Example Service

Hand-written intro that the skill must never touch.

<!-- nexus:begin:overview -->
## Overview

Generated overview body.
<!-- nexus:end:overview -->

## Hand-written section

- a human bullet
- another human bullet

<!-- nexus:begin:layout -->
## Layout

| Path | Content |
|------|---------|
| `src/` | source |
<!-- nexus:end:layout -->

## Notes

Closing hand-written prose.

<!-- nexus:begin:findings -->
## Findings

1. drift recorded, not resolved in prose
<!-- nexus:end:findings -->
"""


# --- mechanics, implemented exactly as SKILL.md specifies -------------------

def regions(text):
    """key -> (start, end) spanning the markers inclusive."""
    out = {}
    for m in re.finditer(r"<!-- nexus:begin:([a-z-]+) -->", text):
        key = m.group(1)
        e = text.find(END.format(k=key), m.end())
        if e == -1:
            raise AssertionError(f"unpaired begin marker: {key}")
        out[key] = (m.start(), e + len(END.format(k=key)))
    return out


def outside_text(text):
    """Everything not inside a marked region — the human-authored part."""
    keep, prev = [], 0
    for s, e in sorted(regions(text).values()):
        keep.append(text[prev:s])
        prev = e
    keep.append(text[prev:])
    return "".join(keep)


def update_region(text, key, body):
    if key not in STABLE:
        raise ValueError(f"unstable key refused: {key}")
    s, e = regions(text)[key]
    block = f"{BEGIN.format(k=key)}\n{body}\n{END.format(k=key)}"
    return text[:s] + block + text[e:]


def remove_region(text, key):
    """Region + the single blank line after it (at EOF, the one before it)."""
    if key not in STABLE:
        raise ValueError(f"unstable key refused: {key}")
    s, e = regions(text)[key]
    if text[e:e + 2] == "\n\n":
        return text[:s] + text[e + 2:]
    m = re.search(r"\n\n$", text[:s])
    if m:
        s = m.start() + 1
    return text[:s] + text[e:]


def insert_before(text, key, body, anchor):
    i = text.find(anchor)
    if i == -1:
        raise AssertionError(f"anchor not found: {anchor!r}")
    block = f"{BEGIN.format(k=key)}\n{body}\n{END.format(k=key)}"
    return text[:i] + block + "\n\n" + text[i:]


def append_region(text, key, body):
    block = f"{BEGIN.format(k=key)}\n{body}\n{END.format(k=key)}"
    return text.rstrip("\n") + "\n\n" + block + "\n"


def body_of(text, key):
    s, e = regions(text)[key]
    return text[s:e].split("\n", 1)[1].rsplit("\n", 1)[0]


def h(t):
    return hashlib.md5(t.encode()).hexdigest()[:12]


# --- checks ----------------------------------------------------------------

def main(argv):
    if len(argv) > 1:
        src = open(argv[1]).read()
        label = argv[1]
    else:
        src = FIXTURE
        label = "embedded fixture"
    orig = src.rstrip("\n") + "\n"

    keys = sorted(regions(orig))
    if len(keys) < 2:
        print(f"need at least 2 marked regions to test, found {keys}")
        return 1
    first, last = keys[0], sorted(regions(orig).items(), key=lambda kv: kv[1][0])[-1][0]

    fails = []

    def check(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
        if not cond:
            fails.append(name)

    print(f"fixture: {label} ({len(orig.splitlines())} lines, md5 {h(orig)})")
    print(f"regions: {keys}\n")

    print("A. update in place")
    upd = update_region(orig, first, "REGENERATED")
    check("human prose outside markers is byte-identical",
          outside_text(upd) == outside_text(orig))
    check("no region duplicated", len(regions(upd)) == len(regions(orig)))
    check("region set unchanged", sorted(regions(upd)) == keys)
    check("only the targeted region changed",
          all(orig[slice(*regions(orig)[k])] == upd[slice(*regions(upd)[k])]
              for k in keys if k != first))

    print("\nB. idempotency")
    once = update_region(orig, first, "SAME")
    check("second application is a no-op",
          once == update_region(once, first, "SAME"), f"md5 {h(once)}")

    print("\nC. removal")
    rm = remove_region(orig, last)
    check("region gone", f"nexus:begin:{last}" not in rm)
    check("no orphan end marker", f"nexus:end:{last}" not in rm)
    # Whitespace byte-identity cannot hold: removing an EOF-adjacent region also
    # removes its separator blank line, by design. Content is the invariant here;
    # byte-level stability is proven by the round-trip in E.
    check("human prose content still identical",
          [l for l in outside_text(rm).splitlines() if l.strip()] ==
          [l for l in outside_text(orig).splitlines() if l.strip()])
    check("other regions untouched",
          sorted(regions(rm)) == [k for k in keys if k != last])

    print("\nD. unknown-key protection")
    injected = orig.replace(
        BEGIN.format(k=first),
        "<!-- nexus:begin:handwritten -->\nHUMAN BLOCK\n<!-- nexus:end:handwritten -->\n\n"
        + BEGIN.format(k=first), 1)
    for op, fn in (("update", update_region), ("removal", remove_region)):
        try:
            fn(injected, "handwritten", "X") if fn is update_region else fn(injected, "handwritten")
            check(f"{op} refuses non-stable key", False)
        except ValueError:
            check(f"{op} refuses non-stable key", True)
    check("non-stable region survives an unrelated update",
          "HUMAN BLOCK" in update_region(injected, first, "Y"))

    print("\nE. round-trip stability (insert and remove are inverses)")
    mid = keys[0] if keys[0] != last else keys[1]
    mid_body = body_of(orig, mid)
    anchor = orig[regions(orig)[mid][1]:].lstrip("\n").split("\n", 1)[0]
    back = insert_before(remove_region(orig, mid), mid, mid_body, anchor)
    check("mid-file region: remove -> insert is byte-identical", back == orig)

    last_body = body_of(orig, last)
    check("EOF region: remove -> append is byte-identical",
          append_region(remove_region(orig, last), last, last_body) == orig)

    t = orig
    for _ in range(5):
        t = append_region(remove_region(t, last), last, last_body)
    check("5 remove/append cycles produce no drift", t == orig)

    check("no run of 2+ blank lines", "\n\n\n" not in orig)
    check("file ends with exactly one newline",
          orig.endswith("\n") and not orig.endswith("\n\n"))

    print("\n" + ("ALL PASS" if not fails else f"FAILED ({len(fails)}): {fails}"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
