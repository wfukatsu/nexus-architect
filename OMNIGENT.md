# OMNIGENT.md

Instructions for running this repository under **Omnigent**, a generic multi-agent
orchestrator, while preserving Claude Code plugin compatibility.

This file is the Omnigent counterpart of [`AGENTS.md`](AGENTS.md) (which targets
Codex) and [`CLAUDE.md`](CLAUDE.md) (which targets Claude Code). All three describe
the **same** skills; only the runtime translation differs. Nothing here modifies the
skills — Omnigent reads the existing `skills/*/SKILL.md` files directly.

## What This Repository Is

A four-plugin system-architecture toolkit originally packaged for Claude Code:

- **architect** — system architecture, refactoring, design, database migration, reporting
- **scalardb** — ScalarDB application development, review, configuration, scaffolding
- **product** — product-direction skills (vision → SLA/NFR), nested under `skills/product/`
- **infra** — multi-cloud, four-environment infrastructure skills, nested under `skills/infra/`

There are ~115 `SKILL.md` files. Each is a self-contained instruction document. Under
Claude Code they are invoked as slash commands (e.g. `/architect:investigate`); under
Omnigent a worker resolves the command to a file, reads it, and follows it.

## Quick Start: the loader

A worker does not need to memorize the resolution rules below — it can call the loader,
which resolves the path, prints a translation preamble, and emits the skill body with
`${CLAUDE_PLUGIN_ROOT}` already expanded:

```bash
bash tools/omnigent/load-skill.sh architect:investigate     # flat (architect) skill
bash tools/omnigent/load-skill.sh scalardb:model            # flat (scalardb) skill
bash tools/omnigent/load-skill.sh product:define-vision     # nested product skill
bash tools/omnigent/load-skill.sh investigate               # bare name → architect namespace
bash tools/omnigent/load-skill.sh --list                    # enumerate every skill
```

The loader exits non-zero (with a stderr message naming what it looked up) when a skill
does not exist. See [`tools/omnigent/README.md`](tools/omnigent/README.md).

## Slash → Path Resolution

When a user invokes a Claude-style command, map it to the matching local file. There are
**four** plugins; `product` and `infra` are nested.

| Command form        | Resolves to                          |
|---------------------|--------------------------------------|
| `/architect:<name>` | `skills/<name>/SKILL.md`             |
| `/scalardb:<name>`  | `skills/<name>/SKILL.md`             |
| `/product:<name>`   | `skills/product/<name>/SKILL.md`     |
| `/infra:<name>`     | `skills/infra/<name>/SKILL.md`       |

`architect` and `scalardb` share the flat `skills/` directory — both prefixes (and a
bare `<name>` with no prefix) resolve flat skills identically. `product` and `infra`
skills are nested; note that `infra` uses names (`design`, `implement`, `review`,
`start`) that also read as bare words, so a bare `<name>` never resolves into
`skills/infra/` — the `infra:` prefix is required.

**The infra router.** `/infra:start` is triage, not analysis: it resolves the
`okf-k8s-tf` bundle, checks `stale_after` freshness, fixes the target environment and
cloud, then hands to `/infra:design`, `/infra:implement` or `/infra:review` with those
four facts already settled. Under Omnigent, run it as a dispatch step and pass its
result into the mode skill rather than re-asking.

**Nested sub-skills.** The migration routers (`migrate-oracle`, `migrate-mysql`,
`migrate-postgresql`) delegate to sub-skills that are *not* slash commands — they are
read by path, e.g. `skills/migrate-oracle/migrate-oracle-to-scalardb/SKILL.md`. The
router body references them via `${CLAUDE_PLUGIN_ROOT}/skills/...` paths, which the
loader expands automatically. They are also loadable directly:
`load-skill.sh architect:migrate-oracle/migrate-oracle-to-scalardb`.

If a referenced skill does not exist, explain that it is unavailable and choose the
closest documented fallback.

## Path Resolution: `${CLAUDE_PLUGIN_ROOT}` and `@`-prefixes

Repository root is an **absolute path** — the loader prints it as
`CLAUDE_PLUGIN_ROOT == <absolute root>` in its preamble. Resolve `${CLAUDE_PLUGIN_ROOT}`,
`@rules/`, `@templates/`, `@skills/` and other repo-relative paths against this absolute
root; **do NOT assume your CWD equals it** (the loader never `cd`s). Treat the repository
root as the plugin root:

- `${CLAUDE_PLUGIN_ROOT}` → the absolute repo root. The loader substitutes any literal
  `${CLAUDE_PLUGIN_ROOT}` in a skill body with the absolute root before emitting it, so a
  worker that uses the loader never sees the raw token. If a worker reads a `SKILL.md`
  directly (without the loader), it must perform this substitution itself.
