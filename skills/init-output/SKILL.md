---
description: |
  Initialize output directories and pipeline-progress.json.
  /architect:init-output [project_name]. Use --reset to reinitialize.
model: haiku
user_invocable: true
---

# Output Initialization

## Expected Outcome

Create the directory structure and progress management files required for pipeline execution.

## Existing State Is Never Discarded

This skill is **additive**. A project may already carry state when it runs — most often
because the `product` pipeline ran first and this is the product→architect handoff
(@docs/design.md §1.1–1.5), but equally on any re-run of the architect path. Read each file
before writing it and merge into what is there. Only `--reset` replaces anything, and only
after a backup.

What is at stake: `work/context.md` is the product-side Open Questions store
(@rules/open-questions.md §6) that `/architect:define-requirements` reads in its Step 2 to
re-ask the `deferred` / `unasked` entries it needs; `work/pipeline-progress.json` is shared
by both pipelines and already holds the product phases and the `output_language` the user
chose during the product run.

## Execution Steps

1. Create the following directories:
   - `reports/before/{project}/`
   - `reports/00_summary/`
   - `reports/01_analysis/`
   - `reports/02_evaluation/`
   - `reports/03_design/`
   - `reports/review/individual/`
   - `generated/`
   - `work/`

2. Create **or merge** `work/pipeline-progress.json`:

   - **Absent** — create it, registering every phase from
     `@skills/common/skill-dependencies.yaml` as `"pending"`, each with the fields defined in
     @skills/common/progress-registry.md.
   - **Present** — keep the file and add only the phase entries it does not already have, as
     `"pending"`. Never reset an entry that exists, never remove a phase this manifest does
     not define (the product pipeline registers its own phases in the same file), and leave
     `gates`, `errors`, `warnings` and any other top-level key untouched.
   - `options` — keep every value already set, in particular `output_language`, which the
     product run may have asked the user for. Fill in only what is missing: `output_language`
     defaults to `"en"`, `confirm_versions` to `true` (whether codegen skills confirm resolved
     dependency versions with the user — see @rules/dependency-versions.md).
   - **Colliding phase names.** Four names are defined by *both* manifests — `map-domains`,
     `design-api`, `create-domain-story`, `report` — and the registry keys phases by bare
     name, so an existing entry under one of them may describe the **product** phase rather
     than this one. Leave it exactly as it is, and append one line to `warnings[]` for each
     such name found already `completed`, naming it and stating that its status may belong to
     the product pipeline and that the architect phase is therefore unverified. The status
     dashboard renders `warnings[]`, so the ambiguity is visible instead of reading as done.

3. Create `work/context.md` **only if it is absent**. If it exists, leave its content in
   place: phases append to it, and on the handoff path it carries the product Open Questions
   table that `/architect:define-requirements` is about to read.

## Options

- `--reset`: Back up the existing `work/pipeline-progress.json` (copy to `*.bak`), then
  re-register **this manifest's** phases as `"pending"` — phases belonging to the product
  pipeline are still preserved. `--reset` does not touch `work/context.md` or
  `work/traceability.json`; both are shared with the product pipeline.

## Completion Criteria

The directory structure and `work/pipeline-progress.json` exist, every architect phase has an
entry, and no pre-existing phase entry, option value, or `work/context.md` content was lost.
