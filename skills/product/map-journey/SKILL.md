---
description: |
  Map each primary persona's customer journey as a stages × layers grid — touchpoints, actions,
  verbatim emotions, pains, opportunities — with Moments of Truth flagged, yielding a prioritized
  opportunity list. /product:map-journey [--auto] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# Customer Journey Maps

## Desired Outcome

Produce one deliverable:

1. **Journey maps** — `reports/01_ux/journey-maps.md` (`JNY-` IDs):
   - One map per primary persona: **stages** (Awareness → Consideration → Purchase →
     Onboarding → Usage → Renewal → Advocacy) ×
   - **layers**: touchpoints/channels, actions, thoughts & emotions (**verbatim** + emotion curve),
     pain points, opportunities
   - **Moments of Truth** (ZMOT / FMOT / SMOT) flagged, especially where the emotion curve dips
   - A prioritized **opportunity list** (the real output)

## Invocation

```
/product:map-journey [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Generate from personas without elicitation; assumed entries → `[proto]` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Ground every row in a persona's job.** Pains/opportunities tie back to `JOB-`/`PER-` IDs.
- **Capture emotion verbatim** where possible; the emotion curve must make the dip visible.
- **Don't invent feelings.** Assumed entries are `[proto]` until validated.
- **Flag Moments of Truth** — the dips at MoTs are the highest-leverage fix points.
- **Stop condition**: each primary persona has a stage×layer map with MoTs flagged and a
  prioritized opportunity list.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/01_ux/personas.md` | Required | `/product:generate-persona` | block with a message — journeys need personas |

## Process

1. **Read context** — personas (focus on the primary), `work/traceability.json`.
2. **Lay out stages** — adapt the default spine to the product/persona.
3. **Fill layers** — touchpoints, actions, verbatim emotions + curve, pains, opportunities per
   stage. Apply `@rules/product/journey-mapping.md`.
4. **Flag MoTs** — mark ZMOT/FMOT/SMOT and the emotion dips.
5. **Prioritize opportunities** — rank by leverage (pain severity × frequency).
6. **Append traceability** — add `JNY-` nodes to `work/traceability.json` with Upstream
   `PER-`/`JOB-` references.
7. **Record** — write the file; append decisions to `work/context.md`; log `[proto]`/`TBD` items.

## Output

`reports/01_ux/journey-maps.md`, with a `JNY-` ID table (Upstream column) and a prioritized
opportunity list.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/journey-mapping.md` | Stages × layers, emotion curve, Moments of Truth |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:generate-persona` | Upstream — provides the personas mapped here |
| `/product:design-positioning` | Downstream — touchpoints feed the positioning matrix |
| `/product:generate-ui-mock` | Downstream — mocks address journey opportunities |
| `/product:adapt-change` | Re-runs this skill when behavior changes |