- `@rules/...`, `@templates/...`, `@skills/...` → resolve as repository-relative paths.

Runtime output directories (repository-relative):

| Purpose            | Path                          |
|--------------------|-------------------------------|
| Reports            | `reports/`                    |
| Generated code     | `generated/`                  |
| Pipeline state     | `work/`                       |
| Rules              | `rules/`                      |
| Common references  | `skills/common/references/`   |
| Subagent templates | `skills/common/subagents/`    |

## Claude Tool → Omnigent Tool Mapping

Skill bodies mention Claude Code tools. Interpret them as Omnigent tools:

| Claude tool        | Omnigent tool   | Notes                                    |
|--------------------|-----------------|------------------------------------------|
| `Read`             | `sys_os_read`   | read a file                              |
| `Write`            | `sys_os_write`  | create/overwrite a file                  |
| `Edit` / `MultiEdit` | `sys_os_edit` | in-place edit                            |
| `Bash`             | `sys_os_shell`  | run a shell command                      |
| `Grep`             | `sys_os_shell`  | `rg` / `grep` within the shell           |
| `Glob`             | `sys_os_shell`  | `rg --files` / `find` within the shell   |
| `LS`               | `sys_os_shell`  | `ls`                                     |
| `WebFetch` / `WebSearch` | (orchestrator web capability) | when network is approved      |

## `Task(...)` Blocks → Sequential Bodies or Orchestrator Dispatch

Several skills (notably the 6-perspective parallel reviews and the migration routers)
spawn Claude sub-agents via `Task(...)`. Under Omnigent, for each `Task` prompt body:

- **Default (sequential):** run each prompt body one after another in the same worker
  and have the orchestrator aggregate the results.
- **Parallel (orchestrator capability):** genuine concurrent sub-agent execution is
  performed by the **orchestrator** via the session/sub-agent dispatch API (e.g.
  `sys_session_send`), not by a plain worker.

> **Note:** `sys_call_async` dispatches a registered local **Python tool**, not an
> agent/sub-agent session — do **not** use it to run `Task(...)` prompt bodies.

Either way, the **orchestrator** computes any composite scores *after* collecting all
results — individual sub-agents only return their own findings (e.g. each review writes
`reports/review/individual/review-<perspective>.json`; the synthesizer merges them).

## `AskUserQuestion` → Orchestrator ↔ Human Gate

When a skill asks a multiple-choice question (`AskUserQuestion`) or otherwise needs human
input:

1. Present the choices as a **numbered list**, followed by an explicit "or type your own
   answer" line — Omnigent has no harness-appended "Other", so the free-text path must be
   offered by hand.
2. **Pause** the run and surface the question to the human via the orchestrator's gate.
3. **Resume** when the human replies, using their selection. A reply matching no number is a
   free-text answer: record it verbatim, never round it to the nearest choice.

This is also how **Open Questions** are handled: an unknown a skill cannot resolve from its
inputs is asked here, and only what the human defers, cannot answer in-session, or was never
asked becomes a `TBD` — recorded with its `OQ-` ID, status and owner per
`rules/open-questions.md`.

When a skill is run with `--auto` (or a `--profile=...` in the product pipeline),
interactivity is bypassed: pick the documented default for each gate and continue without
pausing. Unresolved items are recorded as `unasked` Open Questions, carrying the question and
the options that would have been offered.

## Hooks → Explicit Validation Gate

Under Claude Code, two `PostToolUse` hooks fire automatically after every `Write`/`Edit`
(see `hooks/hooks.json`):

- `hooks/validate-frontmatter.sh` — every `reports/**/*.md` must open with valid YAML
  frontmatter containing `title`, `schema_version`, `skill`.
- `hooks/validate-mermaid.sh` — Mermaid diagram syntax.

**These do NOT auto-fire under Omnigent.** After writing any report `.md`, run them as an
explicit gate (both scripts already support CLI mode — pass file paths as arguments):

```bash
bash hooks/validate-frontmatter.sh <file.md>
bash hooks/validate-mermaid.sh <file.md>
```

A **non-zero exit** means the file has a frontmatter or diagram error — fix it before
continuing. Run both after each report write, not in a batch at the end.

## `model:` Frontmatter

Each `SKILL.md` carries a `model:` tier (opus / sonnet / haiku). Under Omnigent either:

- **ignore it** and use a single capable session model throughout (simplest), or
- **map the tier** to a per-dispatch model when the orchestrator supports model selection.

Recommended tiers (from the skill frontmatter): **opus** for judgment-heavy work
(`analyze`, `redesign`, `design-microservices`, `design-scalardb`, `design-api`,
`map-domains`, `review-risk`, the product strategy skills, and `infra:design` /
`infra:review`), **sonnet** for standard analysis/generation/reviews, **haiku** for
templating (`init-output`, `render-mermaid`).
Prefer Sonnet-or-above for anything not explicitly haiku-tier.

