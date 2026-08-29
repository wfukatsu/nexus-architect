# AGENTS.md

Instructions for using this repository with Codex while preserving Claude Code plugin compatibility.

## What This Repository Is

This repository is a four-plugin architecture toolkit originally packaged for Claude Code:

- `architect`: system architecture, refactoring, design, migration, and reporting skills
- `scalardb`: ScalarDB application development, review, configuration, and scaffolding skills
- `product`: product-direction skills (product vision through SLA/NFR), nested under `skills/product/`; product rules under `rules/product/`
- `infra`: multi-cloud, four-environment infrastructure skills (design, implement, review), nested under `skills/infra/`; infra rules under `rules/infra/`

Claude Code continues to use `CLAUDE.md`, `.claude-plugin/`, and slash commands such as `/architect:start` or `/product:start`.
Codex uses this `AGENTS.md` file plus the `skills/*/SKILL.md` files directly.

## Codex Command Mapping

When the user invokes a Claude-style command in Codex, map it to the matching local skill:

- `/product:<name>` -> read and follow `skills/product/<name>/SKILL.md` (product skills are nested under `skills/product/`; product rules are nested under `rules/product/`)
- `/infra:<name>` -> read and follow `skills/infra/<name>/SKILL.md` (infra skills are nested under `skills/infra/`; infra rules are nested under `rules/infra/`). `/infra:start` is the router: it resolves the bundle, checks freshness and fixes environment and cloud, then follow the mode skill it selects
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
- `AskUserQuestion` / `Question`: present numbered choices in chat, add an explicit "or type your own answer" line (Codex has no harness-appended "Other"), and wait for the user's reply
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
`reports/03_domain/`, `reports/04_quality/` and `work/traceability.json` — matching **files**, not directories, since `/product:init-output` creates two of those directories empty. When any exist, run
`define-requirements` with them as inputs; §1.3 maps each product artifact to its deliverable and
§1.4 lists what product deliberately does *not* supply (per-process transaction consistency,
physical DB inventory, actor/role/permission) — those are what still gets elicited.

Three files under `work/` are **shared by both pipelines**, so every write is additive:

| File | Rule |
|------|------|
| `pipeline-progress.json` | Holds both pipelines' phases in one map keyed by bare phase name. Never re-register the map, never drop an entry your manifest does not define, never reset another pipeline's `options` (notably `output_language`). Write `"plugin": "product"\|"architect"` on every entry you stamp — `map-domains`, `design-api`, `create-domain-story` and `report` are defined by **both** manifests, so that field is the only thing that says whose entry it is. Where it is absent, confirm a `completed` against the phase's declared `outputs:` on disk before treating it as done |
| `traceability.json` | One graph for the whole project. `define-requirements` appends `FR-`/`NFR-` nodes to what product wrote; never start a second file and never truncate it to `[]`. ID prefixes are declared per phase as `id_prefix` in the manifests |
| `context.md` | Decisions, and **the** Open Questions store for the whole project — both pipelines' questions live in this one file, answered in place under their existing `OQ-` IDs; `reports/00_requirements/open-questions.md` is a view rendered from it, not a second store. Allocate a new ID as `max(OQ-###) + 1` over the store, never by numbering from your own reports. Create it only when absent; never overwrite it |

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
| architect | define-requirements, analyze, map-domains, redesign, create-domain-story, design-aggregate, design-state-machine, design-microservices, design-scalardb, design-data-layer, design-api, design-graphql, design-implementation, generate-scalardb-code, generate-api-code, generate-graphql-code, verify-implementation, design-infrastructure, review-risk, review-api-security, export-backlog, review-issue, merge-issue | start, pipeline, deliver-backlog, implement-backlog, capture-followup, investigate, investigate-security, analyze-data-model, evaluate-mmi, evaluate-ddd, integrate-evaluations, select-scalardb-edition, design-scalardb-analytics, generate-test-specs, generate-characterization-tests, generate-contract-tests, generate-acceptance-tests, generate-infra-code, generate-docs, design-security, design-observability, design-disaster-recovery, review-consistency, review-scalardb, review-data-integrity, review-operations, review-business, review-synthesizer, review-report, estimate-cost, estimate-token-cost, migrate-database, migrate-oracle, migrate-mysql, migrate-postgresql | init-output, report, render-mermaid, update-knowledge, report-token-cost, report-backlog-status, report-status |
| scalardb | — | model, config, scaffold, error-handler, crud-ops, jdbc-ops, local-env, docs, build-app, review-code, migrate | — |
| infra | infra:design, infra:review | infra:start, infra:implement | — |
| product | product:define-vision, product:define-success-metrics, product:research-landscape, product:design-revenue, product:name-product, product:validate-assumptions, product:generate-persona, product:design-positioning, product:create-domain-story, product:design-system, product:example-map, product:define-data-model, product:map-domains, product:design-api, product:design-architecture, product:review, product:adapt-change | product:start, product:init-output, product:define-scope, product:map-journey, product:generate-ui-mock, product:define-features, product:generate-frontend, product:design-sla, product:define-nfr, product:report | product:report-status |

## Interaction Rules

