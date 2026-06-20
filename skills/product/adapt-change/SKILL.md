---
description: |
  Re-propagation engine for change. Takes a change, computes the affected scope from
  work/traceability.json (downstream transitive closure → opus judgment → human confirm), re-runs
  ONLY the affected skills, and checks coherence. Minimal re-run, reversible.
  /product:adapt-change --change="<text>" [--type=constraint|market|competitor|tech|regulation] [--auto] [--lang=ja|en].
model: opus
user_invocable: true
---

# Adapt to Change (Re-propagation Engine)

## Desired Outcome

Apply a change to an existing product design with **minimal, reversible** re-runs:

1. **Change log** — `reports/05_adaptation/change-log.md`: the change (description, `--type`,
   timestamp) and a **before/after diff summary** for every re-run artifact (for reversibility).
2. **Impact analysis** — `reports/05_adaptation/impact-analysis.md`: "change → impacted ID →
   re-evaluate? + reason", i.e. the candidate blast radius after the judgment pass.
3. **Updated artifacts** — the affected skills re-run with existing artifacts as input, and the
   corresponding edges in `work/traceability.json` updated.

## Invocation

```
/product:adapt-change --change="<text>" [--type=constraint|market|competitor|tech|regulation] [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--change="<text>"` | **Required** | What changed (free text) |
| `--type=...` | Recommended | Where the change enters the graph: constraint / market / competitor / tech / regulation |
| `--auto` | Optional | Skip the human confirmation step (apply the judged impact set directly) |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Minimal re-run.** Never touch a skill the change does not reach. The graph proposes the
  candidate set; the judgment pass decides whether each upstream reference still holds.
- **Deterministic candidates, judged scope.** Step 2 (transitive closure) is pure graph work;
  step 3 (opus) expands/shrinks it with recorded reasons.
- **Reversibility.** Record a before/after diff summary for every rewritten artifact.
- **Human checkpoint.** Confirm the impact set before rewriting anything (unless `--auto`).
- **Stop condition**: change logged, impact set judged and confirmed, affected skills re-run,
  `traceability.json` updated, and `review` run for coherence.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `--change` | **Required** | User | block with a message — nothing to propagate |
| `work/traceability.json` | Required | all prior skills | block with a message — the engine reads only this |
| existing artifacts | Required | prior skills | block — there must be a design to adapt |

## Process

1. **Intake** — record the change in `change-log.md` (description, `--type`, timestamp passed in).
   Apply `@rules/product/adaptation-engine.md`.
2. **Candidate blast radius (deterministic)** — seed from the `--type` hint, then walk
   `traceability.json` `upstream` edges in reverse to get the downstream transitive closure.
3. **Judgment pass (opus)** — for each candidate decide if its upstream reference still holds;
   expand/shrink the set; write "change → impacted ID → re-evaluate? + reason" to
   `impact-analysis.md`.
4. **Confirm** — present the impact set via `AskUserQuestion` (skip under `--auto`).
5. **Minimal re-run** — re-run only the confirmed affected skills with existing artifacts as input;
   record before/after diffs; update the affected edges in `traceability.json`.
6. **Coherence check** — invoke `/product:review` (consistency + traceability lenses) to catch
   contradictions introduced by the re-propagation.
7. **Record** — finalize both files; append the change summary to `work/context.md`.

## Output

`reports/05_adaptation/change-log.md`, `reports/05_adaptation/impact-analysis.md`, the re-run
artifacts, and an updated `work/traceability.json`.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/adaptation-engine.md` | Edge store, transitive-closure + judgment algorithm, principles |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:review` | Downstream — runs the coherence check after re-propagation |
| `/product:validate-assumptions` | Related — a change may re-open the gate |
| any pipeline skill | Re-invoked selectively as the confirmed impact set requires |
