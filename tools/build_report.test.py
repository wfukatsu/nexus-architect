#!/usr/bin/env python3
"""Contract suite for tools/build-report.py — the generator behind /architect:report.

The report is the one artifact a reader sees instead of the report tree, so the things that
must not break are the ones a casual eyeball would miss: a Mermaid fence silently mangled by
the Markdown converter, an anchor that no longer resolves, a duplicated article id, a section
heading that stayed English in a Japanese project, and a run that crashes on a project whose
review has not happened yet.

A scratch project is built in a temp directory, the tool is run against it, and the emitted
HTML is asserted directly. No network, no services, no fixtures on disk.
"""
import html as html_mod
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "build-report.py")

failures = []
checks = 0


def check(label, condition, detail=""):
    global checks
    checks += 1
    if condition:
        print("  ok   %s" % label)
    else:
        failures.append(label)
        print("  FAIL %s%s" % (label, ("\n         %s" % detail) if detail else ""))


# The Mermaid source under test. It carries the two things that break naive escaping: an HTML
# tag inside a node label, and brace-delimited node syntax that a format string would eat.
MERMAID_SRC = """flowchart TD
    A[Order<br/>Placed] --> B{Payment authorized?}
    B -->|yes| C[Ship]
    B -->|no| D[Cancel & notify]"""

DOC_A = """---
title: "System Overview"
schema_version: 1
---

## Context

The service template is `order-{tenant}-svc` and the retry budget is `{max: 3}` — braces in
prose must survive verbatim.

```mermaid
%s
```

See [the data model](../03_design/data-model.md) for the schema.
""" % MERMAID_SRC

DOC_B = """---
title: "Data Model"
schema_version: 1
---

## Entities

| Entity | Key |
|--------|-----|
| Order  | order_id |
"""

ADR_INDEX = """---
title: "ADR Index"
schema_version: 1
---

| ID | Title |
|----|-------|
| ADR-001 | Consensus Commit as the transaction manager |
"""

ADR_001 = """---
title: "ADR-001: Consensus Commit as the transaction manager"
schema_version: 1
---

## Decision

Use Consensus Commit.
"""

AGGREGATE = """---
title: "Aggregate: Order"
schema_version: 1
---

## Invariants

An order total never goes negative.
"""

