# Rules: Adaptation / Re-propagation Engine (adapt-change)

Reference for `/product:adapt-change`. The engine takes a change, computes the affected scope from
`work/traceability.json`, has a human (or `--auto`) confirm it, re-runs **only** the affected
skills, and checks coherence. The principle is **minimal re-run** — never touch a skill the change
does not reach.

## `work/traceability.json` — the edge store

Every skill appends its IDs here as its final step, so the engine only needs to read this one file.

```jsonc
{
  "schema_version": 1,
  "nodes": [
    { "id": "FEAT-012", "type": "feature", "title": "...", "skill": "define-features",
      "source_file": "reports/02_spec/feature-list.md",
      "upstream": ["JOB-003", "JNY-005", "NSM-001"] }
  ]
}
```

`upstream` points to the nodes a node derives from; the **downstream** direction (who depends on
me) is the reverse of `upstream` and is what propagation follows.

## Engine steps (design.md §7.2)

1. **Intake** — record the change in `change-log.md` (description, `--type`, timestamp passed in).
2. **Candidate blast radius (deterministic)** — find the nodes the change directly touches, then
   compute their **downstream transitive closure** by walking `upstream` edges in reverse. This is
   pure graph work — no judgment yet; it only proposes candidates.
3. **Judgment pass (opus)** — examine each candidate and decide whether its upstream reference
   *still holds* despite the change, **expanding or shrinking** the set. The graph proposes; the
   judgment pass decides. Record "change → impacted ID → re-evaluate? + reason" in
   `impact-analysis.md`.
4. **Human confirmation** — present the confirmed impact set via `AskUserQuestion` (skipped under
   `--auto`).
4b. **Split at the plugin boundary** — after a handoff the graph holds architect's nodes too
   (`FR-`, architect-originated `NFR-`, the physical-only nodes), so the closure reaches them by
   design. Partition the confirmed set by each node's `skill` field, corroborated by its
   `source_file` (`reports/00_requirements/…` and later architect directories are architect's).
5. **Minimal re-run** — re-run only the confirmed affected **product** skills, feeding existing
   artifacts as input, and update the corresponding edges in `traceability.json`. Architect-owned
   nodes are never re-run and their artifacts are never rewritten here (design.md §7.5).
6. **Coherence check** — run `review` (consistency + traceability lenses) to catch contradictions
   introduced by the re-propagation; when the set crossed the boundary, the design.md §1.5
   cross-plugin check applies as well.
7. **Report the architect-side impact** — an `## Architect-Side Impact` section in
   `impact-analysis.md`: one row per architect-owned ID with its artifact, why the change reaches
   it, the owning skill, and the command to act on it. Say so explicitly when it is empty.

## Principles (§7.3)

- **Minimal re-run** — transitive closure + judgment prevents both over-reach (touching unaffected
  skills) and under-reach (missing a real dependent).
- **Reversibility** — `change-log.md` records a before/after diff summary for every re-run artifact,
  so a change can be understood and undone.
- **Human checkpoint** — the impact set is confirmed before any artifact is rewritten (unless
  `--auto`).
- **Idempotent edges** — after re-run, `traceability.json` reflects the new reality; re-running the
  same change is a no-op.

## Change types

`--type=constraint | market | competitor | tech | regulation` hints where the change enters the
graph (e.g. `constraint` → `CON-`/`SCP-`; `market`/`competitor` → market-landscape/positioning;
`regulation` → constraints/NFR). The hint seeds step 2's "directly touched" set. `RULE-` nodes sit
downstream of the `FEAT-` / `CON-` / `SCP-` / `ENT-` they derive from and `EX-` downstream of their
`RULE-`, so a constraint or feature change reaches the example map through the closure and
`example-map` is re-run for the affected features; an `EX-` that changes without its rule is a
finding, not a re-run.

## Sources

- design.md §7 (this plugin's adaptation engine specification)
