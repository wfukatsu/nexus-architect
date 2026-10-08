---
description: |
  Interactively start product-direction design. Determines scope, runs the validation-driven
  pipeline in dependency order, and gates on the riskiest assumptions before deep design.
argument-hint: '[target] [--auto] [--profile=mvp|core-only|ux-to-spec|full] [--frontend|--no-frontend] [--lang=ja|en]'
model: inherit
---

# Product Goal Orchestrator

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

**Usage:** `/product:start [target] [--auto] [--profile=mvp|core-only|ux-to-spec|full] [--frontend|--no-frontend] [--lang=ja|en]`

## Your Role

As the main orchestrator of the `product` plugin, evaluate the user's product idea, decide which
phases to run, and execute the implemented skills in dependency order — keeping the work
**validation-driven**: the strategy must state what it is betting on and how it will be tested,
not just produce internally consistent documents.

## Language Selection

Ask which language to use for output documents (English default / Japanese), unless `--lang` is
given. Record it in `work/pipeline-progress.json` under `options.output_language`.

Ask the same way whether `generate-frontend` should **confirm the dependency versions** it resolves
before pinning them (see @rules/dependency-versions.md), and record it as
`options.confirm_versions` (`true` = ask, default; `false` = adopt the resolved stable set silently).
`--confirm-versions` / `--no-confirm-versions` override it per run.

## Workflow Selection

- Pick a profile (or honor `--profile`): `mvp` (vision + scope + validate — the smallest useful
  direction), `core-only`, `ux-to-spec`, `full`.
- **Implementation status**: all phases in the dependency manifest are implemented (`implemented:
  true`). Should a phase ever be marked `implemented: false`, tell the user it is not yet available
  and skip it (do not fabricate its output).
- **UX-phase visual track** (`full` profile): after `design-positioning`, run the two optional
  artifacts that feed the mocks — `create-domain-story` (the *what*: per-persona screen flow) and
  `design-system` (the *how it looks*: shared visual language) — before `generate-ui-mock`.
- **Example Mapping step** (optional; `ux-to-spec` / `full` profiles): after `define-features`, run
  `/product:example-map` for the Must/Should features — the rules and concrete examples the
  Gherkin, the aggregate invariants and the backlog acceptance criteria derive from. It is
  dialogue-driven; under `--auto` it harvests from the artifacts and records what it could not
  settle as `unasked` questions.
- **Frontend codegen step** (optional; `ux-to-spec` / `full` profiles): at the end of the spec phase
  (after the mocks and `define-features`), `generate-frontend` can turn the mocks + design system into
  a runnable React + Storybook frontend.
  It is **selectable**, not automatic — it produces real code (a heavier artifact), so the
  orchestrator asks before running it (see Execution Flow step 6). `--no-frontend` skips it outright;
  `--frontend` forces it on.

## Execution Flow

1. Read `@skills/product/common/skill-dependencies.yaml` to get phase order and the
   `implemented` flag.
2. Run `/product:init-output` to create the output tree and state files.
3. Execute implemented skills in dependency order, updating `work/pipeline-progress.json`
   **twice per phase** — `status: "in_progress"` with `plugin: "product"` and `started_at`
   *before* invoking the skill, then `completed` (or `failed`) with `completed_at`,
   `outputs` and `summary` after it returns (@skills/common/progress-registry.md). The
   pre-write is what makes `/product:report-status` show the phase as running and what
   attributes its tokens to it; `plugin` is what keeps that attribution off the architect
   pipeline's phase of the same name, since both pipelines write this one file — add to it,
   never re-register it. Append key decisions to `work/context.md` after each phase.
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
     supplied one); never fabricate brand values — unknowns become `TBD`, recorded `unasked`
     (@rules/open-questions.md §5).
   - interactive: offer **build** (derive tokens from positioning/personas) vs **incorporate**
     (`--import` an existing Tailwind / DTCG / Figma Tokens / CSS theme).
   If skipped, `generate-ui-mock` falls back to its built-in defaults.
