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
   re-evaluate? + reason", i.e. the candidate blast radius after the judgment pass, plus an
   `## Architect-Side Impact` section listing every affected architect-owned ID and the skill
   that owns it — reported, never re-run here (see Decision Criteria).
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
- **The architect boundary is a reporting boundary, not a blind spot.** After a handoff
  `traceability.json` holds architect nodes too (`FR-` derived from `FEAT-`, architect-originated
  `NFR-`, the physical-only nodes — @docs/design.md §1.5), so the closure in step 2 legitimately
  reaches them. This skill **names them and stops**: it never rewrites an artifact under
  `reports/00_requirements/` or any other architect output, and never invokes an architect skill.
  Re-running system design is the user's call, made with `/architect:*` — a product-side change
  is not authority to rewrite requirements or architecture documents.
- **Stop condition**: change logged, impact set judged and confirmed, affected **product** skills
  re-run, `traceability.json` updated, `review` run for coherence, and any architect-owned impact
  reported with the skill that owns it.

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
4. **Split the set at the plugin boundary.** Partition the confirmed candidates into
   **product-owned** and **architect-owned** using each node's `skill` field (and its
   `source_file` — anything under `reports/00_requirements/` or a later architect directory is
   architect's). Only the product side is re-run below.
5. **Confirm** — present the impact set via `AskUserQuestion`, with the architect-owned items
   shown as *reported, not re-run* so the user sees what will and will not be touched (skip under
   `--auto`).
6. **Minimal re-run** — re-run only the confirmed affected **product** skills with existing
   artifacts as input; record before/after diffs; update the affected edges in
   `traceability.json`.
7. **Coherence check** — invoke `/product:review` (consistency + traceability lenses) to catch
   contradictions introduced by the re-propagation. When the impact set crossed the boundary,
   the @docs/design.md §1.5 cross-plugin check applies as well: every `FR-` still reachable from
   a `FEAT-`, no product `NFR-` re-numbered, no `upstream` ID left dangling across the boundary
   by this re-run. A break there is a finding, reported — not repaired by rewriting architect's
   side of it.
8. **Report the handoff-forward work** — write a `## Architect-Side Impact` section in
   `impact-analysis.md`: one row per architect-owned ID (ID, artifact, why the change reaches it,
   the owning skill from its `skill` field) and the command to act on it, typically
   `/architect:define-requirements --input=<the re-run product reports>` for `FR-`/`NFR-`, or the
   later architect skill named on the node. State plainly that nothing on that side was modified.
   When the set is empty, say so — an explicit "the change does not cross the boundary" is what
   makes its absence trustworthy.
9. **Record** — finalize both files; append the change summary to `work/context.md`.

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
| any **product** pipeline skill | Re-invoked selectively as the confirmed impact set requires |
| `/architect:define-requirements` | Boundary — architect-owned impact is reported for the user to act on with this (or the later architect skill named on the node), never re-run from here |