- Preserve Claude Code compatibility. Do not remove `.claude-plugin/`, `CLAUDE.md`, or Claude-specific frontmatter unless explicitly asked.
- If a skill asks for multiple-choice input with `AskUserQuestion`, show the choices as a numbered list, end with an explicit "or type your own answer" line, and wait for the user's answer before continuing. A reply that matches no number is a free-text answer: record it verbatim, never round it to the nearest choice.
- When a skill hits an unknown it cannot resolve from its inputs, **ask it** rather than writing `TBD`: derive 2–4 candidate answers with their downstream consequences, present them as above, and only record `TBD` for what the user defers, cannot answer in-session, or was never asked (`--auto`) — each with its `OQ-` ID, status and owner. See `rules/open-questions.md`.
- If a skill asks for parallel Claude subagents, execute the prerequisite steps in order and only parallelize independent shell reads or explicit user-approved agent work.
- Keep generated outputs in the documented output directories and include YAML frontmatter for Markdown reports.
- For any infrastructure design, implementation, or review decision (Terraform, Kubernetes, Helm, Kustomize, Argo CD, GitLab CI/CD, Cosign, Vault, External Secrets, Prometheus/Grafana, Kyverno), ground the answer in the vendored OKF bundle at `knowledge/okf-k8s-tf/` (`tools/update-okf-bundle.sh status --bundle=k8s-tf`; it has **no remote** — the origin repository was deleted). Fix the target environment (`local` / `test` / `staging` / `production`) and cloud before reading anything, keep the bundle's three tiers apart in the output (observed implementation = fact, design guidance = recommendation with a source, open question = unresolved), cite the document behind each claim, and say "outside the bundle's scope" for `local` and for anything production-specific rather than asserting. See `rules/okf-k8s-tf-bundle.md`, `rules/infra/environments.md`, `rules/infra/multi-cloud.md`.
- For any ScalarDB / ScalarDL / ScalarDB Saga design, implementation, review, or migration decision, ground the answer in the version-pinned OKF knowledge bundle at `knowledge/okf-scalardb-scalardl/okf/` (a git submodule; run `tools/update-okf-bundle.sh` to fetch it if absent, `update` to pull the newest, `status` to inspect). Pin product/version/edition first and answer only from that release's docs, per `rules/okf-knowledge-bundle.md`.
- Before writing any file that pins a version (Gradle/Maven, `package.json`, image tags, Helm/Terraform/Kubernetes), **look the version up** from its registry with the shell (`curl` against `repo1.maven.org` / Docker Hub / the Terraform registry, `npm view <pkg> dist-tags --json`, `gh release list -R <owner>/<repo>`, `curl -s https://endoflife.date/api/<product>.json`) — never write a version from memory or copy one out of a skill example. Choose a stable, non-EOL, mutually compatible release, record the decision table in the artifact and `work/version-decisions.json`, and confirm with the user per `--confirm-versions` / `--no-confirm-versions` / `options.confirm_versions` (unset -> interactive runs ask, `--auto` runs adopt). See `rules/dependency-versions.md`.
- When a skill designs, generates, or reviews an HTTP API surface, the specification file under `reports/03_design/api-specifications/` is the **contract**: code may not add an endpoint, parameter, field, or status code the specification does not declare, may not contradict one it does, and a behaviour change edits the specification first. Every operation carries an `operationId` bound 1:1 to one handler, and the binding is recorded in `reports/06_implementation/api-contract-map.json`. See `rules/api-contract-fidelity.md`.
- Every non-2xx response is an RFC 9457 Problem Details object (`application/problem+json`) whose `type` comes from the project's registry in `reports/03_design/api-specifications/problem-types.md` — never a second, ad-hoc error envelope. `UnknownTransactionStatusException` gets its own branch, never a generic 500 handler: the commit may have succeeded, so it is 503 with `Retry-After` **only** when the operation is idempotency-key protected, and otherwise 500 with no retry hint and an explicit reconcile-don't-retry `detail`. See `rules/api-error-standard.md`.
- Generated or AI-written code passes the eight-stage quality gate before a human is asked to review it: build, unit, contract, integration, SAST, dependency scan, API security, and design↕code conformance. **Every stage produces evidence** — a command that ran with its exit code, or a skill that returned findings; "it looks correct" is not a stage result, and a stage that did not run is recorded with its reason rather than omitted. A FAIL blocks the review handoff; it is not a note on the PR. See `rules/ai-code-quality-gate.md` and `rules/api-security-checks.md`.
- Merge-bound application code is written **test-first**, as a Red → Green → Refactor commit series per unit: a `test:` commit whose body names the tests that were run and failed, then the `feat:` commit that makes them pass, then a `refactor:` commit that edits no test. Every repository port gets an in-memory Fake; `Clock` and id generation are injected. The gate reads the branch log and records the sequence per unit — reported, never silent. Legacy modules are pinned by characterization tests recorded from the running system before a transformation step touches them. See `rules/tdd-workflow.md`.
- After editing any report Markdown file or Mermaid diagram, you **must** run the validation hooks before proceeding:
  - `hooks/validate-frontmatter.sh <file.md>`
  - `hooks/validate-mermaid.sh <file.md>`

  A non-zero exit means the file has a frontmatter or diagram error — fix it before continuing.
