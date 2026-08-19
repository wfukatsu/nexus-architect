#!/usr/bin/env python3
"""Contracts the /infra:* skills state in prose and nothing else enforces.

Four of them, each written because the prose can drift away from the thing it describes:

1. The bundle resolution order in rules/okf-k8s-tf-bundle.md is what
   tools/update-okf-bundle.sh actually implements. The rule is what a skill follows when it
   resolves by hand; the script is what it follows when it shells out. If they disagree, one of
   the two paths silently reads a different bundle.
2. Every bundle document the rule's topic map points at exists. The map is the only index a
   skill uses to decide what to open, and a row naming a file that is not there reads as
   "the bundle does not cover this".
3. Every bundle document carries a parseable `stale_after`. The freshness rule is unenforceable
   without it, and a missing one makes a stale document look current.
4. Each skill's declared model matches the Model Policy table in the router, and each template
   the skills name exists and carries the frontmatter block the output-conventions rule requires.

Usage: python3 skills/infra/infra-contract.test.py     (exit 1 on failure)
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUNDLE = os.path.join(ROOT, "knowledge", "okf-k8s-tf")

failures = 0
checks = 0


def check(label, condition, detail=""):
    global failures, checks
    checks += 1
    print("  [%s] %s%s" % ("ok" if condition else "FAIL", label,
                           " — " + str(detail) if detail and not condition else ""))
    if not condition:
        failures += 1


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


RULE = read("rules", "okf-k8s-tf-bundle.md")
SCRIPT = read("tools", "update-okf-bundle.sh")
ROUTER = read("skills", "infra", "start", "SKILL.md")

# ------------------------------------------------------------ resolution order

print("The documented bundle resolution order is the one the script implements")

# The rule's table names the three locations in order; the script's k8s_resolve loop lists the
# same three as shell words. Compare the sequence, not the spelling.
rule_order = re.findall(r"\| [123] \| `([^`]+)`", RULE)
resolve_body = SCRIPT.split("k8s_resolve() {", 1)[1].split("}", 1)[0]
# Only the `for d in ...` header names the locations; "$d" inside the body is the loop variable.
loop_header = resolve_body.split("for d in", 1)[1].split("; do", 1)[0]
script_order = re.findall(r'"\$(\w+)"', loop_header)

check("the rule lists three resolution steps", len(rule_order) == 3, rule_order)
check("the script tries three locations", len(script_order) == 3, script_order)
check("step 1 is the user override",
      "NEXUS_OKF_K8S_TF" in rule_order[0] and script_order[0] == "K8S_OVERRIDE",
      (rule_order[:1], script_order[:1]))
check("step 2 is the vendored copy",
      "knowledge/okf-k8s-tf" in rule_order[1] and script_order[1] == "K8S_VENDORED",
      (rule_order[1:2], script_order[1:2]))
check("step 3 is the cache",
      ".cache" in rule_order[2] and script_order[2] == "K8S_CACHE",
      (rule_order[2:], script_order[2:]))

# The bundle has no remote; a script that grew a fetch path would contradict the rule and the
# provenance note without anything else noticing.
check("the k8s-tf update path does not fetch",
      "git clone" not in SCRIPT.split("k8s_update() {", 1)[1].split("\n}", 1)[0])
check("the rule says there is no remote", "There is no remote" in RULE)

# ------------------------------------------------------------------ topic map

print("Every document the topic map points at exists")

mapped = set(re.findall(r"\| `([a-z-]+/[a-z0-9-]+\.md)` \|", RULE))
check("the topic map is not empty", len(mapped) >= 14, len(mapped))
missing = sorted(p for p in mapped if not os.path.isfile(os.path.join(BUNDLE, p)))
check("every mapped document exists in the bundle", not missing, missing)

# The other direction: a document nobody can find is a document nobody reads.
present = set()
for dirpath, _, files in os.walk(BUNDLE):
    for f in files:
        rel = os.path.relpath(os.path.join(dirpath, f), BUNDLE)
        if f.endswith(".md") and "/" in rel and f != "index.md":
            present.add(rel)
unmapped = sorted(present - mapped)
check("every bundle document is reachable from the topic map", not unmapped, unmapped)

# ------------------------------------------------------------------ freshness

print("Freshness metadata is present and parseable")

undated = []
dates = []
for rel in sorted(present):
    front = read("knowledge", "okf-k8s-tf", *rel.split("/")).split("---", 2)
    hit = re.search(r"^stale_after:\s*[\"']?(\d{4}-\d{2}-\d{2})", front[1] if len(front) > 2 else "", re.M)
    (dates.append((rel, hit.group(1))) if hit else undated.append(rel))
check("every bundle document carries a parseable stale_after", not undated, undated)

# The rule states Kyverno's date is the earliest, and the reason. If another document ever became
# the earliest, the rule's table would be quietly wrong.
if dates:
    earliest = min(d for _, d in dates)
    owners = sorted(rel for rel, d in dates if d == earliest)
    check("the rule names the earliest stale_after", earliest in RULE, earliest)
    check("kyverno is the earliest-expiring document", owners == ["security/kyverno.md"], owners)

# ------------------------------------------------------------- skills & models

print("Skill models and templates match what the router documents")

SKILLS = ("start", "design", "implement", "review")
policy = dict(re.findall(r"\| `/infra:(\w+)` \| (opus|sonnet|haiku) \|", ROUTER))
check("the router documents a model for all four skills",
      set(policy) == set(SKILLS), sorted(policy))

for name in SKILLS:
    body = read("skills", "infra", name, "SKILL.md")
    front = body.split("---", 2)[1]
    declared = re.search(r"^model:\s*(\w+)", front, re.M)
    check("%s declares a model" % name, bool(declared))
    if declared and name in policy:
        check("%s model matches the router's table" % name, declared.group(1) == policy[name],
              "%s vs %s" % (declared.group(1), policy[name]))
    check("%s is user-invocable" % name, "user_invocable: true" in front)

print("Templates the skills name exist and carry the frontmatter block")

named = set()
for name in SKILLS:
    named |= set(re.findall(r"templates/infra/([a-z-]+\.md)", read("skills", "infra", name, "SKILL.md")))
check("the skills name at least three templates", len(named) >= 3, sorted(named))
for tpl in sorted(named):
    path = os.path.join(ROOT, "templates", "infra", tpl)
    check("templates/infra/%s exists" % tpl, os.path.isfile(path))
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        # Outputs land under reports/, where the frontmatter hook is blocking — so the template
        # has to hand the writer a frontmatter block, not just a heading.
        check("templates/infra/%s carries a schema_version frontmatter block" % tpl,
              "schema_version: 1" in text and "```yaml" in text)

print()
print("%d check(s), %d failure(s)" % (checks, failures))
sys.exit(1 if failures else 0)
