---
description: |
  Check the consolidated report for completeness, score accuracy, Mermaid syntax, language
  consistency and structure.
model: sonnet
allowed-tools:
  - Bash(python3 ${CLAUDE_PLUGIN_ROOT}/tools/lib/report_review.py *)
  - 'Bash(python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/report_review.py" *)'
---

# Report Quality Review

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

## Desired Outcome

Validate that `reports/00_summary/full-report.html` accurately and completely reflects the full pipeline output.
Produce a structured review document with PASS / WARN / FAIL verdict per check category.

---

## Review Dimensions

### 1. Completeness (weight: 0.30)

Verify all pipeline phases executed in `work/pipeline-progress.json` are represented in the HTML report.

- Every `completed` phase must have at least one corresponding section in the HTML
- Phase outputs listed in `pipeline-progress.json` must be discoverable in the HTML content
- Key metrics (MMI score, DDD score, review scores, overall verdict) must be present
- If `reports/04_stories/domain-story-*.md` files exist, a Domain Stories section must be present in the HTML; each domain covered must appear as a subsection with its sequence diagram
- If `reports/03_design/aggregates/aggregate-*.md` files exist, each modeled aggregate must appear as a Design subsection with its class diagram and its invariant table — an aggregate rendered as a diagram alone loses the invariants that justified the boundary
- If `reports/03_design/state-machines/state-machine-*.md` files exist, each modeled aggregate must appear as a Design subsection with its state diagram and its state × event matrix — a lifecycle rendered as a diagram alone loses the half of the model that says what happens to the illegal attempts

### 2. Score Accuracy (weight: 0.35)

Cross-check numerical values in the HTML against the authoritative source files.

| Value to check | Source of truth |
|---------------|----------------|
| Per-review scores (consistency, scalardb, operations, risk, business) | `reports/review/review-synthesis.json` |
| Overall weighted score and verdict | `reports/review/review-synthesis.json` |
| MMI scores per module | `reports/02_evaluation/mmi-overview.md` |
| DDD composite score | `reports/02_evaluation/ddd-strategic-evaluation.md` or `ddd-tactical-architecture-evaluation.md` |
| P1/P2/P3 finding IDs | `reports/review/review-synthesis.md` |

Tolerance: scores must match exactly (no rounding drift beyond ±0.5).

### 3. Mermaid Syntax (weight: 0.15)

Scan all `<pre class="mermaid">` blocks in the HTML (`tools/build-report.py` emits
`<div class="mermaid-wrap"><pre class="mermaid">…</pre></div>`) for common syntax errors:

- Mismatched brackets or quotes in node labels
- Invalid arrow syntax (e.g. `->` instead of `-->`)
- Non-ASCII text in node IDs (must be in labels only)
- Empty diagram blocks
- Unsupported diagram types
- A `<code>` element inside the block — `<pre class="mermaid"><code>` is what a generic
  Markdown converter emits, and Mermaid's `startOnLoad` reads `innerHTML`, so every such
  diagram fails with "No diagram type detected". One occurrence scores this lens 1.

Report each problematic block with the first 3 lines of the block as location context.

### 4. Language Consistency (weight: 0.10)

Check that the report's primary language matches `options.output_language` in `work/pipeline-progress.json`.

- If `output_language: "ja"`: section headings, body text, and finding descriptions must be in Japanese. English is acceptable for code blocks, IDs, and technical terms.
- If `output_language: "en"`: all narrative text must be in English.

Flag any sections that appear to be in the wrong language (heuristic: detect majority script per paragraph).

### 5. Structural Integrity (weight: 0.10)

- TOC anchor `href` values must correspond to existing `id` attributes in the document
- No `<section id="...">` should be unreachable from the sidebar navigation
- All `<table>` elements must have a `<thead>` row
- No TODO / placeholder text (e.g. "[TBD]", "PLACEHOLDER", "TODO") should appear in the final output.
  A `TBD` that carries its question ID (`TBD (OQ-012)`) and is explained in the Open Questions section
  is **intentional**, not a placeholder (@rules/open-questions.md) — a bare `TBD` with no `OQ-` ID is
  still a defect

---

## Execution Steps

The five dimensions are mechanical passes over a file of several megabytes — the consolidated
report is the whole pipeline in one page — which no sub-agent can read. The measurement is a
script, deterministic and free; the judgement is yours. Earlier versions spawned one reviewer per
dimension; under `/architect:pipeline` the phase delegated nothing twice in a row and recorded
that as a shortfall, which this method is not.

