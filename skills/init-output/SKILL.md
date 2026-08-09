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

What is at stake: `work/context.md` is **the** Open Questions store for the whole project — both
pipelines' questions, in one file (@rules/open-questions.md §6) — which
`/architect:define-requirements` reads in its Step 2 to re-ask the `deferred` / `unasked` entries
it needs and answer them in place; `work/pipeline-progress.json` is shared
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
     @skills/common/progress-registry.md — including `"plugin": "architect"`, which is what
     makes an entry attributable once both pipelines share the file.
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
     than this one. Leave it exactly as it is. If it carries `"plugin": "product"` the
     question is settled and there is nothing to report; if it carries no `plugin` at all
     and is already `completed`, append one line to `warnings[]` naming it and stating that
     its status may belong to the product pipeline, so the architect phase is unverified.
     The status dashboard renders `warnings[]`, so the ambiguity is visible instead of
     reading as done. **Never add `"plugin": "architect"` to an entry you did not create** —
     that would claim the neighbour's work as this pipeline's.

3. Create `work/context.md` **only if it is absent**, seeded with an empty `## Open Questions`
   section in the @rules/open-questions.md §6 row shape. If it exists, leave its content in
   place: phases append to it, and it is **the** Open Questions store for the whole project —
   both pipelines' questions live in this one file, so on the handoff path it already holds the
   entries `/architect:define-requirements` is about to read, re-ask and answer in place.
   `reports/00_requirements/open-questions.md` is a view rendered from it, never a second store.

## Options

- `--reset`: Back up the existing `work/pipeline-progress.json` (copy to `*.bak`), then
  re-register **this manifest's** phases as `"pending"` — phases belonging to the product
  pipeline are still preserved. `--reset` does not touch `work/context.md` or
  `work/traceability.json`; both are shared with the product pipeline.

## Completion Criteria

The directory structure and `work/pipeline-progress.json` exist, every architect phase has an
entry, and no pre-existing phase entry, option value, or `work/context.md` content was lost.
