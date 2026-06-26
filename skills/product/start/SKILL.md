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
- **Implementation status**: all phases in the dependency manifest are implemented (`implemented:
  true`). Should a phase ever be marked `implemented: false`, tell the user it is not yet available
  and skip it (do not fabricate its output).
- **UX-phase visual track** (`full` profile): after `design-positioning`, run the two optional
  artifacts that feed the mocks — `create-domain-story` (the *what*: per-persona screen flow) and
  `design-system` (the *how it looks*: shared visual language) — before `generate-ui-mock`.

## Execution Flow

1. Read `@skills/product/common/skill-dependencies.yaml` to get phase order and the
   `implemented` flag.
2. Run `/product:init-output` to create the output tree and state files.
3. Execute implemented skills in dependency order. After each phase, update
   `work/pipeline-progress.json` and append key decisions to `work/context.md`.
4. **Validation gate** — after Phase 1 (`define-vision`, `define-scope`), run
   `/product:validate-assumptions`. Read its verdict from `pipeline-progress.json` → `gates`:
   - `no-go`: stop forward progress and help the user revise Phase 1 artifacts (a forward
     iteration, not a failure). Re-run the gate after revision.
   - `go`: proceed to the next phase.
5. **Design-system step (UX phase)** — in the `full` profile, after `design-positioning` and
   before `generate-ui-mock`, run `create-domain-story` then `/product:design-system`.
   `design-system` writes to `design-system/{name}/` (not `reports/`) and sets
   `options.design_system` in `pipeline-progress.json` so the mocks inject `tokens.css`. Mode:
   - `--auto`: build a neutral, accessible default system (or `--import=<path>` when the user
     supplied one); never fabricate brand values — unknowns become `TBD`.
   - interactive: offer **build** (derive tokens from positioning/personas) vs **incorporate**
     (`--import` an existing Tailwind / DTCG / Figma Tokens / CSS theme).
   If skipped, `generate-ui-mock` falls back to its built-in defaults.
6. Skip phases whose prerequisites are absent (consumer treats a skipped/absent input as `TBD`).

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

`design-architecture` additionally emits a technology-fitness assessment
(`reports/03_domain/tech-stack-fitness.md`); a ScalarDB / ScalarDL **Adopt** there bridges directly
to `/architect:select-scalardb-edition` → `/architect:design-scalardb` (and
`/architect:design-scalardb-analytics`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:init-output` | Initialization (called automatically) |
| `/product:define-vision` | First phase — product core |
| `/product:validate-assumptions` | Validation gate after Phase 1 |
| `/product:create-domain-story` | UX phase — persona-anchored domain stories (the axis for UI mocks) |
| `/product:design-system` | UX phase — separately-managed design system (the visual language for UI mocks) |
| `/architect:define-requirements` | Downstream handoff to system design |
