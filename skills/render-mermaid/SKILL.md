---
description: |
  Render Mermaid diagrams to PNG/SVG/PDF and fix syntax errors.
argument-hint: '[target_path]'
model: haiku
---

# Mermaid Rendering and Repair

**Usage:** `/architect:render-mermaid [target_path]`

## Desired Outcome

Convert Mermaid diagrams in the specified Markdown file or directory to images.
Automatically fix any syntax errors found.

## Features

- Mermaid to PNG/SVG/PDF conversion (using the mmdc command)
- Automatic syntax error detection and repair
- Quote correction for non-ASCII text
- Mismatched bracket repair

## Tools

- Uses `mmdc` (mermaid-cli) if installed
- Falls back to syntax validation only if not installed

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

Rendered output is placed in the same directory as the source file.
