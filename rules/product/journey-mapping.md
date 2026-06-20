# Rules: Customer Journey Mapping (map-journey)

Reference for `/product:map-journey`. Map each **primary persona's** journey as a grid of
**stages × layers**, grounded in the persona's jobs and verbatim emotions — not an idealized
marketing funnel.

## Stages (columns)

A default end-to-end spine (adapt to the product):

Awareness → Consideration → Purchase/Sign-up → Onboarding → Usage → Renewal/Retention → Advocacy

Each persona may have its own stage set; one map per primary persona at minimum.

## Layers (rows) — for every stage

- **Touchpoints / channels** — where the interaction happens (web, app, email, sales, support)
- **Actions** — what the persona does to make progress on the job
- **Thoughts & emotions** — captured **verbatim** where possible (quotes), plus an emotion curve
  (high/neutral/low) so the dip is visible
- **Pain points** — friction, drop-off risk, unmet expectation
- **Opportunities** — how the product could remove the pain or amplify a gain

## Moments of Truth (MoT)

Flag the decisive moments along the journey:

- **ZMOT** (Zero) — pre-purchase research before reaching your touchpoints
- **FMOT** (First) — the first direct encounter / first impression
- **SMOT** (Second) — the actual usage experience that confirms or breaks the promise
- (Optional) **UMOT** — the user shares their experience → feeds Advocacy

Mark where the emotion curve dips at a MoT — these are the highest-leverage fix points.

## Discipline

- Tie every Pain/Opportunity back to a `JOB-`/`PER-` id so the map stays grounded.
- Do not invent emotions; mark assumed entries **[proto]** until validated.
- The output of mapping is a prioritized list of **opportunities**, not a pretty diagram.

## ID convention

Each journey (per persona) and each notable opportunity gets a `JNY-xxx` id; append to
`work/traceability.json` with Upstream `PER-`/`JOB-` references. Opportunities feed
`design-positioning` (touchpoints) and later `define-features`.

## Sources

- Nielsen Norman Group — Journey Mapping 101 (stages × lanes)
- P&G / Google — Moments of Truth (FMOT/SMOT) and ZMOT