6. **Frontend codegen step (selectable, spec phase)** — after `generate-ui-mock` (and once
   `define-features` exists, ideally), decide whether to run `/product:generate-frontend`, which emits
   a runnable React + TypeScript + Storybook scaffold under `generated/frontend/` (Atomic Design,
   token-styled, react-router from the story flow):
   - `--frontend` → always run; `--no-frontend` → always skip.
   - interactive (no flag): present the choice via AskUserQuestion — **Generate frontend** (build the
     React/Storybook code now) vs **Skip** (spec docs only; can run `/product:generate-frontend`
     later). Recommend skipping when there is no design system or the mocks are still lo-fi/unstable.
   - `--auto` with no flag: follow the profile — run it when `generate-frontend` is in the selected
     profile (`ux-to-spec`, `full`), skip otherwise.
   Record the decision in `work/pipeline-progress.json`. It does not block downstream phases
   (`define-features` / `define-data-model` read the mocks, not the generated code).
7. Skip phases whose prerequisites are absent (consumer treats a skipped/absent input as `TBD`).

## Phase Execution

A skill's own `model` takes effect only when the user types its command. Run from here with the
Skill tool, a phase runs on whatever this conversation runs on — which is why this skill declares
`model: inherit` rather than a tier of its own: it would otherwise pull every phase down to it.

**Interactive run (no `--auto`): phases run inline, on the session's model.** Every product phase
is a dialogue, and only the main conversation can ask the user. Seventeen of the manifest's phases
are assigned opus: when the session is on a smaller model, say so once before the first phase and
suggest `/model opus` — do not push strategy and judgment through on less.

**`--auto`: each phase runs as a sub-agent on its manifest model.** Nobody is being asked, so
nothing ties a phase to this conversation, and the tier the manifest assigns can be honoured:

```
Agent(
  subagent_type: "general-purpose",
  model: "{phase_model}",
  description: "{phase}",
  prompt: "Run the phase `{phase}` of the nexus product pipeline.
           Project directory: {project_dir} — every `reports/`, `work/`, `design-system/` and
           `generated/` path is relative to it, not to the directory the skill file lives in.
           Invoke the skill `product:{phase}` with the Skill tool, with these arguments:
           {arguments} --auto, and follow it to completion.
           You cannot ask the user: an unknown is recorded `unasked` with its question text and
           the options you would have offered (@rules/open-questions.md §5).
           Do not write this phase's entry in work/pipeline-progress.json — the orchestrator does.
           Reply with: the files you wrote, a two-line summary of what the phase concluded, any
           gate verdict, and the `OQ-` IDs you recorded. If the phase could not complete, say so
           and why."
)
```

`{phase_model}` is the phase's `model` in @skills/product/common/skill-dependencies.yaml, read at
the moment of the call. The validation gate still decides here: read its verdict from
`pipeline-progress.json` → `gates` after the `validate-assumptions` sub-agent returns.

## Iteration (not waterfall)

- The validation gate and the post-Phase-2 synthesis checkpoint may amend earlier artifacts
  **within the forward pipeline**. Reserve `/product:adapt-change` for genuine external changes.

## Error Handling

On phase failure, present choices via AskUserQuestion: Retry / Skip and continue / Abort.
If a phase is skipped, downstream skills treat its output as absent (`TBD`), never empty.

## Context Management

For long runs, periodically update `work/context.md`: key decisions, open assumptions, and the
`## Open Questions` table. Open Questions are carried across phases, not restated per phase — each
skill re-asks the `deferred` / `unasked` entries it needs and updates them in place under their
existing `OQ-` IDs (@rules/open-questions.md §7). Under `--auto` / `--profile=…` nothing is asked;
the entries are recorded `unasked` and surfaced by `/product:report`.

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
| `/product:name-product` | Optional — names the product as an acronym after the vision (in `full`) |
| `/product:validate-assumptions` | Validation gate after Phase 1 |
| `/product:create-domain-story` | UX phase — persona-anchored domain stories (the axis for UI mocks) |
| `/product:design-system` | UX phase — separately-managed design system (the visual language for UI mocks) |
| `/product:generate-frontend` | Spec phase — selectable React + Storybook codegen from the mocks (`--frontend`/`--no-frontend`) |
| `/architect:define-requirements` | Downstream handoff to system design |
