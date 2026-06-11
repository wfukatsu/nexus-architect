---
description: |
  Review the quality of the generated HTML report (full-report.html).
  Checks completeness, score accuracy, Mermaid syntax, language consistency, and structural integrity.
  Invoked via /architect:review-report.
model: sonnet
user_invocable: true
---

# Report Quality Review

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

Scan all `<div class="mermaid">` blocks in the HTML for common syntax errors:

- Mismatched brackets or quotes in node labels
- Invalid arrow syntax (e.g. `->` instead of `-->`)
- Non-ASCII text in node IDs (must be in labels only)
- Empty diagram blocks
- Unsupported diagram types

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
- No TODO / placeholder text (e.g. "[TBD]", "PLACEHOLDER", "TODO") should appear in the final output

---

## Execution Steps

### Step 1: Load Reference Data

Read the following files **before** spawning sub-agents:

1. `work/pipeline-progress.json` — list of completed phases and their outputs
2. `reports/review/review-synthesis.json` — authoritative scores and finding IDs
3. `reports/00_summary/full-report.html` — the report under review

Extract and record:
- All phases with `status: "completed"` and their `summary` fields
- `weighted_score`, `verdict`, and per-perspective scores from review-synthesis.json
- MMI scores from `mmi-overview.md` (read separately if not in synthesis)
- The list of P1 finding IDs from `review-synthesis.md`

### Step 2: Spawn Parallel Dimension Reviewers

Issue all five Task() calls in a **single message** so they run in parallel.
Pass the extracted reference data inline in each prompt (do not ask sub-agents to re-read pipeline-progress.json).

**Task A — Completeness**
```
Task(
  subagent_type: "general-purpose",
  description: "Report completeness check",
  prompt: """
You are reviewing whether reports/00_summary/full-report.html covers all pipeline phases.

Completed phases (from pipeline-progress.json):
<COMPLETED_PHASES>
[List each phase name and its summary, one per line]
</COMPLETED_PHASES>

Read the HTML file at reports/00_summary/full-report.html.

For each completed phase, check whether there is a corresponding section in the HTML.
Also verify these key metrics appear somewhere in the HTML:
- MMI system score
- DDD composite score
- Overall review verdict and weighted score
- At least one Mermaid diagram

Score 1-5: 5=All phases and metrics present, 4=1-2 minor omissions, 3=Missing one phase section, 2=Missing multiple phases, 1=Major content missing

Return ONLY this JSON (no markdown fences):
{
  "name": "Completeness",
  "weight": 0.30,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "RPT-1<NN>",
      "severity": "critical|major|minor|info",
      "location": "<html section or 'global'>",
      "title": "<finding title>",
      "description": "<what is missing and its impact>",
      "recommendation": "<specific fix>"
    }
  ]
}
"""
)
```

**Task B — Score Accuracy**
```
Task(
  subagent_type: "general-purpose",
  description: "Report score accuracy check",
  prompt: """
You are cross-checking numerical scores in the HTML report against authoritative sources.

Authoritative scores (from review-synthesis.json and mmi-overview.md):
<SCORES>
[List each score: "consistency: 76", "scalardb: 78", "operations: 62", "risk: 48", "business: 74", "weighted_total: 65.5", "verdict: FAIL", "mmi_system: 50.8", "ddd_score: 30.3", etc.]
</SCORES>

P1 finding IDs that must appear in the HTML:
<P1_IDS>
[List each P1 finding ID, e.g. "RSK-002", "RSK-013", ...]
</P1_IDS>

Read the HTML file at reports/00_summary/full-report.html.

1. Find each score value in the HTML and compare to the authoritative value (tolerance: ±0.5).
2. Check that every P1 finding ID appears somewhere in the HTML.
3. Verify the overall verdict string (PASS / CONDITIONAL_PASS / FAIL) matches.

Score 1-5: 5=All values exact, 4=Trivial rounding only, 3=1-2 minor discrepancies, 2=Score error >2pts or missing P1 ID, 1=Multiple major errors or wrong verdict

Return ONLY this JSON (no markdown fences):
{
  "name": "Score Accuracy",
  "weight": 0.35,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "RPT-2<NN>",
      "severity": "critical|major|minor|info",
      "location": "<element or section in HTML>",
      "title": "<discrepancy description>",
      "description": "<expected value vs actual value found in HTML>",
      "recommendation": "<fix>"
    }
  ]
}
"""
)
```