## Pipeline Sequencing

`skills/pipeline/SKILL.md` (and `skills/start/SKILL.md`) are orchestrators — they do no
analysis themselves. To run a pipeline under Omnigent:

1. Read the DAG from `skills/common/skill-dependencies.yaml` (the architect pipeline) or
   `skills/product/common/skill-dependencies.yaml` (the product pipeline). Each entry
   lists `depends_on`, `parallel_with`, `conditions`, `outputs`, and `model`.
2. Execute phases in dependency order; run `parallel_with` groups concurrently (see the
   `Task` dispatch section). Honor `conditions` (e.g. `scalardb_enabled` selects
   `review-scalardb`; `scalardb_disabled` selects `review-data-integrity`).
3. Track progress in `work/pipeline-progress.json` (plain data — not a Claude construct).
   It also holds `options.output_language` (`en` default, `ja` supported) and
   `options.confirm_versions` (see Dependency Versions). **Both pipelines write this one
   file** — see Product → Architect Handoff for the rules that makes necessary.

The `disable-model-invocation: true` frontmatter on orchestrator files is a Claude Code
hint; Omnigent ignores it and treats the file as the orchestration spec above.

## Product → Architect Handoff

The two pipelines run one after the other in the same project directory: `/product:*` ends
at SLA/NFR and hands off to `define-requirements`, which reads the product reports rather
than re-eliciting them. `docs/design.md` §1 is the contract — read it before running either
side of the boundary; §1.3 maps each product artifact to its deliverable and §1.4 lists what
product deliberately does not supply.

Detect the handoff by globbing `reports/00_core/`, `reports/01_ux/`, `reports/02_spec/`,
`reports/03_domain/`, `reports/04_quality/` and `work/traceability.json` — matching **files**,
not directories: `/product:init-output` creates two of those directories empty, so a
directory-existence test passes on any initialized product project.

Three files under `work/` are shared, so **every write is additive** — read before writing
and merge into what is there:

- **`pipeline-progress.json`** — one `phases` map, keyed by bare phase name, holding both
  pipelines' entries. Never re-register the map, never drop an entry the manifest you are
  running does not define, never reset another pipeline's `options`. Stamp
  `"plugin": "product"` or `"architect"` on every entry you write: `map-domains`,
  `design-api`, `create-domain-story` and `report` exist in **both** manifests, and that
  field is the only thing that distinguishes them. Where it is absent, confirm a `completed`
  against the phase's declared `outputs:` on disk before skipping the phase as done.
- **`traceability.json`** — one graph for the project; `define-requirements` appends
  `FR-`/`NFR-` nodes to what product wrote. Never start a second file, never truncate it to
  `[]`. Which skill mints which ID prefix is declared as `id_prefix` on each manifest phase.
- **`context.md`** — decisions, and **the** Open Questions store for the whole project: both
  pipelines' questions live in this one file and are answered in place under their existing
  `OQ-` IDs, so an architect answer is visible to a later product rerun.
  `reports/00_requirements/open-questions.md` is a view rendered from it, never a second store.
  New IDs are `max(OQ-###) + 1` over the store. Create only when absent; never overwrite.

`adapt-change` walks the shared graph, so its blast radius reaches architect's nodes. It
reports them and stops: no architect skill is re-run and no architect artifact is rewritten
(`docs/design.md` §7.5).

## Interaction Rules

- **Non-invasive.** Do not modify `.claude-plugin/`, `CLAUDE.md`, `AGENTS.md`, the
  `SKILL.md` bodies, `rules/`, `templates/`, or `hooks/`. Omnigent adds only this file and
  the `tools/omnigent/` helpers; Claude Code compatibility is preserved.
- Present `AskUserQuestion` choices as a numbered list plus an "or type your own answer"
  line, and wait for the human's reply (unless `--auto`).
- Keep generated outputs in the documented output directories with YAML frontmatter.
- After writing any report `.md` or Mermaid diagram, run **both** validation hooks and fix
  any non-zero exit before proceeding.

## ScalarDB / ScalarDL / ScalarDB Saga Knowledge Bundle

Any ScalarDB / ScalarDL / ScalarDB Saga design, implementation, review, or migration decision must be grounded in
the version-pinned OKF knowledge bundle at `knowledge/okf-scalardb-scalardl/okf/` (a git
submodule; run `tools/update-okf-bundle.sh` to fetch it if absent, `update` to pull the newest,
`status` to inspect). Pin the project's product, version, and edition first, then answer only from that
release's docs and cite each concept's `resource` URL. See
[`rules/okf-knowledge-bundle.md`](rules/okf-knowledge-bundle.md).

## Kubernetes / Terraform Knowledge Bundle

