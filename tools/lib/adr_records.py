"""Validation for the Architecture Decision Records under `reports/03_design/adr/`.

Five architect design skills append records to one directory (@rules/architecture-decision-records.md),
so the contract that keeps the set coherent — one id per record equal to its file name, a
non-empty `upstream`, `supersedes` pointing at records that exist and are marked superseded, an
index that is exactly the set of records — is checked here rather than trusted to five prose
sections. A record that cites no upstream node is the defect this exists to catch: a preference
written as a decision.

Usage:  python3 tools/lib/adr_records.py <project_dir>   (exit 1 on violations)
"""

import os
import re
import sys

ADR_DIR = os.path.join("reports", "03_design", "adr")
INDEX = "index.md"
LABEL = "adr records"
ID_RE = re.compile(r"^ADR-(\d{3,})$")
FILE_RE = re.compile(r"^adr-(\d{3,})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
NODE_RE = re.compile(r"^[A-Z]+-\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
STATUSES = ("proposed", "accepted", "superseded", "deprecated")
HEADINGS = ("## Context", "## Decision", "## Alternatives considered", "## Consequences")
MAX_RECORD_BYTES = 1024 * 1024


def parse_frontmatter(text):
    """The YAML subset the frontmatter uses: `key: scalar` and `key: [a, b]`. Returns
    (dict, error); an absent or unterminated block is an error, not an empty dict."""
    if not text.startswith("---"):
        return None, "frontmatter must start with ---"
    end = text.find("\n---", 3)
    if end < 0:
        return None, "frontmatter is not terminated"
    data = {}
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            return None, "frontmatter line without a key: %r" % line
        key, _, raw = line.partition(":")
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            value = [v.strip().strip("\"'") for v in inner.split(",") if v.strip()] if inner else []
        else:
            value = raw.strip("\"'")
        data[key.strip()] = value
    return data, None


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_record(name, text):
    """(record dict or None, [errors]) for one file's content."""
    errors = []
    match = FILE_RE.match(name)
    if not match:
        errors.append("%s: file name must be adr-NNN-<kebab-slug>.md" % name)
    data, err = parse_frontmatter(text)
    if err:
        return None, errors + ["%s: %s" % (name, err)]
    record_id = data.get("id")
    if not isinstance(record_id, str) or not ID_RE.match(record_id):
        errors.append("%s: id must match ADR-###" % name)
    elif match and ID_RE.match(record_id).group(1) != match.group(1):
        errors.append("%s: id %s does not match the number in the file name" % (name, record_id))
    if str(data.get("schema_version")) != "1":
        errors.append("%s: schema_version must be 1" % name)
    for key in ("title", "skill"):
        if not _text(data.get(key)):
            errors.append("%s: %s is required" % (name, key))
    if data.get("status") not in STATUSES:
        errors.append("%s: status must be one of %s" % (name, "/".join(STATUSES)))
    if not (_text(data.get("decided_at")) and DATE_RE.match(data["decided_at"])):
        errors.append("%s: decided_at must be an ISO 8601 date" % name)
    upstream = data.get("upstream")
    if not isinstance(upstream, list) or not upstream:
        errors.append("%s: upstream must be a non-empty list — a decision that cites nothing "
                      "is a preference" % name)
    else:
        for node in upstream:
            if not NODE_RE.match(node):
                errors.append("%s: upstream entry %r is not a traceability id" % (name, node))
    supersedes = data.get("supersedes", [])
    if isinstance(supersedes, str):
        supersedes = [supersedes] if supersedes else []
    if not isinstance(supersedes, list):
        errors.append("%s: supersedes must be a list" % name)
        supersedes = []
    else:
        for old in supersedes:
            if not ID_RE.match(old):
                errors.append("%s: supersedes entry %r is not an ADR id" % (name, old))
            elif old == record_id:
                errors.append("%s: supersedes itself" % name)
    body = text[text.find("\n---", 3) + 4:]
    for heading in HEADINGS:
        if not re.search(r"^%s\s*$" % re.escape(heading), body, re.M):
            errors.append("%s: missing section %r" % (name, heading))
    data["_supersedes"] = supersedes
    data["_file"] = name
    return data, errors


def validate_directory(records, index_text):
    """Cross-record rules over (name -> text) plus the index content (None when absent)."""
    errors, parsed = [], {}
    for name in sorted(records):
        record, errs = validate_record(name, records[name])
        errors.extend(errs)
        if record is None:
            continue
        rid = record.get("id")
        if isinstance(rid, str) and ID_RE.match(rid):
            if rid in parsed:
                errors.append("%s: duplicate id %s (also %s)" % (name, rid, parsed[rid]["_file"]))
            else:
                parsed[rid] = record
    for rid, record in sorted(parsed.items()):
        for old in record["_supersedes"]:
            if old not in parsed:
                errors.append("%s: supersedes %s, which does not exist" % (record["_file"], old))
            elif parsed[old].get("status") != "superseded":
                errors.append("%s: supersedes %s, but its status is %r, not superseded"
                              % (record["_file"], old, parsed[old].get("status")))
    superseded_by = {old for r in parsed.values() for old in r["_supersedes"]}
    for rid, record in sorted(parsed.items()):
        if record.get("status") == "superseded" and rid not in superseded_by:
            errors.append("%s: status superseded but no record supersedes it" % record["_file"])

    if index_text is None:
        if parsed:
            errors.append("%s: %s is missing" % (LABEL, INDEX))
    else:
        listed = set(re.findall(r"\bADR-\d{3,}\b", index_text))
        for rid in sorted(parsed):
            if rid not in listed:
                errors.append("%s: %s is not listed" % (INDEX, rid))
        for rid in sorted(listed - set(parsed)):
            errors.append("%s: lists %s, which has no record" % (INDEX, rid))
    return parsed, errors


def load_and_validate(project_dir):
    """(records, errors); a project with no adr/ directory is (None, []) — the phase is optional."""
    path = os.path.join(project_dir, ADR_DIR)
    if not os.path.isdir(path):
        return None, []
    records, index_text, errors = {}, None, []
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if not os.path.isfile(full) or not name.endswith(".md"):
            continue
        if os.path.getsize(full) > MAX_RECORD_BYTES:
            errors.append("%s: larger than %d bytes" % (name, MAX_RECORD_BYTES))
            continue
        try:
            with open(full, encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            errors.append("%s: unreadable — %s" % (name, exc))
            continue
        if name == INDEX:
            index_text = text
        else:
            records[name] = text
    parsed, more = validate_directory(records, index_text)
    return parsed, errors + more


def main(argv):
    project_dir = argv[1] if len(argv) > 1 else "."
    records, errors = load_and_validate(project_dir)
    if records is None and not errors:
        print("no %s in %s — nothing to validate" % (LABEL, project_dir))
        return 0
    for error in errors:
        print(error)
    if errors:
        print("%d violation(s)" % len(errors))
        return 1
    print("%s are well-formed (%d records)" % (LABEL, len(records)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
