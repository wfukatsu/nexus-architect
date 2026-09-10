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


# ---------------------------------------------------------------- product fixtures
# The product tree has its own section map and opens with the validation status instead
# of a review verdict. The shapes below mirror a real /product:start run: an ASM- table
# with bold cells, TBD placeholders in both ASCII and full-width parentheses, the 8-column
# Open Questions store, a Mermaid fence inside a domain story, example maps with an index,
# HTML mocks and figures that must be listed but never embedded, and an undeclared
# directory (poc/) that still has to appear.
PRODUCT_ASSUMPTIONS = """---
title: "Assumptions"
schema_version: 1
---

| ID | Category | Hypothesis | Impact |
|----|----------|------------|--------|
| ASM-001 | Desirability | **Auditors want external proof** (VIS-001) | high |
| ASM-002 | Feasibility | **Zero impact on existing jobs** | high |
| ASM-003 | Viability | Customers pay per seal event | low |

The unit price is TBD-assumption until the pilot.
"""

PRODUCT_VALIDATION_PLAN = """---
title: "Validation Plan"
schema_version: 1
---

| ID | Test | Threshold | Status |
|----|------|-----------|--------|
| ASM-001 | interviews | majority agree | not run |
| ASM-002 | PoC week 1 | < 5% slowdown | not run |
| ASM-003 | price survey | < 50% too expensive | not run |
"""

PRODUCT_PERSONAS = """---
title: "Personas"
schema_version: 1
---

## PER-001

The p95 target is TBD (OQ-001) and the tenant model is TBD（OQ-004）.
"""

PRODUCT_STORY = """---
title: "Domain Story: Disclosure"
schema_version: 1
---

```mermaid
%s
```
""" % MERMAID_SRC

PRODUCT_FEATURES = """---
title: "Feature List"
schema_version: 1
---

See the [example maps](examples/index.md).
"""

PRODUCT_OQ_STORE = (
    "## Open Questions\n\n"
    "| ID | Question | Status | Answer | Options offered | Owner | Impact | Asked at |\n"
    "|----|----------|--------|--------|-----------------|-------|--------|----------|\n"
    "| OQ-001 | What is the p95 latency target? | deferred | — | 200ms / 500ms | product owner | High | define-nfr |\n"
    "| OQ-002 | Which tenant isolation model? | answered | schema per tenant | — | architect | Medium | map-domains |\n"
    "| OQ-003 | Is the brand name registrable? | external | — | — | legal | Low | name-product |\n"
    "| OQ-004 | Who approves on mobile? | unasked | — | — | product owner | Medium | map-journey |\n"
)


def simple_doc(title, body="Body.\n"):
    return '---\ntitle: "%s"\nschema_version: 1\n---\n\n%s' % (title, body)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def build_product_project(root, language, degraded=False):
    """A product-pipeline scratch project. `degraded` drops the gate, the assumptions
    document and the Open Questions store — the shapes the summary must survive."""
    progress = {
        "schema_version": 1,
        "project_name": "scratch-product",
        "options": {"output_language": language, "profile": "full"},
        "phases": {},
    }
    if not degraded:
        progress["gates"] = {"validate-assumptions": {
            "verdict": "go", "open_assumptions": ["ASM-001", "ASM-002"],
            "evaluated_at": "2026-01-01T00:00:00+00:00"}}
    write(os.path.join(root, "work", "pipeline-progress.json"), json.dumps(progress, indent=2))
    if not degraded:
        write(os.path.join(root, "work", "context.md"), PRODUCT_OQ_STORE)
    core = os.path.join(root, "reports", "00_core")
    # Written in reverse pipeline order so name order and manifest order disagree.
    write(os.path.join(core, "scope-definition.md"), simple_doc("Scope Definition"))
    write(os.path.join(core, "vision-mission-value.md"), simple_doc("Vision"))
    if not degraded:
        write(os.path.join(core, "assumptions.md"), PRODUCT_ASSUMPTIONS)
    write(os.path.join(core, "validation-plan.md"), PRODUCT_VALIDATION_PLAN)
    write(os.path.join(core, "summary.md"), simple_doc("A document named summary"))
    write(os.path.join(root, "reports", "01_ux", "personas.md"), PRODUCT_PERSONAS)
    write(os.path.join(root, "reports", "01_ux", "domain-stories", "domain-story-disclosure.md"),
          PRODUCT_STORY)
    spec = os.path.join(root, "reports", "02_spec")
    write(os.path.join(spec, "feature-list.md"), PRODUCT_FEATURES)
    write(os.path.join(spec, "examples", "index.md"), simple_doc("Example Map Index"))
    write(os.path.join(spec, "examples", "example-map-feat-001.md"),
          simple_doc("Example Map: Search"))
    write(os.path.join(spec, "ui-mocks", "solution-exploration.md"),
          simple_doc("Solution Exploration"))
    write(os.path.join(spec, "ui-mocks", "SCR-001.html"), "<html><body>mock</body></html>")
    write(os.path.join(root, "reports", "03_domain", "domain-map.md"),
          simple_doc("Domain Map", "![runtime view](figures/arch.png)\n"))
    write(os.path.join(root, "reports", "03_domain", "figures", "arch.png"), "")
    write(os.path.join(root, "reports", "poc", "poc-results.md"), simple_doc("PoC Results"))
    write(os.path.join(root, "reports", "report", "review.md"), simple_doc("Multi-Lens Review"))