Any infrastructure design, implementation, or review decision must be grounded in the OKF bundle
at `knowledge/okf-k8s-tf/` (`tools/update-okf-bundle.sh status --bundle=k8s-tf`). Unlike the
ScalarDB bundle it is **vendored, not a submodule** — its origin repository was deleted, so there
is no remote and `update` cannot fetch.

Fix the target environment (`local` / `test` / `staging` / `production`) and cloud before reading
anything. Keep the bundle's three tiers apart in the output: observed implementation is fact,
design guidance is a recommendation carrying its source, an open question stays open. `local` is
absent from the bundle entirely and `production` has no observed implementation — say so rather
than asserting. See [`rules/okf-k8s-tf-bundle.md`](rules/okf-k8s-tf-bundle.md),
[`rules/infra/environments.md`](rules/infra/environments.md) and
[`rules/infra/multi-cloud.md`](rules/infra/multi-cloud.md).

The infra skills have **no dependency manifest** — they are a router plus three modes, not a
pipeline — so nothing in Pipeline Sequencing applies to them and they write no
`work/pipeline-progress.json` phase entries.

## Dependency Versions

Any generated file that pins a version (Gradle/Maven, `package.json`, image tags, Helm/Terraform/
Kubernetes) must use a version that was **looked up** from its registry at generation time — never
recalled from model memory or copied out of a skill example — and must be a stable, non-EOL,
mutually compatible release. Whether the resolved set is confirmed with the human is configurable:
`--confirm-versions` / `--no-confirm-versions` per run, `options.confirm_versions` in
`work/pipeline-progress.json` as the project default (unset -> interactive runs ask, `--auto` runs
adopt). Record the decision table in the artifact and in `work/version-decisions.json`. See
[`rules/dependency-versions.md`](rules/dependency-versions.md).

## API Contract Fidelity

When a skill designs, generates, or reviews an HTTP API surface, the specification file under
`reports/03_design/api-specifications/` is the **contract**, not an illustration of one. Generated or
hand-written code may not add an endpoint, parameter, field, or status code the specification does
not declare, may not contradict one it does, and a behaviour change edits the specification first.
Every operation carries an `operationId` bound 1:1 to exactly one handler, and that binding is
recorded in `reports/06_implementation/api-contract-map.json`, whose `unmapped` arrays are never
omitted. Where code and contract disagree, **report the drift — do not silently reconcile it**. See
[`rules/api-contract-fidelity.md`](rules/api-contract-fidelity.md).

Every non-2xx response is an RFC 9457 Problem Details object served as `application/problem+json`,
with its `type` drawn from the project's registry in
`reports/03_design/api-specifications/problem-types.md`. A second, parallel error envelope anywhere
in the project is a defect. `UnknownTransactionStatusException` never reaches a generic 500 handler:
the commit may have succeeded, so it is 503 with `Retry-After` **only** when the operation is
idempotency-key protected, and 500 with no retry hint and an explicit reconcile-don't-retry `detail`
otherwise. See [`rules/api-error-standard.md`](rules/api-error-standard.md).

## AI Code Quality Gate

Generated or AI-written code passes an eight-stage gate before a human is asked to review it: build,
unit tests, contract tests, integration tests, SAST, dependency scan, API security, and design↕code
conformance. Under Omnigent the first six are `sys_os_shell` invocations and the last two are the
`review-api-security` / `verify-implementation` skills. Stage 2 also runs the coverage verification
and the mutation run over the touched `domain/` packages; stage 4 runs `integrationTest` (the `TX-`
scenarios over an in-process ScalarDB), `acceptanceTest` (the Gherkin scenarios) and, on the legacy
path, `characterizationTest`. Every command runs from a clean build state — a cached task that exits
0 having run nothing is recorded as zero coverage, never as a pass. Merge-bound code reaching the
gate was written test-first as a `test:` → `feat:` → `refactor:` commit series per unit
([`rules/tdd-workflow.md`](rules/tdd-workflow.md)); the gate reads the branch log and reports the
sequence per unit.

**Every stage produces evidence.** A stage passes when a command ran and exited zero, or when a skill
returned findings — a worker's assessment that the code looks correct is not a stage result. A stage
that did not run is recorded with its reason (`not-applicable` / `not-configured` / `skipped-by-user`),
never omitted, because an omitted stage reads as a passed one. A FAIL verdict blocks the handoff to
human review rather than becoming a note on it. See
[`rules/ai-code-quality-gate.md`](rules/ai-code-quality-gate.md) and
[`rules/api-security-checks.md`](rules/api-security-checks.md).

## Output Language

Configurable per project in `work/pipeline-progress.json` (`options.output_language`:
`en` default, `ja` supported). Report prose uses the configured language; YAML frontmatter
keys and Mermaid node IDs stay in English. See [`rules/output-conventions.md`](rules/output-conventions.md).
