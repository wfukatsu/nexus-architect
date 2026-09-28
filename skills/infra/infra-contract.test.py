#!/usr/bin/env python3
"""Contracts the /infra:* skills state in prose and nothing else enforces.

Four of them, each written because the prose can drift away from the thing it describes:

1. The bundle resolution order in rules/okf-k8s-tf-bundle.md is what
   tools/update-okf-bundle.sh actually implements, and its update path collects the public
   upstream rather than cloning a remote the bundle does not have. The rule is what a skill
   follows when it resolves by hand; the script is what it follows when it shells out. If they
   disagree, one of the two paths silently reads a different bundle.
2. Every bundle document the rule's topic map points at exists. The map is the only index a
   skill uses to decide what to open, and a row naming a file that is not there reads as
   "the bundle does not cover this".
3. Every bundle document carries a parseable `stale_after`, later than its `verified` date. The
   freshness rule is unenforceable without it, and a missing one makes a stale document look
   current. The dates move with the weekly refresh, so the rule itself must not pin them.
4. Each skill's declared model matches the Model Policy table in the router, and each template
   the skills name exists and carries the frontmatter block the output-conventions rule requires.

Usage: python3 skills/infra/infra-contract.test.py     (exit 1 on failure)
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

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

# The bundle has no origin repository; its upstream is the public documentation it cites. The
# update path must collect that and nothing else — a git clone would mean it grew a remote the
# rule and the provenance note deny, and a path to the private repositories would publish them.
k8s_update = SCRIPT.split("k8s_update() {", 1)[1].split("\n}", 1)[0]
check("the k8s-tf update path does not clone", "git clone" not in k8s_update)
check("the k8s-tf update path runs the upstream collector", "refresh-okf-k8s-tf.py" in k8s_update)
check("the rule says there is no origin repository", "There is no origin repository to pull" in RULE)
check("the rule names the upstream the collector reads", "knowledge/okf-k8s-tf-upstream/" in RULE)

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

# The dates move with every weekly refresh, so the rule must not pin them — a date written into
# the rule would be quietly wrong a week later. What must hold instead: a document is never due
# for re-verification before it was verified.
check("the rule pins no stale_after date in a table", not re.search(r"\| *20\d\d-\d\d-\d\d *\|", RULE))
backwards = []
for rel, date in dates:
    front = read("knowledge", "okf-k8s-tf", *rel.split("/")).split("---", 2)[1]
    hit = re.search(r"^verified:.*\bat:\s*[\"']?(\d{4}-\d{2}-\d{2})", front, re.M)
    if hit and date <= hit.group(1):
        backwards.append((rel, hit.group(1), date))
check("every stale_after falls after the document's verified date", not backwards, backwards)

# The weekly refresh computes which documents await re-verification; that list is worth nothing
# unless it reaches the skills that cite the bundle. `status` prints it, the router carries it
# downstream as the freshness list, and every mode skill cites a listed document with its caveat.
print("The freshness list reaches the skills that cite the bundle")

tmp = tempfile.mkdtemp()
try:
    bundle, upstream = os.path.join(tmp, "bundle"), os.path.join(tmp, "upstream")
    shutil.copytree(BUNDLE, bundle)
    helm = os.path.join(bundle, "foundation", "helm.md")
    with open(helm, encoding="utf-8") as fh:
        body = fh.read()
    with open(helm, "w", encoding="utf-8") as fh:
        fh.write(re.sub(r"^stale_after:.*$", "stale_after: 2000-01-01", body, count=1, flags=re.M))
    os.makedirs(upstream)
    with open(os.path.join(upstream, "state.json"), "w", encoding="utf-8") as fh:
        json.dump({"checked_at": "2026-09-28T14:00:00Z", "pending_as_of": "2026-09-28", "pages": {}, "releases": {},
                   "pending": {"security/kyverno.md": ["release Kyverno 1.20.0: minor behind stated 1.18 since 2026-11-10",
                                                      "past stale_after 2026-11-01"]}}, fh)
    run = subprocess.run(["bash", os.path.join(ROOT, "tools", "update-okf-bundle.sh"), "status", "--bundle=k8s-tf"],
                         env=dict(os.environ, NEXUS_OKF_K8S_TF=bundle, NEXUS_OKF_K8S_TF_UPSTREAM=upstream),
                         capture_output=True, text=True)
    out = run.stdout
    check("status runs against an overridden bundle and upstream", run.returncode == 0, run.stderr)
    check("status lists a document past its stale_after, with the date",
          re.search(r"^  foundation/helm\.md \(stale_after 2000-01-01\)$", out, re.M), out)
    check("status lists each document awaiting re-verification, with its reasons",
          re.search(r"^  security/kyverno\.md: release Kyverno 1\.20\.0: .*; past stale_after 2026-11-01$", out, re.M), out)
    check("status says as of when the list was computed", "awaiting re-verification: 1 (as of 2026-09-28" in out, out)
finally:
    shutil.rmtree(tmp)

check("the router settles the freshness list and passes it downstream",
      "freshness list" in ROUTER and "awaiting re-verification" in ROUTER
      and re.search(r"## Step 5.*freshness list", ROUTER, re.S))
for mode in ("design", "implement", "review"):
    text = read("skills", "infra", mode, "SKILL.md")
    check("/infra:%s receives the freshness list and cites a listed document with its caveat" % mode,
          "freshness list" in text and "awaits re-verification" in text)

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
