#!/usr/bin/env python3
"""The committed reference DDD document set for `samples/ec-monolith` stays valid and stays in
step with `docs/ddd-coverage.md`.

`samples/ec-monolith/expected-reports/` holds what the DDD-relevant skills produce on the sample,
committed outside the git-ignored `reports/` tree so a reader can see the document set instead of
trusting the coverage table. This suite stages it as a project (`<tmp>/reports/...`), runs every
manifest validator the toolkit has against it, runs the two output hooks on every Markdown file,
and asserts that every artifact path the coverage table cites for these techniques has a
counterpart in the set — and that nothing in the set lives at a path the table does not cite.
Exit 1 on any failure."""

import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SET = os.path.join(HERE, "expected-reports")
COVERAGE = os.path.join(ROOT, "docs", "ddd-coverage.md")

# The artifacts the coverage table cites that the reference set is expected to realise. A path
# with a placeholder (`{domain}`, `NNN-<slug>`) matches any file the placeholder admits.
CITED = [
    "reports/01_analysis/ubiquitous-language.md",
    "reports/02_spec/examples/example-map-{feat}.md",
    "reports/03_design/bounded-contexts-redesign.md",
    "reports/03_design/context-map.md",
    "reports/03_design/adr/adr-NNN-<slug>.md",
    "reports/03_design/adr/index.md",
    "reports/03_design/aggregates/aggregate-manifest.json",
    "reports/03_design/domain-event-catalog.json",
    "reports/03_design/scalardb-transaction.md",
    "reports/03_design/state-machines/state-machine-manifest.json",
    "reports/04_stories/domain-story-{domain}.md",
]
VALIDATORS = ["aggregate_manifest.py", "state_machine_manifest.py", "domain_event_catalog.py",
              "adr_records.py"]
HOOKS = ["validate-frontmatter.sh", "validate-mermaid.sh"]

checks = failures = 0


def check(label, condition, detail=""):
    global checks, failures
    checks += 1
    if condition:
        print("  ok    %s" % label)
    else:
        failures += 1
        print("  FAIL  %s%s" % (label, (" — %s" % detail) if detail else ""))


def glob_of(cited):
    return re.sub(r"\{[a-z]+\}|NNN-<slug>", "*", cited)


def files_in(root):
    out = []
    for base, _, names in os.walk(root):
        for name in sorted(names):
            out.append(os.path.relpath(os.path.join(base, name), root).replace(os.sep, "/"))
    return sorted(out)


print("The reference set exists and is cited by the coverage table")
check("expected-reports/ is present", os.path.isdir(SET))
present = ["reports/" + f for f in files_in(SET)] if os.path.isdir(SET) else []
check("it is not empty", bool(present))
with open(COVERAGE, encoding="utf-8") as handle:
    coverage = handle.read()
for cited in CITED:
    check("coverage table cites %s" % cited, "`%s`" % cited in coverage)
    matched = [p for p in present if fnmatch.fnmatch(p, glob_of(cited))]
    check("  …and the set realises it", bool(matched), "no file matches %s" % glob_of(cited))
cited_dirs = {os.path.dirname(c) for c in CITED}
strays = [p for p in present if os.path.dirname(p) not in cited_dirs and not p.endswith("README.md")]
check("every file in the set lives under a directory the table cites", not strays, strays)
check("the coverage table links to the reference set",
      "samples/ec-monolith/expected-reports" in coverage)

print("Staged as a project, every validator accepts it")
tmp = tempfile.mkdtemp()
try:
    staged = os.path.join(tmp, "reports")
    shutil.copytree(SET, staged)
    for validator in VALIDATORS:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "lib", validator), tmp],
                           capture_output=True, text=True)
        check("%s exits 0" % validator, r.returncode == 0, (r.stdout + r.stderr).strip())
        check("  …and validated something, not nothing", "nothing to validate" not in r.stdout,
              r.stdout.strip())

    print("Every Markdown file passes the two output hooks")
    md = [p for p in files_in(staged) if p.endswith(".md") and not p.endswith("README.md")]
    check("there are Markdown documents to check", bool(md))
    for hook in HOOKS:
        bad = []
        for rel in md:
            r = subprocess.run(["bash", os.path.join(ROOT, "hooks", hook), os.path.join(staged, rel)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                bad.append("%s: %s" % (rel, (r.stderr or r.stdout).strip().splitlines()[:2]))
        check("%s accepts all %d documents" % (hook, len(md)), not bad, bad)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("%d check(s), %d failure(s)" % (checks, failures))
sys.exit(1 if failures else 0)
