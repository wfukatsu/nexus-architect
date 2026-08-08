# AGENTS.md

Instructions for using this repository with Codex while preserving Claude Code plugin compatibility.

## What This Repository Is

This repository is a three-plugin architecture toolkit originally packaged for Claude Code:

- `architect`: system architecture, refactoring, design, migration, and reporting skills
- `scalardb`: ScalarDB application development, review, configuration, and scaffolding skills
- `product`: product-direction skills (product vision through SLA/NFR), nested under `skills/product/`; product rules under `rules/product/`

Claude Code continues to use `CLAUDE.md`, `.claude-plugin/`, and slash commands such as `/architect:start` or `/product:start`.
Codex uses this `AGENTS.md` file plus the `skills/*/SKILL.md` files directly.

## Codex Command Mapping

When the user invokes a Claude-style command in Codex, map it to the matching local skill:

- `/product:<name>` -> read and follow `skills/product/<name>/SKILL.md` (product skills are nested under `skills/product/`; product rules are nested under `rules/product/`)
- `/architect:<name>` -> read and follow `skills/<name>/SKILL.md`
- `/scalardb:<name>` -> read and follow `skills/<name>/SKILL.md`
- `@rules/...`, `@templates/...`, and `@skills/...` -> resolve as repository-relative paths

If a referenced skill does not exist, explain that it is unavailable and choose the closest documented fallback.

Before running an entry-point skill (`/product:start`, `/product:define-vision`, `/architect:investigate`, `/architect:define-requirements`), consult the input-requirements guides for the information the user must supply: [product Input Requirements](docs/product-input-requirements.md) and [architect Input Requirements](docs/architect-input-requirements.md).

## Claude Tool Mapping

Many skill files mention Claude Code tools. In Codex, interpret them as follows:

- `Read`: use `sed`, `cat`, or `rg` to read files
- `Write`: create files with `apply_patch`
- `Edit` / `MultiEdit`: use `apply_patch`
- `Bash`: use shell commands
- `Grep`: use `rg`
- `Glob`: use `rg --files` or `find`
- `LS`: use `ls`
- `WebFetch` / `WebSearch`: use Codex web access, Context7, or `curl` when network access is approved
- `AskUserQuestion` / `Question`: present numbered choices in chat and wait for the user's reply
- `Task` / `Subagent`: run the steps in the main Codex thread unless the user explicitly asks for sub-agents
- `Parallel`: use parallel shell reads where useful; keep code-writing steps coordinated
- `TodoWrite` / `TodoRead`: use local todo files only if the task requires persistent todos
- `Skill`: open the referenced `SKILL.md` and follow it
- `ExitPlanMode`: ignore

## Runtime Paths

Prefer repository-relative paths for Codex execution:

- Reports: `reports/`
- Generated code: `generated/`
- Pipeline state: `work/`
- Rules: `rules/`
- Common references: `skills/common/references/`
- Subagent prompt templates: `skills/common/subagents/`

Skills reference plugin files via `${CLAUDE_PLUGIN_ROOT}/...` (e.g.
`${CLAUDE_PLUGIN_ROOT}/skills/common/references/api-reference.md`,
`${CLAUDE_PLUGIN_ROOT}/rules/scalardb-crud-patterns.md`). In Codex, resolve
these as repository-relative paths (see the `CLAUDE_PLUGIN_ROOT` note below).

Legacy fallbacks (only if an old skill copy still mentions them):

- `.claude/docs/*` -> `skills/common/references/*`
- `.claude/rules/*` -> `rules/*`

For migration skills that mention `.claude/configuration/databases.env` or `.claude/output/`, keep those paths unless the user asks to migrate the runtime state. They are compatibility paths and can be used by both Claude Code and Codex.

When a skill mentions `CLAUDE_PLUGIN_ROOT`, treat the repository root as the plugin root in Codex.

- `${CLAUDE_PLUGIN_ROOT}/skills/common/subagents/<db>/` -> `skills/common/subagents/<db>/` (subagent prompt templates for migration skills)
- `${CLAUDE_PLUGIN_ROOT}/subagents/<db>/` -> `skills/common/subagents/<db>/` (legacy subagent prompt path)

## Pipeline Skill

`skills/pipeline/SKILL.md` is an orchestrator. It does not perform analysis itself — it reads
`skills/common/skill-dependencies.yaml` to determine execution order, then invokes each phase's
`SKILL.md` in sequence. When running the pipeline in Codex, follow the dependency graph manually:
read each skill file in order and execute it before moving to the next phase.

The `disable-model-invocation: true` frontmatter in that file is a Claude Code plugin hint; Codex
does not interpret it, so treat the file as the orchestration specification described above.

## Product → Architect Handoff

`product` and `architect` are two pipelines with two manifests
(`skills/product/common/skill-dependencies.yaml`, `skills/common/skill-dependencies.yaml`), run
one after the other in the same project directory. `/product:*` ends at SLA/NFR and hands off to
`define-requirements`, which reads the product reports instead of re-eliciting them. The contract
is `docs/design.md` §1 — read it before running either side of the boundary.

Detect the handoff by globbing `reports/00_core/`, `reports/01_ux/`, `reports/02_spec/`,
`reports/03_domain/`, `reports/04_quality/` and `work/traceability.json`. When any exist, run
`define-requirements` with them as inputs; §1.3 maps each product artifact to its deliverable and
§1.4 lists what product deliberately does *not* supply (per-process transaction consistency,
physical DB inventory, actor/role/permission) — those are what still gets elicited.

Three files under `work/` are **shared by both pipelines**, so every write is additive:

