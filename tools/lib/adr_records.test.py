#!/usr/bin/env python3
"""Contract test for `adr_records.py` — the ADR directory rules of
@rules/architecture-decision-records.md §2–§4, each exercised with one well-formed record and
the defect it rejects. Exit 1 on any failure."""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adr_records as A  # noqa: E402

checks = failures = 0


def check(label, condition, detail=""):
    global checks, failures
    checks += 1
    if condition:
        print("  ok    %s" % label)
    else:
        failures += 1
        print("  FAIL  %s%s" % (label, (" — %s" % detail) if detail else ""))


def record(rid="ADR-001", status="accepted", upstream="[CTX-001, NFR-002]", supersedes="[]",
           body=None, skill="redesign", decided="2026-08-29", schema="1"):
    body = body if body is not None else (
        "\n## Context\n\nforces\n\n## Decision\n\nWe will.\n\n"
        "## Alternatives considered\n\n| A | why |\n|---|---|\n\n## Consequences\n\nnone\n")
    return ("---\nid: %s\ntitle: \"A decision\"\nstatus: %s\nskill: %s\ndecided_at: \"%s\"\n"
            "upstream: %s\nsupersedes: %s\nschema_version: %s\n---\n%s"
            % (rid, status, skill, decided, upstream, supersedes, schema, body))


def index(*ids):
    rows = "".join("| %s | t | accepted | redesign | 2026-08-29 | CTX-001 |\n" % i for i in ids)
    return "| ID | Title | Status | Skill | Decided | Upstream |\n|---|---|---|---|---|---|\n" + rows


def errors_of(records, index_text):
    return A.validate_directory(records, index_text)[1]


print("A well-formed directory passes")
ok = {"adr-001-context-split.md": record()}
check("one record + index → no violations", errors_of(ok, index("ADR-001")) == [],
      errors_of(ok, index("ADR-001")))
check("empty directory with no index → no violations", errors_of({}, None) == [])

print("Record shape (§2)")
for label, name, text, needle in [
    ("file name must be adr-NNN-slug", "ADR-1.md", record(), "file name"),
    ("id must match ADR-###", "adr-001-x.md", record(rid="ADR-1"), "ADR-###"),
    ("id equals the number in the file name", "adr-002-x.md", record(rid="ADR-001"), "does not match"),
    ("status is one of the four", "adr-001-x.md", record(status="done"), "status"),
    ("decided_at is a date", "adr-001-x.md", record(decided="yesterday"), "decided_at"),
    ("schema_version is 1", "adr-001-x.md", record(schema="2"), "schema_version"),
    ("upstream must be non-empty", "adr-001-x.md", record(upstream="[]"), "preference"),
    ("upstream entries are traceability ids", "adr-001-x.md", record(upstream="[the boss said so]"), "not a traceability id"),
    ("the four body headings are present", "adr-001-x.md", record(body="\n## Context\n\nx\n"), "missing section"),
    ("frontmatter must be present", "adr-001-x.md", "# no frontmatter\n", "frontmatter"),
    ("supersedes itself is rejected", "adr-001-x.md", record(supersedes="[ADR-001]"), "itself"),
]:
    errs = errors_of({name: text}, index("ADR-001"))
    check(label, any(needle in e for e in errs), errs)

print("Cross-record rules (§4)")
errs = errors_of({"adr-001-a.md": record(), "adr-002-b.md": record(rid="ADR-001")}, index("ADR-001"))
check("duplicate id across files is rejected", any("duplicate id" in e for e in errs), errs)
errs = errors_of({"adr-002-b.md": record(rid="ADR-002", supersedes="[ADR-001]")}, index("ADR-002"))
check("supersedes must name an existing record", any("does not exist" in e for e in errs), errs)
errs = errors_of({"adr-001-a.md": record(), "adr-002-b.md": record(rid="ADR-002", supersedes="[ADR-001]")},
                 index("ADR-001", "ADR-002"))
check("a superseded record must carry status superseded", any("not superseded" in e for e in errs), errs)
good = {"adr-001-a.md": record(status="superseded"),
        "adr-002-b.md": record(rid="ADR-002", supersedes="[ADR-001]")}
check("a coherent supersession chain passes", errors_of(good, index("ADR-001", "ADR-002")) == [],
      errors_of(good, index("ADR-001", "ADR-002")))
errs = errors_of({"adr-001-a.md": record(status="superseded")}, index("ADR-001"))
check("status superseded without a successor is rejected", any("no record supersedes" in e for e in errs), errs)

print("The index is a view of the directory (§3)")
errs = errors_of(ok, None)
check("index missing when records exist", any("index.md is missing" in e for e in errs), errs)
errs = errors_of(ok, index())
check("a record absent from the index", any("not listed" in e for e in errs), errs)
errs = errors_of(ok, index("ADR-001", "ADR-009"))
check("an index row with no record", any("no record" in e for e in errs), errs)

print("CLI envelope")
tmp = tempfile.mkdtemp()
try:
    check("no adr/ directory → exit 0",
          subprocess.run([sys.executable, A.__file__, tmp], capture_output=True).returncode == 0)
    adr = os.path.join(tmp, A.ADR_DIR)
    os.makedirs(adr)
    with open(os.path.join(adr, "adr-001-a.md"), "w", encoding="utf-8") as f:
        f.write(record())
    r = subprocess.run([sys.executable, A.__file__, tmp], capture_output=True, text=True)
    check("missing index → exit 1 with the violation printed", r.returncode == 1 and "index.md" in r.stdout, r.stdout)
    with open(os.path.join(adr, "index.md"), "w", encoding="utf-8") as f:
        f.write(index("ADR-001"))
    r = subprocess.run([sys.executable, A.__file__, tmp], capture_output=True, text=True)
    check("well-formed → exit 0 with a summary", r.returncode == 0 and "1 records" in r.stdout, r.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("%d check(s), %d failure(s)" % (checks, failures))
sys.exit(1 if failures else 0)