FEATURE = """Feature: Place an order
  Scenario: Payment is authorized
    Given a cart with 2 items
    When the customer confirms
    Then the order is placed
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def build_project(root, language):
    """A scratch project with no review synthesis — the 'review not yet run' shape."""
    write(os.path.join(root, "work", "pipeline-progress.json"), json.dumps({
        "$schema": "progress-registry-v1",
        "project_name": "scratch-project",
        "target_path": "./scratch",
        "options": {"scalardb_enabled": True, "workflow_type": "greenfield",
                    "output_language": language},
        "phases": {},
    }, indent=2))
    write(os.path.join(root, "work", "context.md"),
          "## Open Questions\n\n"
          "| ID | Question | Status | Owner |\n|----|----------|--------|-------|\n"
          "| OQ-001 | What is the p95 latency target? | deferred | product owner |\n"
          "| OQ-002 | Which tenant isolation model? | answered | architect |\n")
    write(os.path.join(root, "reports", "01_analysis", "system-overview.md"), DOC_A)
    write(os.path.join(root, "reports", "03_design", "data-model.md"), DOC_B)
    write(os.path.join(root, "reports", "03_design", "adr", "index.md"), ADR_INDEX)
    write(os.path.join(root, "reports", "03_design", "adr", "adr-001-consensus-commit.md"),
          ADR_001)
    write(os.path.join(root, "reports", "03_design", "aggregates", "aggregate-order.md"),
          AGGREGATE)
    # A manifest that must never be rendered.
    write(os.path.join(root, "reports", "03_design", "aggregates", "aggregate-manifest.json"),
          json.dumps({"aggregates": [{"id": "AGG-001", "root": "Order"}]}))
    write(os.path.join(root, "reports", "07_test-specs", "bdd-scenarios", "order.feature"),
          FEATURE)


def run(project_dir, output):
    return subprocess.run(
        [sys.executable, TOOL, project_dir, "--output", output],
        capture_output=True, text=True)


tmp = tempfile.mkdtemp(prefix="build-report-test-")
try:
    # ------------------------------------------------------------- English project
    print("A project whose review has not run yet still produces a complete report")

    en_dir = os.path.join(tmp, "en")
    build_project(en_dir, "en")
    out = os.path.join(tmp, "en-report.html")
    proc = run(en_dir, out)

    check("exit 0 on a well-formed project", proc.returncode == 0,
          proc.stderr.strip() or proc.stdout.strip())
    check("the output file was written", os.path.exists(out))
    doc = open(out, encoding="utf-8").read() if os.path.exists(out) else ""

    # --- article identity -----------------------------------------------------
    ids = re.findall(r'<article class="doc" id="([^"]+)"', doc)
    expected = {"system-overview", "data-model", "index", "adr-001-consensus-commit",
                "aggregate-order", "feature-order"}
    check("every source document became exactly one article",
          set(ids) == expected, "got %s" % sorted(ids))
    check("no article id is emitted twice", len(ids) == len(set(ids)),
          [i for i in ids if ids.count(i) > 1])
    check("the printed article count matches the articles emitted",
          ("%d articles" % len(ids)) in proc.stdout, proc.stdout.strip())

    # --- manifests are never rendered ----------------------------------------
    check("aggregate-manifest.json is not rendered",
          "aggregate-manifest" not in doc and "AGG-001" not in doc)

    # --- Mermaid round-trip ---------------------------------------------------
    blocks = re.findall(r'<pre class="mermaid">(.*?)</pre>', doc, re.S)
    fence_count = DOC_A.count("```mermaid")
    check("one mermaid block per mermaid fence",
          len(blocks) == fence_count, "%d blocks vs %d fences" % (len(blocks), fence_count))
    check("the printed mermaid count matches the blocks emitted",
          ("%d mermaid blocks" % len(blocks)) in proc.stdout, proc.stdout.strip())
    check("the fence body round-trips through html.unescape unchanged",
          bool(blocks) and html_mod.unescape(blocks[0]) == MERMAID_SRC,
          repr(html_mod.unescape(blocks[0])) if blocks else "no block")
    check("the escaping is applied exactly once (no &amp;amp; in the block)",
          bool(blocks) and "&amp;amp;" not in blocks[0])
    check("braces in prose survive the render",
          "order-{tenant}-svc" in doc and "{max: 3}" in doc)

    # --- links and anchors ----------------------------------------------------
    check("an inter-report link was rewritten to its in-page anchor",
          'href="#data-model"' in doc and "03_design/data-model.md" not in
          re.sub(r'<span class="src">[^<]*</span>', "", doc))

    # --- Gherkin --------------------------------------------------------------
    check("the .feature file is rendered as a Gherkin code block",
          '<code class="language-gherkin">' in doc and "Scenario: Payment is authorized" in doc)
    check("the .feature article is titled from its Feature: line",
          "Place an order" in doc)

    # --- section identifiers --------------------------------------------------
    # Heading hierarchy (review-report RPT-502): one page-level h1, phases h2, documents h3,
    # a document's `##` at h4 — no level skipped and no per-article h1.
    check("exactly one <h1> on the page", len(re.findall(r"<h1[ >]", doc)) == 1,
          len(re.findall(r"<h1[ >]", doc)))
    check("document titles are <h3 class=\"doc-title\">",
          doc.count('<h3 class="doc-title">') == len(re.findall(r'<article class="doc"', doc)))
    check("a document's ## renders as <h4>", "<h4" in doc and "<h3 id=" not in doc)
    h2_ids = re.findall(r'<h2 id="([^"]+)"', doc)
    check("section ids are the canonical identifiers, in pipeline order",
          h2_ids == ["analysis", "design", "test-specs"], h2_ids)
    check("the summary section is present", 'id="summary"' in doc)

    # --- missing review synthesis --------------------------------------------
    check("the summary says the review has not been run",
          "review-synthesis.json" in doc and "has not been run" in doc)

    # --- language -------------------------------------------------------------
    check('<html lang="en"> for an English project', '<html lang="en">' in doc)
    check("English section headings", ">Analysis</h2>" in doc and ">Design</h2>" in doc)
    check("English executive-summary label", "Executive Summary" in doc)
    check("no Japanese chrome leaked into an English report",
          "エグゼクティブサマリ" not in doc and "目次" not in doc)

    # -------------------------------------------------------------- Japanese project
    print("output_language: ja switches every UI string, not the document content")

    ja_dir = os.path.join(tmp, "ja")
    build_project(ja_dir, "ja")
    ja_out = os.path.join(tmp, "ja-report.html")
    ja_proc = run(ja_dir, ja_out)
    check("exit 0 on the Japanese project", ja_proc.returncode == 0, ja_proc.stderr.strip())
    ja_doc = open(ja_out, encoding="utf-8").read() if os.path.exists(ja_out) else ""

    check('<html lang="ja"> for a Japanese project', '<html lang="ja">' in ja_doc)
    check("Japanese section headings",
          ">分析（Analysis）</h2>" in ja_doc and ">設計（Design）</h2>" in ja_doc)
    check("Japanese table of contents title", ">目次</h2>" in ja_doc)
    check("Japanese executive-summary heading", "エグゼクティブサマリ" in ja_doc)
    check("Japanese 'review not run' note", "レビューは未実行" in ja_doc)
    check("document content is unchanged by the language switch",
          "System Overview" in ja_doc and "Place an order" in ja_doc)
    check("the section identifiers are language-independent",
          re.findall(r'<h2 id="([^"]+)"', ja_doc) == h2_ids)

    # ------------------------------------------------------------------ failure mode
    print("A directory that is not a project is refused, not half-rendered")

    empty = os.path.join(tmp, "not-a-project")
    os.makedirs(empty)
    bad = run(empty, os.path.join(tmp, "never.html"))
    check("exit 1 when the directory has no reports/", bad.returncode == 1, bad.returncode)
    check("the refusal names the missing directory", "reports/" in bad.stderr, bad.stderr)
    check("nothing was written", not os.path.exists(os.path.join(tmp, "never.html")))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d checks, %d failed" % (checks, len(failures)))
if failures:
    for f in failures:
        print("  - %s" % f)
    raise SystemExit(1)