### Step 1: Measure

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/report_review.py" <project_dir> out=work/report-review.json
```

The tool reads `reports/00_summary/full-report.html`, `work/pipeline-progress.json`,
`reports/review/review-synthesis.json`, `mmi-overview.md` and the DDD evaluation, and prints one
JSON document — per dimension, what it measured, the findings the measurements imply (`RPT-1xx` …
`RPT-5xx`, each with severity, location, title, description, recommendation) and the score the
scales below assign; then `weighted_score`, `verdict` and `by_severity`. Exit 1 means there is no
report to review: record the phase `failed` with that reason and stop.

| Dimension | What is measured | Score 1–5 |
|-----------|------------------|-----------|
| Completeness | every `completed` phase with a Markdown output under `reports/` has a document (`<article class="doc" id="<stem>">`); MMI, DDD, aggregate score and verdict stand next to their labels; each domain story, aggregate and state machine file is a document with its diagram and (tactical models) its table | 5 all present; 4 one or two minor omissions (a metric, a diagram, a table); 3 one phase without a section; 2 two; 1 three or more |
| Score Accuracy | each `perspective_scores` value within 120 characters of its name, the aggregate, the verdict string, every P0/P1 finding id | 5 all exact; 4 rounding only; 3 three or more rounded; 2 one score or id missing; 1 the verdict differs (critical) or several missing |
| Mermaid Syntax | every `<pre class="mermaid">` block: `<code>` inside (major), empty (major), unknown type (major), single-dash arrows, non-ASCII node ids, unbalanced brackets and quotes (minor; brackets in flowcharts only) | 5 none; 4 one minor; 3 two or more minor; 2 one major; 1 two or more major |
| Language Consistency | headings and paragraphs (code, `<pre>` and diagrams excluded) against `options.output_language`: a CJK share over 30 % is wrong under `en`, under 10 % wrong under `ja` | 5 none; 4 one or two paragraphs; 3 a heading or three paragraphs; 2 several headings or over ten paragraphs; 1 the majority |
| Structural Integrity | every sidebar `href="#…"` has its `id`; every section and document is in the sidebar; every table has a header row; no `[TBD]` / `TODO` / `PLACEHOLDER` / `〇〇` / `＊＊＊`; a `TBD` without its `OQ-` id; a non-empty `<title>`; one `<h1>` | 5 none; 4 one minor; 3 two or more minor; 2 a broken link or no title; 1 two or more |

Weighted score `0.30 A + 0.35 B + 0.15 C + 0.10 D + 0.10 E`, rounded to two places. Verdict: **PASS**
at ≥ 4.0 with no critical finding; **PASS_WITH_WARNINGS** at ≥ 3.0 with none; **FAIL** below 3.0 or
with any critical.

### Step 2: Judge

Read `work/report-review.json`, then the parts of the report the findings point at (the HTML is
too large to read whole; read the document or block a finding names). For each finding decide
whether it stands, and whether its severity is right:

- A phase the tool reports uncovered because its outputs were written **after** the report was
  built (an extension-tier phase run later) is a stale report, not a missing section: the
  recommendation is `/architect:report` again, and the finding stays major.
- A document present but thin — a story without its activities, an aggregate whose invariant table
  is empty — is what the tool cannot see. Open the document and add a Completeness finding when
  the section would not let a reader reconstruct the model (`RPT-1<nn>`, numbered after the
  tool's).
- A `TBD` the tool counts as bare but which sits in a sentence that names its question two words
  later is not a placeholder; drop the finding and say so under Minor / Info.
- A Mermaid minor in a block that renders (a quote inside a label the tool miscounts) is dropped
  the same way, with the block number.

Scores move only when a finding is dropped or added: recompute from the table above, never by
feel. Record what you dropped and what you added; the JSON is the evidence and stays in `work/`.

### Step 3: Verdict

The weighted score and verdict of the JSON, recomputed after Step 2's changes with the same
formula and thresholds.

### Step 4: Write Output

Write `reports/review/quality-review.md` with the following structure. (The file was `report-quality-review.md` before 0.43.3; under that name a sub-agent cannot write it — Claude Code refuses a sub-agent's Write of a Markdown file whose name starts with `report`, `summary` or `findings` — and this phase runs as a sub-agent under the orchestrators.)
The template below is in English; translate all headings and narrative text into the
language configured in `work/pipeline-progress.json` (`options.output_language`).
YAML frontmatter keys always remain in English.

```markdown
---
title: "Report Quality Review — <project_name>"
schema_version: 1
phase: "Review"
skill: review-report
generated_at: "<ISO-8601>"
input_files:
  - reports/00_summary/full-report.html
  - reports/review/review-synthesis.json
  - work/pipeline-progress.json
  - work/report-review.json
---

## Overall Verdict: <PASS|PASS_WITH_WARNINGS|FAIL> (weighted score: X.X / 5.0)

## Score Summary

| Dimension | Weight | Score | Findings |
|-----------|--------|-------|----------|
| Completeness | 30% | X/5 | N |
| Score Accuracy | 35% | X/5 | N |
| Mermaid Syntax | 15% | X/5 | N |
| Language Consistency | 10% | X/5 | N |
| Structural Integrity | 10% | X/5 | N |
| **Weighted Total** | | **X.X/5** | |

## Method

[One line: measured by `tools/lib/report_review.py` (report size, blocks, tables, paragraphs counted),
findings dropped or added in Step 2 and why]

## Critical / Major Findings

[List each critical or major finding with ID, title, location, description, recommendation]

## Minor / Info Findings

[List minor and info findings as a compact table]

## Required Fixes

[Numbered list of specific edits required to bring the report to PASS]
```

Also update `work/pipeline-progress.json`:
- Set `review-report.status` to `"completed"`
- Set `review-report.outputs` to `["reports/review/quality-review.md"]`
- Write a one-sentence summary into `review-report.summary`

---

## Finding ID Scheme

| Prefix | Dimension |
|--------|-----------|
| RPT-1xx | Completeness |
| RPT-2xx | Score Accuracy |
| RPT-3xx | Mermaid Syntax |
| RPT-4xx | Language Consistency |
| RPT-5xx | Structural Integrity |

---

## Output

Write all output in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/review/quality-review.md` | Structured quality review with verdict and findings |
