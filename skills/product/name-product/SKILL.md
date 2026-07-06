---
description: |
  Name the product as an alphabetic acronym — a short, pronounceable Latin-letter name whose every
  letter is the initial of an English word, so the name itself expands into a phrase that states the
  product's value. Grounded in vision/values/positioning; shortlists candidates and recommends one.
  /product:name-product [target] [--input=<file|dir>] [--count=N] [--style=acronym|initialism|hybrid] [--seed=<letters|word>] [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# Product Naming (Acronym / Backronym)

## Desired Outcome

Produce a product name that is **spelled in the Latin alphabet** and in which **every letter is the
first letter of an English word**, so the name doubles as a phrase describing the product. Deliver:

- **Product Name** — `reports/00_core/product-name.md`
  - A **word bank**: English candidate words grouped by initial letter, drawn from the product's
    vision, values, differentiators, and domain (each word tagged with the theme it expresses)
  - **Candidate names** (default 5): each is a short pronounceable string plus its **full expansion**
    — one English word per letter — and a one-line read of what the expansion asserts
  - A **screening table** scoring each candidate on the naming criteria (distinct, short,
    pronounceable, appropriate, expandable, protectable)
  - A **shortlist of 3** and **one recommended name** with rationale traced to `VIS-` IDs
  - **Availability checks** listed as Open Questions — never asserted as cleared
  - Each candidate and the recommendation carry a `NAM-` ID

The name is not decoration: it flows into the PR-FAQ heading, the positioning canvas, and every UI
mock, so it must survive the same value story those artifacts tell.

## Invocation

```
/product:name-product [target] [--input=<file|dir>]... [--count=N] [--style=acronym|initialism|hybrid] [--seed=<letters|word>] [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `target` | Optional | Product idea / working name to re-name or theme to seed from |
| `--input=<file\|dir>` | Optional, repeatable | Brief, brand notes, glossary, prior docs |
| `--count=N` | Optional | Number of candidate names to generate (default 5) |
| `--style` | Optional | `acronym` = pronounced as a word (NEXUS); `initialism` = spelled out letter-by-letter (SDK); `hybrid`. Default `acronym` |
| `--seed=<letters\|word>` | Optional | Fix letters or backronym a given base word (e.g. `--seed=SCALAR` finds a word per letter) |
| `--auto` | Optional | Skip elicitation; generate from inputs only. Unknowns → `TBD` |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **The constraint is absolute**: every letter of the final name maps to exactly one English word,
  and the per-letter words together read as a coherent phrase about the product. A candidate with a
  broken, forced, or nonsensical expansion is rejected, however nice it sounds.
- **Pronounceable and short** (`acronym` style): aim for 4–6 letters, ≤3 syllables, one obvious
  reading. `initialism` style may be shorter (2–4 letters) but must still expand.
- **Appropriate, not generic**: the expansion should describe *this* product's differentiation, not
  a category truism ("Fast Reliable Efficient System" describes everything → reject).
- **Grounded, never fabricated**: expansion words come from the product's own vision/values/
  positioning vocabulary. Do **not** claim a name, domain, or trademark is available — availability
  is verified externally and logged to Open Questions.
- **Stop condition**: `--count` candidates exist, each with a valid full expansion and a screening
  score; a shortlist of 3 and one recommendation with rationale are written.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/00_core/vision-mission-value.md` | Recommended | `/product:define-vision` | elicit vision/values inline, or `TBD` |
| `reports/01_ux/positioning.md` | Optional | `/product:design-positioning` | proceed; use vision vocabulary only |
| `reports/01_ux/personas.md` | Optional | `/product:generate-persona` | proceed without tone cues |
| `reports/00_core/scope-definition.md` | Optional | `/product:define-scope` | proceed |
| `work/pipeline-progress.json` | Recommended | `/product:init-output` | ask for `output_language` |

## Process

1. **Read context** — load `--input`, the vision/values, positioning, personas, scope, and
   `work/traceability.json`. Extract the load-bearing value keywords and differentiators, each with
   its `VIS-`/`POS-` source.
2. **Elicit (gap-driven, skip on `--auto`)** — confirm tone (technical vs. friendly), any letters/
   words the user wants included or avoided, and language of the name (names stay Latin-alphabet even
   when `--lang=ja`).
3. **Build the word bank** — for each theme keyword, list strong English words and record each word's
   initial letter and the theme it expresses. This is the raw material for expansions.
4. **Generate candidates** — apply `@rules/product/naming-frameworks.md`. Work both directions:
   forward (assemble initials from value words into a pronounceable string) and backward (pick a
   pronounceable string, then fit one English word per letter from the bank). Honor `--seed`.
   Produce `--count` candidates, each with a **complete letter-by-letter expansion**.
5. **Screen** — score each candidate on the six naming criteria; drop any with a forced or generic
   expansion. Note pronunciation and syllable count.
6. **Availability** — list the exact checks to run (trademark class, `.com`/domain, app-store,
   collision with the word bank's own competitors) as **Open Questions**; never mark them cleared.
7. **Shortlist & recommend** — pick 3, then 1, with rationale that cites the `VIS-` IDs the expansion
   satisfies. Assign `NAM-` IDs.
8. **Append traceability** — for each `NAM-` node add `{id, type:"name", title, skill:"name-product",
   source_file, upstream:[VIS-…, POS-…]}` to `work/traceability.json`.
9. **Record** — write `reports/00_core/product-name.md`; append the recommendation to
   `work/context.md`; log availability checks and any `TBD` to Open Questions.

## Output

`reports/00_core/product-name.md` — word bank, candidate table with full expansions, screening
scores, shortlist, one recommended name, a `NAM-` ID table with an Upstream column, and an Open
Questions block for availability. The name string itself is always Latin-alphabet regardless of
`output_language`; surrounding prose follows the configured language.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/naming-frameworks.md` | Acronym/backronym construction + naming quality criteria |
| `@rules/product/vision-frameworks.md` | Source of the value vocabulary the expansion must express |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-vision` | Upstream — supplies the vision/values the expansion encodes |
| `/product:design-positioning` | Upstream (soft) — differentiation vocabulary; consumes the chosen name |
| `/product:generate-ui-mock` | Downstream — the name appears across the mocks |
| `/product:adapt-change` | Re-runs this skill when the vision or positioning shifts |
