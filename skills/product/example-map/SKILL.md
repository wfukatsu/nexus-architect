---
description: |
  Run Example Mapping per feature — the business rules the feature must obey (RULE-), one concrete
  example per rule on each side of its boundary (EX-), and the questions nobody could settle (OQ-)
  — so acceptance tests, aggregate invariants and backlog acceptance criteria derive from agreed
  cases instead of from the feature's name. Runs after define-features, before the data model,
  the aggregates and the test specs.
  /product:example-map [--feature=<FEAT>] [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# Example Mapping

## Desired Outcome

Produce one deliverable per feature:

1. **Example map** — `reports/02_spec/examples/example-map-{feat}.md` (`RULE-` and `EX-` IDs):
   the feature as the story, every business rule it must obey, at least one positive and one
   negative concrete example per rule, and the questions the session could not settle, recorded
   in the shared Open Questions store under their `OQ-` IDs.

Plus one index, `reports/02_spec/examples/index.md`, listing each mapped feature with its rule
count, example count, open-question count and size verdict — the view a reader uses to see which
features are understood and which are still arguments.

The method, the four cards and the session discipline are @rules/product/example-mapping.md.
Read it before the first session; this skill facilitates it, it does not restate it.

## Invocation

```
/product:example-map [--feature=<FEAT>] [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--feature=<FEAT>` | Optional | Map this feature only (`FEAT-` id). Defaults to every Must and Should feature in `feature-list.md`, in priority order, selected interactively |
| `--auto` | Optional | Harvest rules and examples from the artifacts without a session; every rule with no harvestable example becomes an `OQ-` recorded `unasked` (@rules/open-questions.md §5) |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Every rule has an example on each side.** A rule with no negative example has not located its
  boundary; a rule with no positive example has not been shown to be satisfiable. Both are
  findings, not omissions.
- **Every example illustrates exactly one rule.** An example that needs two rules is two examples;
  an example that illustrates none is an unwritten rule.
- **Concrete, not schematic.** `20 EUR credit, 25 EUR order, rejected: insufficient-credit` — an
  example a domain expert can call wrong.
- **Harvest before asking.** Rules the mocks, the scope, the data model and the domain stories
  already state are presented as candidates, never asked from scratch (@rules/open-questions.md
  §1). Questions already in `work/context.md` are re-asked under their existing `OQ-`.
- **Size is a verdict.** More than roughly 6–8 rules, or a session that overruns, means the
  feature is too big; the map says so and names the seam, and `define-features` /
  `adapt-change` own the split. This skill never edits `feature-list.md`.
- **Stop condition**: every selected feature has a map, every rule has at least one positive and
  one negative example, every example names its rule, every unsettled point is an `OQ-` with an
  owner, and `RULE-` / `EX-` nodes are in the graph.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/02_spec/feature-list.md` | Required | `/product:define-features` | **stop and report** — there is no story to map |
| `reports/02_spec/ui-mocks/` | Recommended | `/product:generate-ui-mock` | UI-enforced rules are not harvested; asked instead |
| `reports/00_core/scope-definition.md`, `constraints.md` | Recommended | `/product:define-scope` | external rules (`CON-`) are not harvested |
| `reports/01_ux/domain-stories/` | Optional | `/product:create-domain-story` | exception scenarios are not harvested as negative examples |
| `reports/02_spec/data-model.md` | Optional | `/product:define-data-model` | structural rules (cardinality, required attributes) are not harvested — on a rerun after the data model exists, they are |
| `reports/01_ux/journey-maps.md` | Optional | `/product:map-journey` | pains at Moments of Truth are not harvested as rule candidates |
| `work/context.md` § Open Questions | Recommended | every prior skill | questions are minted fresh instead of re-asked |

## Process

1. **Read context** — feature list, mocks, scope, stories, data model, `work/traceability.json`,
   and the Open Questions store. If `feature-list.md` is empty, stop and report.
2. **Select stories** — honor `--feature`; otherwise present the Must/Should features with
   `multiSelect: true` in priority order and let the user pick (all of them under `--auto`).
3. **Harvest candidates** per story — rules and examples the artifacts already imply, each with
   its `source` (@rules/product/example-mapping.md § Where rules come from): the feature's own
   description and screen, the mocks' validation and disabled states, `scope-definition.md` /
   `constraints.md`, the domain stories' exception scenarios, the data model's cardinalities, and
   the journey's pains at its Moments of Truth.
4. **Run the session** per story (@rules/product/example-mapping.md § Running the session):
   confirm / correct / add rules; for every rule ask for the example that breaks it and the one
   that satisfies it; for every volunteered example name its rule; record what stays open as an
   `OQ-` with owner and options, reusing an existing ID where the question already exists.
   Batch questions (1–4 per `AskUserQuestion` call), and keep each story inside two rounds.
5. **Size verdict** — rule count, overrun, and the seam when the story should split.
6. **Write** — one map per story and the index, immediately, not batched at the end.
7. **Append traceability** — add `RULE-` nodes (`upstream: [FEAT-…]` plus any `CON-` / `SCP-` /
   `ENT-` the rule derives from) and `EX-` nodes (`upstream: [RULE-…]`) to
   `work/traceability.json`, IDs allocated `max + 1` over the graph per prefix.
8. **Record** — append decisions to `work/context.md`; update the Open Questions store in place
   (@rules/open-questions.md §6–7).

## Output

`reports/02_spec/examples/example-map-{feat}.md` per feature (`{feat}` is the lower-cased
`FEAT-` id, e.g. `feat-012`), and `reports/02_spec/examples/index.md`.

### Output Document Structure

```markdown
---
title: "Example Map: {Feature title}"
schema_version: 1
phase: "Phase 3: UX -> Spec"
skill: example-map
generated_at: "ISO8601"
feature: "FEAT-012"
mode: "interactive|auto"
input_files:
  - reports/02_spec/feature-list.md
---

# Example Map: {Feature title}

## Story

**FEAT-012** — [the feature as `feature-list.md` states it, verbatim; its screen and MoSCoW]

## Rules

| ID | Rule | Source | Examples |
|----|------|--------|----------|
| RULE-001 | An order cannot exceed the customer's available credit | scope-definition.md CON-004 | EX-001, EX-002 |
| RULE-002 | An order has at least one line | data-model.md ENT-004 | EX-003, EX-004 |

## Examples

| ID | Rule | Kind | Given | When | Then |
|----|------|------|-------|------|------|
| EX-001 | RULE-001 | positive | customer with 100 EUR credit | orders 25 EUR of goods | order placed; OrderPlaced |
| EX-002 | RULE-001 | negative | customer with 20 EUR credit | orders 25 EUR of goods | rejected: insufficient-credit |
| EX-003 | RULE-002 | positive | cart with one line | place order | order placed |
| EX-004 | RULE-002 | negative | empty cart | place order | rejected: order-empty |

## Questions

| OQ | Question | Status | Owner |
|----|----------|--------|-------|
| OQ-007 | Is a 10% overdraft allowed on trade accounts? | deferred | Head of Sales |

## Size Verdict

[Rule count, whether the session overran, and — when the story should split — the seam and the
rules that go with each half. "Fits" when it fits.]

## Findings for Upstream

[A `FEAT-` that turned out to be two, a rule that contradicts `scope-definition.md`, a mock that
enforces a rule the room rejected — reported here for `define-features` / `adapt-change`, never
edited from this skill.]
```

## Handoff

| Consumer | What it takes |
|----------|---------------|
| `/architect:generate-test-specs` | Each `RULE-` becomes a `Rule:` block and each `EX-` a `Scenario:` in the feature's `.feature` file, annotated with its ID — Gherkin generated from agreed cases, not from the feature's name |
| `/architect:design-aggregate` | `RULE-` entries mapped to an aggregate's commands are its invariant candidates; their `EX-` entries are the invariant's first concrete examples |
| `/architect:design-state-machine` | A rule of the form "X only before / after Y" is a matrix cell; the skill cites the `RULE-` |
| `/architect:export-backlog` | Each `RULE-` is an acceptance criterion on the feature's Issue, with its `EX-` scenarios inside the box |
| `/architect:define-requirements` | An `FR-` derived from a `FEAT-` carries that feature's `RULE-` entries as its acceptance criteria |
| `/product:review` (traceability lens) | Every Must/Should `FEAT-` has a map; every `RULE-` has both example kinds; every `EX-` names one rule |

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/example-mapping.md` | The four cards, harvesting sources, the session, discipline, ID convention |
| `@rules/open-questions.md` | Asking, recording and re-asking what the session could not settle |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:define-features` | Upstream — the stories; also the owner of any split this skill recommends |
| `/product:generate-ui-mock` | Upstream — UI-enforced rules are harvested as candidates |
| `/product:define-scope` | Upstream — external constraints are rule candidates |
| `/product:create-domain-story` | Upstream — exception scenarios are negative-example candidates |
| `/product:define-data-model` | Downstream (and upstream on rerun) — structural rules confirm cardinalities and required attributes |
| `/architect:design-aggregate` | Downstream — rules become invariants, examples their concrete cases |
| `/architect:generate-test-specs` | Downstream — rules and examples become the Gherkin |
| `/architect:export-backlog` | Downstream — rules become acceptance criteria |
| `/product:adapt-change` | Re-runs this skill for the features a change reaches |
