---
name: report
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

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/00_summary/full-report.html` | Consolidated HTML report |
