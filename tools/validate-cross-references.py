#!/usr/bin/env python3
"""Cross-reference lint for design artifacts.

Catches the mechanical inconsistency classes that shipped as review findings once:
  1. schema-doc table counts that disagree with the tables actually defined
  2. hand-written operation totals that disagree with the OpenAPI files
  3. problem-type slugs used in OpenAPI but absent from the registry (and
     example status codes that disagree with the registry row)
  4. bare section references (e.g. "§3.1") that resolve to no heading in the
     same file (phantom self-references)
  5. singular/plural near-misses of namespace names across design docs

Usage:  validate-cross-references.py [project_root]
Exit 0 = clean, 1 = findings, 2 = cannot run.
"""

import glob
import os
import re
import sys

DESIGN = "reports/03_design"
SCHEMA_MD = os.path.join(DESIGN, "scalardb-schema.md")
REGISTRY_MD = os.path.join(DESIGN, "api-specifications", "problem-types.md")
OPENAPI_GLOB = os.path.join(DESIGN, "api-specifications", "openapi", "*.yaml")

findings = []


def finding(check, path, message):
    findings.append("[%s] %s: %s" % (check, path, message))


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


# --- 1. schema table counts -------------------------------------------------

def check_schema_counts(root):
    path = os.path.join(root, SCHEMA_MD)
    if not os.path.isfile(path):
        return set()
    text = read(path)
    # namespace summary rows: | `name` | owner | <int> |
    declared = {}
    for m in re.finditer(r"^\|\s*`([a-z_][a-z0-9_]*)`\s*\|[^|]*\|\s*(\d+)\s*\|", text, re.M):
        declared[m.group(1)] = int(m.group(2))
    # actual: "#### table" headings inside the "### ... <ns> ..." section
    sections = re.split(r"^###\s+", text, flags=re.M)
    actual = {}
    for sec in sections[1:]:
        header = sec.splitlines()[0]
        body = sec[: len(sec)]
        # stop at the next "## " top-level heading if present
        body = re.split(r"^##\s+", body, flags=re.M)[0]
        for ns in declared:
            if re.search(r"\b%s\b" % re.escape(ns), header):
                actual[ns] = len(re.findall(r"^####\s+\S+", body, flags=re.M))
                break
    for ns, count in declared.items():
        if ns in actual and actual[ns] != count:
            finding("schema-count", SCHEMA_MD,
                    "namespace '%s' declares %d tables but defines %d '####' tables"
                    % (ns, count, actual[ns]))
    return set(declared)


# --- 2. operation totals ------------------------------------------------------

def check_operation_totals(root):
    op_count = 0
    for path in glob.glob(os.path.join(root, OPENAPI_GLOB)):
        op_count += len(re.findall(r"^\s*operationId:\s*\S+", read(path), re.M))
    if op_count == 0:
        return
    for path in glob.glob(os.path.join(root, "reports", "**", "*.md"), recursive=True):
        text = read(path)
        for m in re.finditer(r"operationId\s*総数\s*(\d+)|total of\s*(\d+)\s+operationIds", text):
            stated = int(m.group(1) or m.group(2))
            if stated != op_count:
                finding("op-total", os.path.relpath(path, root),
                        "states %d operationIds but the OpenAPI files define %d"
                        % (stated, op_count))


# --- 3. problem-type slugs ----------------------------------------------------

def check_problem_types(root):
    reg_path = os.path.join(root, REGISTRY_MD)
    if not os.path.isfile(reg_path):
        return
    registry = {}  # slug -> set of statuses
    for m in re.finditer(r"^\|\s*\d+\s*\|\s*`([a-z0-9-]+)`\s*\|[^|]*\|\s*([0-9 /]+)\|",
                         read(reg_path), re.M):
        registry[m.group(1)] = set(int(s) for s in re.findall(r"\d{3}", m.group(2)))
    if not registry:
        return
    for path in glob.glob(os.path.join(root, OPENAPI_GLOB)):
        rel = os.path.relpath(path, root)
        for i, line in enumerate(read(path).splitlines(), 1):
            for m in re.finditer(r"/problems/([a-z0-9-]+)", line):
                slug = m.group(1)
                if slug == "{slug}" or "{" in slug:
                    continue
                if slug not in registry:
                    finding("problem-slug", rel,
                            "line %d uses unregistered problem type '%s'" % (i, slug))
                    continue
                sm = re.search(r"\bstatus:\s*(\d{3})\b", line)
                if sm and int(sm.group(1)) not in registry[slug]:
                    finding("problem-status", rel,
                            "line %d: example pairs '%s' with status %s but the registry row "
                            "allows %s" % (i, slug, sm.group(1),
                                           sorted(registry[slug])))


# --- 4. phantom section self-references ----------------------------------------

def check_section_refs(root):
    for path in glob.glob(os.path.join(root, "reports", "**", "*.md"), recursive=True):
        text = read(path)
        headings = set(m.group(1).rstrip(".")
                       for m in re.finditer(r"^#{2,4}\s*(\d+(?:\.\d+)*)[.\s]", text, re.M))
        if not headings:
            headings = set()
        rel = os.path.relpath(path, root)
        for i, line in enumerate(text.splitlines(), 1):
            for m in re.finditer(r"§\s*(\d+(?:\.\d+)*)", line):
                # a §-ref qualified by a file name refers to that file, not this one
                before = line[: m.start()]
                if any(tok in before for tok in
                       (".md", ".html", ".yaml", ".yml", ".json", ".graphqls",
                        "@rules", "@docs")):
                    continue
                ref = m.group(1)
                if ref not in headings and ref.split(".")[0] not in headings:
                    finding("phantom-ref", rel,
                            "line %d references §%s but no such numbered heading exists "
                            "in this file (qualify it with the target file name, or fix "
                            "the number)" % (i, ref))


# --- 5. namespace near-misses ---------------------------------------------------

def check_namespace_variants(root, namespaces):
    if not namespaces:
        return
    variants = {}
    for ns in namespaces:
        for v in {ns + "s", ns[:-1] if ns.endswith("s") else None} - {None}:
            if v not in namespaces:
                variants[v] = ns
    if not variants:
        return
    for path in glob.glob(os.path.join(root, DESIGN, "**", "*.md"), recursive=True):
        rel = os.path.relpath(path, root)
        for i, line in enumerate(read(path).splitlines(), 1):
            # only inspect a window around the word "namespace" — a service named
            # like the singular of a namespace is legitimate elsewhere on the line
            windows = []
            for kw in ("namespace", "名前空間"):
                for km in re.finditer(re.escape(kw), line):
                    windows.append(line[max(0, km.start() - 60): km.end() + 60])
            for window in windows:
                for v, ns in variants.items():
                    if re.search(r"(?<![a-z_])%s(?![a-z_-])" % re.escape(v), window):
                        finding("ns-variant", rel,
                                "line %d mentions '%s' in a namespace context but the "
                                "schema defines '%s'" % (i, v, ns))


def main(argv):
    root = argv[1] if len(argv) > 1 else "."
    if not os.path.isdir(os.path.join(root, "reports")):
        print("validate-cross-references: no reports/ under %s" % root, file=sys.stderr)
        return 2
    namespaces = check_schema_counts(root)
    check_operation_totals(root)
    check_problem_types(root)
    check_section_refs(root)
    check_namespace_variants(root, namespaces)
    for f in findings:
        print(f, file=sys.stderr)
    if findings:
        print("validate-cross-references: %d finding(s)" % len(findings), file=sys.stderr)
        return 1
    print("validate-cross-references: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
