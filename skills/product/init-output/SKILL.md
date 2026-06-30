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

2. Initialize `work/pipeline-progress.json` with this schema (register every phase from
   `@skills/product/common/skill-dependencies.yaml` as `"pending"`):

   ```json
   {
     "schema_version": 1,
     "options": { "output_language": "en", "no_research": false, "profile": "full", "design_system": null, "frontend": null },
     "phases": {
       "define-vision": { "status": "pending", "outputs": [], "updated_at": null }
     },
     "gates": { "validate-assumptions": { "verdict": "pending", "open_assumptions": [] } }
   }
   ```

   Ask the user which `output_language` to use (`en` default / `ja`) unless it is already set
   or passed via `--lang`.

3. Initialize `work/traceability.json` as an empty graph — this is what makes
   `/product:adapt-change` work; every skill appends to it:

   ```json
   { "schema_version": 1, "nodes": [] }
   ```

4. Create `work/context.md` as an empty file (carries decisions between phases).

## Options

- `--reset`: Back up existing `work/pipeline-progress.json` and `work/traceability.json`
  (copy to `*.bak`) before reinitializing.

## Completion Criteria

The directory tree, `work/pipeline-progress.json`, `work/traceability.json`, and
`work/context.md` all exist.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:start` | Calls this automatically before running phases |
