---
description: |
  Initialize the product-direction output tree, pipeline progress file, and the
  traceability graph used by adapt-change.
  /product:init-output [project_name]. Use --reset to reinitialize.
model: sonnet
user_invocable: true
---

# Output Initialization

## Expected Outcome

Create the directory structure and state files required to run the `product` pipeline.

## Existing State Is Never Discarded

This skill is **additive**. All three state files are shared — `work/pipeline-progress.json`
holds both pipelines' phases, `work/traceability.json` is the single trace graph that
`/architect:define-requirements` appends its `FR-` / `NFR-` nodes to (@docs/design.md §1.5),
and `work/context.md` is the Open Questions store both plugins read. Read each before writing
it and merge into what is there; only `--reset` replaces, and only after a backup.

## Execution Steps

1. Create the following directories (only those that do not yet exist):
   - `reports/00_core/`
   - `reports/01_ux/`
   - `reports/01_ux/domain-stories/`
   - `reports/02_spec/ui-mocks/`
   - `reports/03_domain/`
   - `reports/04_quality/`
   - `reports/05_adaptation/`
   - `reports/report/`
   - `work/`

2. Create **or merge** `work/pipeline-progress.json` with this schema, registering every phase
   from `@skills/product/common/skill-dependencies.yaml` as `"pending"`. When the file already
   exists, add only the entries it lacks — never reset an existing entry, never remove a phase
   this manifest does not define (the architect pipeline registers its own phases in the same
   file), keep every `options` value already set, and leave other top-level keys untouched.
   Every entry this skill creates carries `"plugin": "product"` — with both pipelines in one
   file, that field is what makes an entry attributable (@skills/common/progress-registry.md).
   `map-domains`, `design-api`, `create-domain-story` and `report` are defined by **both**
   manifests and the registry keys phases by bare name, so an existing entry under one of
   those names may be the architect phase: leave it as it is — never relabel it `product` —
   and append a line to `warnings[]` for each one found already `completed` with no `plugin`
   field to settle it.

   ```json
   {
     "schema_version": 1,
     "options": { "output_language": "en", "confirm_versions": true, "no_research": false, "profile": "full", "design_system": null, "frontend": null },
     "phases": {
       "define-vision": { "status": "pending", "plugin": "product", "started_at": null, "completed_at": null, "updated_at": null, "note": null, "outputs": [] }
     },
     "gates": { "validate-assumptions": { "verdict": "pending", "open_assumptions": [] } }
   }
   ```

   Phase entries follow the shared contract in @skills/common/progress-registry.md — in
   particular `status: "in_progress"` + `started_at` are written *before* a phase runs, which
   is what `/product:report-status` and the token-usage hook read.

   Ask the user which `output_language` to use (`en` default / `ja`) unless it is already set
   or passed via `--lang`. `confirm_versions` (default `true`) controls whether
   `/product:generate-frontend` confirms the dependency versions it resolves before pinning them —
   see @rules/dependency-versions.md.

3. Initialize `work/traceability.json` **only if it is absent**, as an empty graph — this is
   what makes `/product:adapt-change` work; every skill appends to it:

   ```json
   { "schema_version": 1, "nodes": [] }
   ```

   If it already exists, keep it and its `nodes` as they are. It is the single trace graph
   for the project: `/architect:define-requirements` appends `FR-` / `NFR-` nodes to this same
   file (@docs/design.md §1.5), and truncating it to `[]` would sever the cross-plugin chain.

4. Create `work/context.md` **only if it is absent**, carrying decisions between phases and
   seeded with an empty `## Open Questions` section — the Open Questions store every skill
   appends to (row shape in @rules/open-questions.md §6):

   ```markdown
   ## Open Questions

   | ID | Question | Status | Answer | Options offered | Owner | Impact | Asked at |
   |----|----------|--------|--------|-----------------|-------|--------|----------|
   ```

   If it exists, leave its content in place and only append the `## Open Questions` header
   when the file does not already have one.

## Options

- `--reset`: Back up existing `work/pipeline-progress.json` and `work/traceability.json`
  (copy to `*.bak`) before reinitializing. Reinitializing re-registers **this manifest's**
  phases as `"pending"` and preserves any architect phases and any architect-written
  traceability nodes; `work/context.md` is not touched.

## Completion Criteria

The directory tree, `work/pipeline-progress.json`, `work/traceability.json`, and
`work/context.md` all exist, the last with its `## Open Questions` table header in place, and
no pre-existing phase entry, option value, traceability node, or `context.md` content was lost.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:start` | Calls this automatically before running phases |
