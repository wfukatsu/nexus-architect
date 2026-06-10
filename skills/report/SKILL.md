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

## Input Sources

Compile all Markdown files found in the following directories (skip any that don't exist):

| Directory | Phase | Section heading |
|-----------|-------|-----------------|
| `reports/before/{project}/` | Investigation | 調査 / Investigation |
| `reports/01_analysis/` | Analysis | 分析 / Analysis |
| `reports/02_evaluation/` | Evaluation | 評価 / Evaluation |
| `reports/03_design/` | Design | 設計 / Design |
| `reports/04_stories/` | Domain Stories | ドメインストーリー / Domain Stories |
| `reports/review/` | Review | レビュー / Review |

`reports/04_stories/` is optional — include the section only when one or more `domain-story-*.md` files exist there.

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/00_summary/full-report.html` | Consolidated HTML report |
