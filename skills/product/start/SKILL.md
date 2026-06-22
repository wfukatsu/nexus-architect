---
description: |
  Interactively start product-direction design. Determines scope, runs the validation-driven
  pipeline in dependency order, and gates on the riskiest assumptions before deep design.
  /product:start [target] [--auto] [--profile=mvp|core-only|ux-to-spec|full] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# Product Goal Orchestrator

## Your Role

As the main orchestrator of the `product` plugin, evaluate the user's product idea, decide which
phases to run, and execute the implemented skills in dependency order — keeping the work
**validation-driven**: the strategy must state what it is betting on and how it will be tested,
not just produce internally consistent documents.

## Language Selection

Ask which language to use for output documents (English default / Japanese), unless `--lang` is
given. Record it in `work/pipeline-progress.json` under `options.output_language`.

## Workflow Selection

- Pick a profile (or honor `--profile`): `mvp` (vision + scope + validate — the smallest useful
  direction), `core-only`, `ux-to-spec`, `full`.
- **Implementation status**: all 21 product skills are implemented (`implemented: true` for every
  phase in the dependency manifest), so any profile — including `full` — runs end to end. Profiles
  scope *which* phases run, not what is available; they never skip a phase for being unimplemented.

## Execution Flow

1. Read `@skills/product/common/skill-dependencies.yaml` to get phase order and dependencies
   (all phases are `implemented: true`).
2. Run `/product:init-output` to create the output tree and state files.
3. Execute the selected profile's skills in dependency order. After each phase, update
   `work/pipeline-progress.json` and append key decisions to `work/context.md`.
4. **Validation gate** — after Phase 1 (`define-vision`, `define-scope`), run
   `/product:validate-assumptions`. Read its verdict from `pipeline-progress.json` → `gates`:
   - `no-go`: stop forward progress and help the user revise Phase 1 artifacts (a forward
     iteration, not a failure). Re-run the gate after revision.
   - `go`: proceed to the next phase.
5. Skip phases whose prerequisites are absent (consumer treats a skipped/absent input as `TBD`).

## Iteration (not waterfall)

- The validation gate and the post-Phase-2 synthesis checkpoint may amend earlier artifacts
  **within the forward pipeline**. Reserve `/product:adapt-change` for genuine external changes.

## Error Handling

On phase failure, present choices via AskUserQuestion: Retry / Skip and continue / Abort.
If a phase is skipped, downstream skills treat its output as absent (`TBD`), never empty.

## Context Management

For long runs, periodically update `work/context.md`: key decisions, open assumptions,
unresolved questions.

## Handoff

When `define-nfr` / `map-domains` / `design-api` artifacts exist, they can be handed to
`/architect:define-requirements --input=<reports/...>` for system implementation design (see the
mapping table in the design docs). Logical (product) vs physical (architect) split applies.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:init-output` | Initialization (called automatically) |
| `/product:define-vision` | First phase — product core |
| `/product:validate-assumptions` | Validation gate after Phase 1 |
| `/architect:define-requirements` | Downstream handoff to system design |