| File | Rule |
|------|------|
| `pipeline-progress.json` | Holds both pipelines' phases in one map keyed by bare phase name. Never re-register the map, never drop an entry your manifest does not define, never reset another pipeline's `options` (notably `output_language`). Write `"plugin": "product"\|"architect"` on every entry you stamp — `map-domains`, `design-api`, `create-domain-story` and `report` are defined by **both** manifests, so that field is the only thing that says whose entry it is. Where it is absent, confirm a `completed` against the phase's declared `outputs:` on disk before treating it as done |
| `traceability.json` | One graph for the whole project. `define-requirements` appends `FR-`/`NFR-` nodes to what product wrote; never start a second file and never truncate it to `[]`. ID prefixes are declared per phase as `id_prefix` in the manifests |
| `context.md` | Carries decisions and the Open Questions table across phases and across the boundary. Create it only when absent; never overwrite it |

`/product:adapt-change` walks the shared graph, so its blast radius reaches architect's nodes. It
**reports** them and stops — it never re-runs an architect skill or rewrites an architect
artifact (`docs/design.md` §7.5).

## Model Recommendations

Claude Code switches models automatically based on each skill's assignment. Codex ignores the
`model:` setting and uses the session model throughout, so choose an equivalent tier when possible:
Opus for architecture decisions, strategy, tradeoff analysis, and risk; Sonnet for standard analysis,
structured generation, and most reviews; Haiku for template generation and simple transforms.

The dependency YAML files are authoritative for pipeline skills; standalone skills use their
`SKILL.md` frontmatter. Product skill names are prefixed below to distinguish them from architect
skills with the same name.

`implement-backlog` is a thin sonnet orchestrator that delegates heavy steps to model-tiered
sub-agents (haiku digests, sonnet implementation, opus only for planning and consistency verdicts —
see its Sub-Agent Execution table). On runtimes without model switching, run the whole skill at the
session model and preserve the delegation structure (sub-agents return digests, not full sources).

| Plugin | Opus equivalent | Sonnet equivalent | Haiku equivalent sufficient |
|---|---|---|---|
| architect | define-requirements, analyze, map-domains, redesign, create-domain-story, design-microservices, design-scalardb, design-data-layer, design-api, design-implementation, generate-scalardb-code, design-infrastructure, review-risk, export-backlog, review-issue, merge-issue | start, pipeline, deliver-backlog, implement-backlog, capture-followup, investigate, investigate-security, analyze-data-model, evaluate-mmi, evaluate-ddd, integrate-evaluations, select-scalardb-edition, design-scalardb-analytics, generate-test-specs, generate-infra-code, generate-docs, design-security, design-observability, design-disaster-recovery, review-consistency, review-scalardb, review-data-integrity, review-operations, review-business, review-synthesizer, review-report, estimate-cost, migrate-database, migrate-oracle, migrate-mysql, migrate-postgresql | init-output, report, render-mermaid, update-knowledge, report-token-cost, report-backlog-status, report-status |
| scalardb | — | model, config, scaffold, error-handler, crud-ops, jdbc-ops, local-env, docs, build-app, review-code, migrate | — |
| product | product:define-vision, product:define-success-metrics, product:research-landscape, product:design-revenue, product:name-product, product:validate-assumptions, product:generate-persona, product:design-positioning, product:create-domain-story, product:design-system, product:define-data-model, product:map-domains, product:design-api, product:design-architecture, product:review, product:adapt-change | product:start, product:init-output, product:define-scope, product:map-journey, product:generate-ui-mock, product:define-features, product:generate-frontend, product:design-sla, product:define-nfr, product:report | product:report-status |

## Interaction Rules

- Preserve Claude Code compatibility. Do not remove `.claude-plugin/`, `CLAUDE.md`, or Claude-specific frontmatter unless explicitly asked.
- If a skill asks for multiple-choice input with `AskUserQuestion`, show the choices as a numbered list and wait for the user's answer before continuing.
- If a skill asks for parallel Claude subagents, execute the prerequisite steps in order and only parallelize independent shell reads or explicit user-approved agent work.
- Keep generated outputs in the documented output directories and include YAML frontmatter for Markdown reports.
- For any ScalarDB / ScalarDL / ScalarDB Saga design, implementation, review, or migration decision, ground the answer in the version-pinned OKF knowledge bundle at `knowledge/okf-scalardb-scalardl/okf/` (a git submodule; run `tools/update-okf-bundle.sh` to fetch it if absent, `update` to pull the newest, `status` to inspect). Pin product/version/edition first and answer only from that release's docs, per `rules/okf-knowledge-bundle.md`.
- Before writing any file that pins a version (Gradle/Maven, `package.json`, image tags, Helm/Terraform/Kubernetes), **look the version up** from its registry with the shell (`curl` against `repo1.maven.org` / Docker Hub / the Terraform registry, `npm view <pkg> dist-tags --json`, `gh release list -R <owner>/<repo>`, `curl -s https://endoflife.date/api/<product>.json`) — never write a version from memory or copy one out of a skill example. Choose a stable, non-EOL, mutually compatible release, record the decision table in the artifact and `work/version-decisions.json`, and confirm with the user per `--confirm-versions` / `--no-confirm-versions` / `options.confirm_versions` (unset -> interactive runs ask, `--auto` runs adopt). See `rules/dependency-versions.md`.
- After editing any report Markdown file or Mermaid diagram, you **must** run the validation hooks before proceeding:
  - `hooks/validate-frontmatter.sh <file.md>`
  - `hooks/validate-mermaid.sh <file.md>`

  A non-zero exit means the file has a frontmatter or diagram error — fix it before continuing.
