# Output Conventions

## Output Language

The output language is configured per project in `work/pipeline-progress.json`:
- `options.output_language`: "en" (default) or "ja"
- All report documents, analysis text, and descriptions use the configured language
- YAML frontmatter keys remain in English regardless of output language
- Mermaid node IDs remain in English; labels use the configured language

## YAML Frontmatter (Required)

All output files must include the following frontmatter:

```yaml
---
title: "Document Title"
schema_version: 1
phase: "Phase N: Category Name"
skill: skill-name
generated_at: "ISO8601"
input_files:
  - reports/XX/input-file.md
---
```

## File Naming Conventions

- **kebab-case only**: `ubiquitous-language.md` (NOT `ubiquitous_language.md`)
- Directories indicate the phase, so no phase prefix is needed in file names
- Suffix examples: `-analysis.md`, `-evaluation.md`, `-design.md`, `-specs.md`

## Immediate Output Rule

**Important**: Output files immediately upon completion of each step. Do not batch outputs at the end.

Reasons:
- To allow pipeline interruption and resumption
- To make intermediate artifacts visible
- To enable skill parallelization

## Language

- All output documents: Use the configured language (see Output Language above)
- YAML frontmatter: English keys, values in the configured language
- Mermaid nodes: Wrap non-ASCII text in quotes

## Document Structure

- Heading levels start at `##` (`#` is reserved for the title)
- Place Mermaid diagrams at appropriate locations
- Tables use standard Markdown format
- Code blocks must include language specification