**Task C — Mermaid Syntax**
```
Task(
  subagent_type: "general-purpose",
  description: "Mermaid diagram syntax check",
  prompt: """
You are checking Mermaid diagram blocks in an HTML file for syntax errors.

Read the HTML file at reports/00_summary/full-report.html.

Extract all content inside <div class="mermaid">...</div> blocks.
For each block, check for:
1. Invalid arrow syntax (e.g. single-dash -> instead of -->)
2. Non-ASCII characters in node IDs (only allowed in quoted labels)
3. Unclosed brackets or quotes in node labels
4. Empty or near-empty blocks (less than 2 lines of content)
5. Unknown diagram type keyword in the first line

Score 1-5: 5=All diagrams syntactically valid, 4=1 minor issue, 3=2-3 minor issues, 2=1 major syntax error, 1=Multiple major errors

Return ONLY this JSON (no markdown fences):
{
  "name": "Mermaid Syntax",
  "weight": 0.15,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "RPT-3<NN>",
      "severity": "critical|major|minor|info",
      "location": "<first 3 lines of the problematic block>",
      "title": "<syntax issue>",
      "description": "<what is wrong and why it will fail to render>",
      "recommendation": "<corrected syntax>"
    }
  ]
}
"""
)
```

**Task D — Language Consistency**
```
Task(
  subagent_type: "general-purpose",
  description: "Report language consistency check",
  prompt: """
You are checking that an HTML report is written in the correct language.

Configured output language: <OUTPUT_LANGUAGE>
(ja = Japanese, en = English)

Read the HTML file at reports/00_summary/full-report.html.

Check that:
1. Section headings are in the configured language
2. Body text paragraphs are in the configured language
3. Table cell content (non-technical) is in the configured language
4. Code blocks, IDs, technical terms, and Mermaid node IDs may remain in English regardless

For each paragraph or heading that appears to be in the wrong language, record a finding.

Score 1-5: 5=Fully consistent, 4=1-2 sentences wrong language, 3=One section wrong language, 2=Multiple sections wrong language, 1=Majority in wrong language

Return ONLY this JSON (no markdown fences):
{
  "name": "Language Consistency",
  "weight": 0.10,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "RPT-4<NN>",
      "severity": "critical|major|minor|info",
      "location": "<section and element>",
      "title": "<language issue>",
      "description": "<what was found and what was expected>",
      "recommendation": "<translation or fix>"
    }
  ]
}
"""
)
```

**Task E — Structural Integrity**
```
Task(
  subagent_type: "general-purpose",
  description: "Report structural integrity check",
  prompt: """
You are checking the structural integrity of an HTML report.

Read the HTML file at reports/00_summary/full-report.html.

Check for:
1. Every href="#<anchor>" in the sidebar nav has a matching id="<anchor>" in the document
2. Every <section id="..."> is linked from the sidebar
3. All <table> elements have a header row (<thead> or first <tr> with <th> elements)
4. No placeholder text: "[TBD]", "TODO", "PLACEHOLDER", "〇〇", "＊＊＊" in visible text
5. The <title> element is non-empty and descriptive
6. The page has exactly one <h1> element (in the hero section)

Score 1-5: 5=No structural issues, 4=1 minor issue, 3=2-3 minor issues, 2=Broken navigation link, 1=Multiple broken links or missing structure

Return ONLY this JSON (no markdown fences):
{
  "name": "Structural Integrity",
  "weight": 0.10,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "RPT-5<NN>",
      "severity": "critical|major|minor|info",
      "location": "<element or section>",
      "title": "<structural issue>",
      "description": "<what is broken>",
      "recommendation": "<fix>"
    }
  ]
}
"""
)
```

### Step 3: Compute Weighted Score and Determine Verdict

After all five Tasks complete:

```
weighted_score = round(
  0.30 × scoreA +
  0.35 × scoreB +
  0.15 × scoreC +
  0.10 × scoreD +
  0.10 × scoreE,
  2
)
```

Verdict thresholds (scale: 1–5):
| Verdict | Condition |
|---------|-----------|
| **PASS** | weighted_score ≥ 4.0 AND no critical findings |
| **PASS_WITH_WARNINGS** | weighted_score ≥ 3.0 AND critical = 0 |
| **FAIL** | weighted_score < 3.0 OR any critical finding exists |

### Step 4: Write Output

Write `reports/review/report-quality-review.md` with the following structure.
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

## Critical / Major Findings

[List each critical or major finding with ID, title, location, description, recommendation]

## Minor / Info Findings

[List minor and info findings as a compact table]

## Required Fixes

[Numbered list of specific edits required to bring the report to PASS]
```

Also update `work/pipeline-progress.json`:
- Set `review-report.status` to `"completed"`
- Set `review-report.outputs` to `["reports/review/report-quality-review.md"]`
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
| `reports/review/report-quality-review.md` | Structured quality review with verdict and findings |
