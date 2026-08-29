---
description: |
  Compile all Markdown reports into a consolidated HTML report.
  Invoked via /architect:report.
model: haiku
user_invocable: true
---

# Report Compilation

## Desired Outcome

Generate a consolidated HTML report from all Markdown files under reports/.

## Features

- Markdown to HTML conversion
- Inline rendering of Mermaid diagrams
- Automatic table of contents generation
- Section structure organized by phase
- Light/dark theme support
- Responsive design (mobile and print friendly)

## Execution

**The report is built by a tool, not authored.** Do not read the report tree and write HTML
by hand: the rendering — escaping, anchors, article ids, section order, the bilingual
chrome — is a contract the tool owns and a test suite guards
(`tools/build_report.test.py`). Hand-writing it drifts from that contract silently and
costs a full re-read of every report on every run.

One command does the whole job:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/build-report.py" <project_dir>
# --output PATH       write somewhere other than reports/00_summary/full-report.html
# --mermaid-js PATH   inline this copy of mermaid.min.js instead of the resolved default
```

`<project_dir>` is the project root — the directory holding `reports/` and `work/`; it
defaults to the current directory. The tool reads `options.output_language` from
`work/pipeline-progress.json` itself, so no language argument is passed.

Steps:

1. **Run the command.** Exit 0 means the report was written. Exit 1 means the directory has
   no `reports/` (wrong project root), or the Python dependencies are missing — in that
   case run `pip install -r requirements.txt` and retry.
2. **Record what it printed.** One line: the article count, the number of Mermaid blocks
   embedded, the byte size, whether Mermaid was inlined or left to the CDN, and the output
   path. Report those numbers to the user rather than re-describing the report's contents.
3. **Stamp the phase** in `work/pipeline-progress.json` per @skills/common/progress-registry.md
   — `in_progress` before the run, then `completed` with `outputs` and a one-line `summary`
   afterwards. Write `"plugin": "architect"`: `report` is defined by both manifests, so that
   field is the only thing that says whose entry this is.

The tool inlines Mermaid from the first copy it finds — the one named on the command line,
then `<repo>/tools/docs-site/node_modules/mermaid/dist/mermaid.min.js`, then
`~/.cache/nexus-architect/mermaid.min.js` — and falls back to a CDN `<script src>` with a
visible note in the report when none exists.

Quality review of the produced HTML is a separate skill: `/architect:review-report`.

## Input Sources

Compile all Markdown files found in the following directories (skip any that don't exist).
Render each section heading in the language configured in `work/pipeline-progress.json`
(`options.output_language`); the English names below are the canonical section identifiers,
and they are the `<h2 id>` of each section in the emitted HTML regardless of language.

| Directory | Phase | Section heading (English canonical) |
|-----------|-------|--------------------------------------|
| `reports/before/{project}/` | Investigation | Investigation |
| `reports/01_analysis/` | Analysis | Analysis |
| `reports/02_evaluation/` | Evaluation | Evaluation |
| `reports/03_design/` | Design | Design |
| `reports/04_stories/` | Domain Stories | Domain Stories |
| `reports/06_implementation/` | Implementation | Implementation |
| `reports/07_test-specs/` | Test Specifications | Test Specifications |
| `reports/review/` | Review | Review |

`reports/before/` holds one subdirectory per investigated project; each becomes its own
subgroup within the Investigation section, discovered by glob rather than assumed.

`reports/04_stories/` is optional — include the section only when one or more `domain-story-*.md` files exist there.

`reports/03_design/aggregates/` is a subdirectory of the Design section and is compiled with it — include each `aggregate-*.md` as a Design subsection carrying its `classDiagram` and its invariant table with examples. `aggregate-manifest.json` is the machine-readable model, not report content: it is not rendered.

`reports/03_design/state-machines/` is a subdirectory of the Design section and is compiled with it — include each `state-machine-*.md` as a Design subsection carrying its `stateDiagram-v2` and its state × event matrix. `state-machine-manifest.json` is the machine-readable model, not report content: it is not rendered.

`reports/03_design/adr/` is compiled with the Design section too, `index.md` first and then
the records in `ADR-###` order. `reports/03_design/api-specifications/` contributes its
Markdown as subsections; the OpenAPI/AsyncAPI YAML is listed by file name and `info.title`
only, never embedded. No manifest JSON is ever rendered.

`reports/07_test-specs/bdd-scenarios/*.feature` is rendered as Gherkin code blocks within
the Test Specifications section.

The Executive Summary is built from `work/pipeline-progress.json`,
`reports/review/review-synthesis.json` and the Open Questions store in `work/context.md`.
When the review has not run — no `review-synthesis.json` — the report is still produced and
the summary says so instead of carrying a quality gate verdict.

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/00_summary/full-report.html` | Consolidated HTML report |
