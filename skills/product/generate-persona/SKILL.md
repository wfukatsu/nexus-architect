---
description: |
  Generate Jobs-to-be-Done–anchored personas — job stories plus persona cards (context, pains,
  gains, JTBD, verbatim) — as a proto-persona scaffold that promotes to research-based as evidence
  arrives. Never fabricates demographics or quotes.
  /product:generate-persona [--input=<file|dir>] [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# Personas (Jobs-to-be-Done)

## Desired Outcome

Produce one deliverable:

1. **Personas** — `reports/01_ux/personas.md`:
   - **Job stories** (`JOB-` IDs) — *When [situation], I want to [motivation], so I can [outcome]*,
     covering functional / emotional / social dimensions
   - **Persona cards** (`PER-` IDs) — archetype, context & behaviors, JTBD, Pains, Gains, and a
     verbatim quote (marked `[proto]` if unvalidated)
   - A designated **primary persona** vs secondary / anti-personas

Personas are anchored to jobs (which survive pivots), not to demographics. Unvalidated content is
explicitly a **proto-persona** scaffold.

## Invocation

```
/product:generate-persona [--input=<file|dir>]... [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--input=<file\|dir>` | Recommended | Interview notes, surveys, analytics, support logs |
| `--auto` | Optional | Skip elicitation; generate proto-personas from inputs only |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Anchor to jobs, not demographics.** Every persona must carry at least one `JOB-` story.
- **AI output is a scaffold.** Mark unvalidated claims `[proto]`; emotional validity is weak until
  research confirms it. Prefer research data wherever it exists.
- **Never fabricate demographics or quotes.** Unknowns → `TBD` in Open Questions.
- **Name a primary persona** — the product cannot be optimized for "everyone".
- **Stop condition**: ≥1 job story per persona, each persona card complete (or `TBD`/`[proto]`),
  and a primary persona designated.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/00_core/vision-mission-value.md` | Required | `/product:define-vision` | block with a message — personas need the target group |
| research material (`--input`) | Recommended | User | proceed as proto-persona; mark `[proto]` |

## Process

1. **Read context** — vision (target group), `work/context.md`, `work/traceability.json`, `--input`.
2. **Extract jobs** — write job stories from the target group's situations (functional/emotional/
   social). Apply `@rules/product/persona-jtbd.md`.
3. **Build cards** — context, Pains, Gains, JTBD, verbatim (from research, else `[proto]`).
4. **Prioritize** — designate the primary persona vs secondary / anti-personas.
5. **Append traceability** — add `JOB-`/`PER-` nodes to `work/traceability.json` with Upstream
   `VIS-` references.
6. **Record** — write the file; append decisions to `work/context.md`; log `TBD`/`[proto]` items.

## Output

`reports/01_ux/personas.md`, with `JOB-`/`PER-` ID tables (Upstream column) and the primary persona
flagged.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/persona-jtbd.md` | JTBD job stories, persona cards, proto vs research-based |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-vision` | Upstream — provides the target group |
| `/product:map-journey` | Downstream — maps the journey of each persona |
| `/product:define-features` | Downstream — features serve `JOB-`/`PER-` |
| `/product:adapt-change` | Re-runs this skill when the audience changes |
