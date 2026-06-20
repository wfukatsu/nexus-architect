---
description: |
  Consolidate all product artifacts into one self-contained HTML report (Mermaid inline) that leads
  with a mandatory "Key Assumptions & Validation Status" section — gate verdict, open assumptions,
  every TBD, and Open Questions — before any design content. /product:report [--auto] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# Consolidated Report

## Desired Outcome

Produce one deliverable:

1. **Full report** — `reports/report/full-report.html`:
   - **Leads with "Key Assumptions & Validation Status"** — the gate verdict, untested/open
     assumptions with thresholds, every `TBD` / `TBD-assumption`, and Open Questions
   - Then a section per phase in pipeline order, each linking to its source file
   - Mermaid diagrams rendered inline; self-contained (inline CSS), no external assets beyond the
     Mermaid runtime

## Invocation

```
/product:report [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Generate from whatever artifacts exist |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Assumptions first.** The validation status sits at the very top — the reader must see what is a
  bet before reading the design.
- **Never fabricate a "pass".** A missing artifact or a `no-go` verdict is stated prominently.
- **Self-contained.** Inline CSS; render Mermaid; no broken external references.
- **Stop condition**: the Key Assumptions section is present and complete, all existing artifacts are
  included in pipeline order, and Mermaid blocks render.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/**/*.md` | Required | all prior skills | include whatever exists; note missing phases |
| `work/pipeline-progress.json` | Required | `/product:init-output` | report the gate verdict; if absent, mark `TBD` |
| `reports/00_core/assumptions.md` | Recommended | `/product:validate-assumptions` | assumptions section degrades to "not yet validated" |
| `work/context.md` | Recommended | all skills | Open Questions section degrades to `TBD` |

## Process

1. **Collect** — gather all `reports/**/*.md`, the gate verdict, assumptions, and Open Questions.
2. **Build the header** — assemble "Key Assumptions & Validation Status" from the gate, open `ASM-`,
   all `TBD`s, and Open Questions. Apply `@rules/product/review-and-report.md`.
3. **Assemble body** — one section per phase in pipeline order, linking source files; render Mermaid.
4. **Self-contain** — inline CSS; verify no broken references.
5. **Record** — write `full-report.html`; append a note to `work/context.md`.

## Output

`reports/report/full-report.html`, leading with validation status and consolidating all artifacts.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/review-and-report.md` | Report structure and the mandatory assumptions header |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:review` | Upstream — findings can be surfaced in the report |
| `/product:validate-assumptions` | Upstream — supplies the gate verdict and open assumptions |
| `/product:start` | Orchestrator — typically runs `report` as the final step |