def summary_of(doc):
    m = re.search(r'<section id="summary".*?</section>', doc, re.S)
    return m.group(0) if m else ""


def oq_group(doc, label):
    """The table that follows the `<h4>label (n)</h4>` heading of one status group."""
    m = re.search(r"<h4>%s \(\d+\)</h4>(.*?)</table>" % re.escape(label), doc, re.S)
    return m.group(1) if m else ""


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


def run(project_dir, output=None, *extra):
    argv = [sys.executable, TOOL, project_dir]
    if output:
        argv += ["--output", output]
    return subprocess.run(argv + list(extra), capture_output=True, text=True)


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
    # Mermaid's startOnLoad reads innerHTML: a <code> wrapper inside <pre class="mermaid">
    # becomes part of the diagram text and every diagram fails with "No diagram type
    # detected". The fence must therefore never go through the generic code path.
    check("no mermaid block wraps its source in <code>",
          '<pre class="mermaid"><code' not in doc)
    check("no mermaid fence fell through to the generic code renderer",
          "language-mermaid" not in doc)
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

    # --------------------------------------------------------------- product project
    print("A product project is detected, ordered by the manifest and opens with the "
          "validation status")

    pr_dir = os.path.join(tmp, "product")
    build_product_project(pr_dir, "en")
    pr_proc = run(pr_dir)                      # no --output: the layout's default path
    pr_out = os.path.join(pr_dir, "reports", "report", "full-report.html")
    check("exit 0 on a product project", pr_proc.returncode == 0,
          pr_proc.stderr.strip() or pr_proc.stdout.strip())
    check("the default output of a product project is reports/report/full-report.html",
          os.path.exists(pr_out))
    check("the printed line names the detected layout", "layout=product" in pr_proc.stdout,
          pr_proc.stdout.strip())
    pr_doc = open(pr_out, encoding="utf-8").read() if os.path.exists(pr_out) else ""
    pr_summary = summary_of(pr_doc)

    # --- sections --------------------------------------------------------------
    pr_h2 = re.findall(r'<h2 id="([^"]+)"', pr_doc)
    check("product section ids are the canonical identifiers, in pipeline order",
          pr_h2 == ["core", "ux", "spec", "domain", "other", "review"], pr_h2)
    check("the summary section precedes every phase section",
          0 < pr_doc.find('id="summary"') < pr_doc.find('<h2 id="core"'))
    check("the summary is titled Key Assumptions & Validation Status",
          "<h2>Key Assumptions &amp; Validation Status</h2>" in pr_summary)
    check('id="summary" is emitted exactly once', pr_doc.count('id="summary"') == 1)
    check("exactly one <h1> on the product page", len(re.findall(r"<h1[ >]", pr_doc)) == 1)

    # --- gate, assumptions, TBD, Open Questions -------------------------------
    check("the gate verdict is a GO banner",
          'verdict-banner ok' in pr_summary and ">GO<" in pr_summary)
    check("only the open ASM- rows are repeated in the summary",
          "ASM-001" in pr_summary and "ASM-002" in pr_summary and "ASM-003" not in pr_summary)
    check("bold inside an ASM- cell renders as <strong>",
          "<strong>Auditors want external proof</strong>" in pr_summary)
    check("the validation plan rows are repeated too",
          "PoC week 1" in pr_summary and "price survey" not in pr_summary)
    personas_row = re.search(r'<tr><td><a href="#personas">.*?</tr>', pr_summary, re.S)
    check("the TBD table links the personas document with both placeholders and their OQs",
          bool(personas_row) and '<td class="num">2</td><td class="num">0</td>' in
          personas_row.group(0) and "OQ-001" in personas_row.group(0)
          and "OQ-004" in personas_row.group(0),
          personas_row.group(0) if personas_row else "no row")
    asm_row = re.search(r'<tr><td><a href="#assumptions">.*?</tr>', pr_summary, re.S)
    check("a TBD-assumption is counted in its own column",
          bool(asm_row) and '<td class="num">0</td><td class="num">1</td>' in asm_row.group(0),
          asm_row.group(0) if asm_row else "no row")
    check("the TBD note totals the placeholders",
          "2 <code>TBD</code> and 1 <code>TBD-assumption</code>" in pr_summary)
    check("a deferred question is listed with its owner",
          "OQ-001" in oq_group(pr_summary, "deferred")
          and "product owner" in oq_group(pr_summary, "deferred"))
    check("an external question is listed with its owner",
          "OQ-003" in oq_group(pr_summary, "external")
          and "legal" in oq_group(pr_summary, "external"))
    check("an unasked question is visibly different from a deferred one",
          "OQ-004" in oq_group(pr_summary, "unasked")
          and "OQ-004" not in oq_group(pr_summary, "deferred"))
    check("answered questions are a count, not a table",
          "1 answered" in pr_summary and "OQ-002" not in pr_summary)

    # --- order, subgroups, assets, other -------------------------------------
    pr_ids = re.findall(r'<article class="doc" id="([^"]+)"', pr_doc)
    core_ids = [i for i in pr_ids if i in
                ("vision-mission-value", "scope-definition", "assumptions", "validation-plan",
                 "summary-2")]
    check("documents follow the manifest's pipeline order, not name order",
          core_ids == ["vision-mission-value", "scope-definition", "assumptions",
                       "validation-plan", "summary-2"], core_ids)
    check("examples/index.md leads its subgroup",
          pr_ids.index("index") < pr_ids.index("example-map-feat-001"))
    check("a link to examples/index.md became an in-page anchor", 'href="#index"' in pr_doc)
    check("subgroup titles are the bilingual UI strings",
          ">Domain Stories</h3>" in pr_doc and ">Example Maps</h3>" in pr_doc
          and ">UI Mocks</h3>" in pr_doc)
    check("HTML mocks and figures are listed by name, never embedded",
          "<code>SCR-001.html</code>" in pr_doc and "<code>arch.png</code>" in pr_doc
          and "mock</body>" not in pr_doc)
    check("a Markdown document under ui-mocks/ is still an article",
          "solution-exploration" in pr_ids)
    check("a relative image path is re-based onto the output directory",
          'src="../03_domain/figures/arch.png"' in pr_doc)
    check("an undeclared directory becomes a subgroup of Other Documents",
          ">poc</h3>" in pr_doc and "poc-results" in pr_ids)
    check("a document named summary.md does not collide with the summary section",
          "summary-2" in pr_ids and "summary" not in pr_ids)
    check("review.md does not collide with the review section",
          "review-2" in pr_ids and "review" not in pr_ids)
    check("no product article id is emitted twice", len(pr_ids) == len(set(pr_ids)))

    # --- Mermaid ---------------------------------------------------------------
    pr_blocks = re.findall(r'<pre class="mermaid">(.*?)</pre>', pr_doc, re.S)
    check("one mermaid block per fence in the product report", len(pr_blocks) == 1,
          len(pr_blocks))
    check("the product fence round-trips unchanged",
          bool(pr_blocks) and html_mod.unescape(pr_blocks[0]) == MERMAID_SRC)
    check("no product mermaid block wraps its source in <code>",
          '<pre class="mermaid"><code' not in pr_doc and "language-mermaid" not in pr_doc)

    # --- flags -----------------------------------------------------------------
    ja_pr_out = os.path.join(tmp, "product-ja.html")
    ja_pr = run(pr_dir, ja_pr_out, "--lang", "ja")
    ja_pr_doc = open(ja_pr_out, encoding="utf-8").read() if os.path.exists(ja_pr_out) else ""
    check("--lang overrides the project's output_language", ja_pr.returncode == 0
          and '<html lang="ja">' in ja_pr_doc and "主要な仮説と検証状況" in ja_pr_doc)
    check("the product section identifiers are language-independent",
          re.findall(r'<h2 id="([^"]+)"', ja_pr_doc) == pr_h2)
    forced_out = os.path.join(tmp, "product-as-architect.html")
    forced = run(pr_dir, forced_out, "--layout", "architect")
    forced_doc = open(forced_out, encoding="utf-8").read() if os.path.exists(forced_out) else ""
    check("--layout architect overrides the detection",
          forced.returncode == 0 and '<h2 id="core"' not in forced_doc
          and "Executive Summary" in forced_doc)

    # --- degraded inputs -------------------------------------------------------
    print("A product project without a gate, assumptions or an OQ store still renders")
    dg_dir = os.path.join(tmp, "product-degraded")
    build_product_project(dg_dir, "en", degraded=True)
    dg_out = os.path.join(tmp, "product-degraded.html")
    dg = run(dg_dir, dg_out)
    dg_doc = open(dg_out, encoding="utf-8").read() if os.path.exists(dg_out) else ""
    dg_summary = summary_of(dg_doc)
    check("exit 0 without gate, assumptions.md or context.md", dg.returncode == 0,
          dg.stderr.strip())
    check("the missing gate is a warning banner, not a fabricated verdict",
          'verdict-banner warn' in dg_summary and "has not been evaluated" in dg_summary)
    check("the missing assumptions document is stated",
          "assumptions.md</code> does not exist" in dg_summary)
    check("the missing OQ store is stated",
          "context.md</code> does not exist" in dg_summary)

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
