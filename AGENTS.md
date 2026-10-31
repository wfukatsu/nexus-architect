# AGENTS.md

The one entry document for every runtime that drives this repository: Claude Code (as four
plugins with slash commands), Codex (reading this file at the repository root) and Omnigent (a
generic orchestrator, through `tools/omnigent/load-skill.sh`). All three run the same
`skills/**/SKILL.md` files; only the translation in § Runtimes differs.

## What This Is

A four-plugin system-architecture toolkit:

- **product** — product direction: a validation-driven, dialogue-based pipeline from product vision to SLA/NFR; hands off to architect for system implementation design
- **architect** — system architecture for legacy refactoring, greenfield design and consulting deliverables
- **scalardb** — ScalarDB application development toolkit
- **infra** — multi-cloud (AWS / Azure / GCP) × four-environment (local / test / staging / production) infrastructure: design, implementation and review of Terraform / Kubernetes / GitOps, grounded in the vendored OKF `okf-k8s-tf` bundle

Workflows:
- **Product direction**: vision → success metrics / revenue → scope → validate → personas/journey/positioning → domain-stories/design-system → UI/features/data/frontend → domains/API → SLA/NFR → architecture/tech-fitness → review/report (handoff to `/architect:define-requirements`)
- **Legacy refactoring**: investigate → analyze → evaluate → redesign → implement
- **Greenfield design**: requirements → domain modeling → ScalarDB design → infra → deploy
- **Consulting deliverables**: reports, cost estimates, domain stories
- **Infrastructure**: triage (bundle / freshness / environment / cloud) → design → implement → review, per environment and per cloud

Commands are `/product:<name>`, `/architect:<name>`, `/scalardb:<name>`, `/infra:<name>`. Entry
points: `/product:start` (product direction), `/architect:start` (interactive analysis/design),
`/architect:pipeline` (automated), `/infra:start` (infrastructure). Before an entry point, the
inputs the user must supply are `docs/product-input-requirements.md` and
`docs/architect-input-requirements.md`.

## Runtimes

**Claude Code** installs the four plugins from `.claude-plugin/marketplace.json`; a registered
skill is a slash command, `hooks/hooks.json` fires automatically, and a skill's `model` /
`allowed-tools` apply as `docs/skill-authoring.md` measures. In this repository `CLAUDE.md` is a
stub holding `@AGENTS.md`, so this file is read once on every version and every **Project
instructions** setting; edit this file, never the stub.

**Codex** reads this file at the repository root and truncates it silently past
`project_doc_max_bytes` (32 KiB by default) — `tools/docs_consistency.test.py` keeps it under
that, and `docs/codex-usage.md` says how to raise the budget. It has no `@` imports, no plugins
and no hooks: everything it needs is below.

**Omnigent** calls the loader, which resolves a command to its file, prints a translation
preamble and emits the body with `${CLAUDE_PLUGIN_ROOT}` expanded to the absolute root (`bash
tools/omnigent/load-skill.sh architect:investigate`; `--list` enumerates; see
`tools/omnigent/README.md`). Parallel `Agent(...)` bodies are dispatched by the orchestrator
(`sys_session_send`), never by `sys_call_async`, which runs a local Python tool.

**Command → file.** `/architect:<name>` and `/scalardb:<name>` → `skills/<name>/SKILL.md` (one flat
tree; a bare `<name>` resolves there too); `/product:<name>` → `skills/product/<name>/SKILL.md`;
`/infra:<name>` → `skills/infra/<name>/SKILL.md` (prefix required: `design`, `implement`, `review`,
`start` also read as bare words). The migration routers read nested sub-skills by path
(`skills/migrate-oracle/migrate-oracle-to-scalardb/SKILL.md`); they are not commands. A skill
that does not exist is reported as unavailable, with the closest documented fallback. Outputs
go to `reports/`, `generated/` and `work/` of the project being worked on; `${CLAUDE_PLUGIN_ROOT}`
and the `@rules/…` notation are the repository root (`Shared files:` line in each skill). Legacy
path spellings and the migration tree's `.claude/configuration/` compatibility paths are
translated in `docs/codex-usage.md` § Runtime Paths.

**Skill vocabulary.** Skill bodies name Claude Code tools. Translate:

| In a skill | Claude Code | Codex | Omnigent |
|------------|-------------|-------|----------|
| `Read`, `Write`, `Edit` (`MultiEdit`) | the tools | `sed`/`cat`/`rg`; `apply_patch` | `sys_os_read`, `sys_os_write`, `sys_os_edit` |
| `Bash`, `Grep`, `Glob`, `LS` | the tools | shell, `rg`, `rg --files`/`find`, `ls` | `sys_os_shell` |
| `WebFetch` / `WebSearch` | the tools | web access, Context7 or `curl` when approved | orchestrator web capability |
| `AskUserQuestion` | the tool (harness appends "Other") | numbered list + an explicit "or type your own answer" line; wait; an answer matching no number is free text, recorded verbatim | the same, surfaced through the orchestrator's human gate; `--auto` picks the documented default and records the question `unasked` |
| `Agent(...)` with `model`, `run_in_background` | the tool; `model` on every call (`skills/common/sub-agent-patterns.md`) | run the prompt bodies in sequence in the main thread unless the user asks for sub-agents | sequential in one worker, or orchestrator dispatch; composite scores computed after all results are in |
| `Skill` | the tool | open the named `SKILL.md` and follow it | the loader |
| `model:` frontmatter, `disable-model-invocation`, `allowed-tools` | honoured as measured | ignored — choose an equivalent session model (opus: architecture, strategy, risk; sonnet: analysis, generation, reviews; haiku: templating) | ignore, or map the tier per dispatch |
| the two report hooks | fire on Write/Edit under `reports/` | run by hand after every report write: `hooks/validate-frontmatter.sh <file>`, `hooks/validate-mermaid.sh <file>`; non-zero means fix before continuing | the same |
| `TodoWrite`, `ExitPlanMode` | the tools | a local todo file if needed; ignore | ignore |

`/architect:pipeline` is non-interactive on every runtime: a question a phase would ask is
recorded `unasked` (`rules/open-questions.md` §5). Under Claude Code each phase is a sub-agent on
the manifest's `model`; elsewhere run the phases in manifest order on the session model.

## Repository Mechanics

This repo is not an application — it is a **plugin marketplace** whose product is a corpus of
~120 skill instruction files (117 registered as commands, plus the ten nested migration
sub-skills). There is no build step; "developing" here means editing skills, rules and hooks.
The authoring rules, with the measurements behind them, are `docs/skill-authoring.md`. In brief:

- **Packaging.** `.claude-plugin/marketplace.json` defines the four plugins, each with its version, and lists the skill directories it ships. Adding a skill is two edits: `skills/<name>/SKILL.md` **and** its path in the plugin's `skills` array. Only the migration sub-skills stay unregistered, by design.
- **Anatomy.** One self-contained `SKILL.md` per skill, under 500 lines (a step's template or long example goes in `reference/` beside it), with frontmatter `description` (≤ 300 characters, no flags), `argument-hint` (restated as the body's `**Usage:**` line), `model`, and where needed `disable-model-invocation` / `allowed-tools`. No `name` key, no key Claude Code does not document. Body: Desired Outcome → Decision Criteria → Prerequisites → steps, opening with the `Shared files:` line when it cites `@rules/…`-style paths. English only; `output_language` governs generated reports, never the skills.
- **Hooks** (`hooks/hooks.json`; fire automatically under Claude Code, never bypass). `validate-mermaid.sh` on every Write/Edit of Markdown; `validate-frontmatter.sh` on `reports/**` inside a pipeline project (one with `work/pipeline-progress.json` above the file); `record_token_usage.py` after Write/Edit/Agent and at Stop/SubagentStop, appending to `work/token-usage.json` (`rules/token-pricing.md`). Every enabled plugin loads its own copy, so `hooks/claim.sh` lets one copy per `tool_use_id` act — keep that guard in any hook you add. Hook mode exits 2 (fed back for self-correction); CLI mode with file arguments exits 1.
- **Tests.** No unit-test framework; each suite is an executable contract that exits 1 on failure. `bash tools/run-tests.sh` runs them all (`-v` streams, a substring selects); it discovers any `*.test.py` / `*.test.sh`, and `.github/workflows/contracts.yml` runs the same on every push and pull request, then `claude plugin validate . --strict` and `claude plugin validate skills --strict` on a pinned version (which do not reach `skills/product/`, `skills/infra/` or unknown frontmatter keys — the suites own those). What each suite guards is `docs/test-suites.md`; a new suite gets its row in the same commit, or `tools/docs_consistency.test.py` fails. Behavioural evals (`evals/`, `tools/eval-plugin.sh <plugin>`) cost money and run on demand when a `description` changes. Not in the runner: `samples/scalardb-transaction-tests/` (`./gradlew integrationTest`, after a ScalarDB bump). The weekly `refresh-okf-k8s-tf.yml` workflow is not a gate: it collects the k8s-tf bundle's public upstream and opens a pull request; revising the documents is `/architect:revise-knowledge`.
- **Release.** Git-flow by hand: `release/x.y.z` → bump the versions in `marketplace.json` (all plugins share one number) → `CHANGELOG.md` and `CHANGELOG_ja.md` → merge to `main` → annotated tag → GitHub release.

## Command Reference

**117 slash commands across four plugins.** The catalogue — every command with its model,
prerequisites and full flag signature — is `docs/skill-reference.md` (`_ja` for Japanese), read on
demand and deliberately not imported here. This table maps *which group does what*; the counts
partition all 117.

| Group | Entry point | What it does | n |
|-------|-------------|--------------|---|
| **Product Direction** `/product:*` | `/product:start` | Validation-driven pipeline from product vision to SLA/NFR, gating on the riskiest assumptions; hands off to `/architect:define-requirements`. Skills under `skills/product/`, rules under `rules/product/` | 28 |
| **Orchestration & setup** | `/architect:start`, `/architect:pipeline` | Interactive or automated execution of the architect core pipeline, plus `init-output` | 3 |
| **Core pipeline** `/architect:*` | run by the orchestrators | requirements → investigate → analyze → evaluate → redesign → design → review → report. Phases, order, outputs and models are the manifest's: `skills/common/skill-dependencies.yaml` | 29 |
| **Extension tier** | invoked individually | Implementation specs, code generation (REST / GraphQL / ScalarDB / contract, acceptance and characterization tests / IaC / docs), verification and the quality gate, infrastructure / security / observability / DR design, cost estimation, SQL migration to ScalarDB. Enumerated under Pipeline Dependencies | 24 |
| **Backlog Delivery** | `/architect:deliver-backlog` | export → implement → review → merge over GitLab/GitHub work items. Writes **merge-bound code into the project's real source tree**, never `generated/`, and stops at every human gate | 7 |
| **Database Migration** | `/architect:migrate-database` | Oracle / MySQL / PostgreSQL → ScalarDB: schema extraction, analysis, SP/trigger conversion (the router delegates to nested sub-skills) | 4 |
| **ScalarDB Development** `/scalardb:*` | `/scalardb:build-app` | Schema modeling, configuration, scaffolding, CRUD/JDBC patterns, exception handling, code review, migration advice | 11 |
| **Multi-Cloud Infrastructure** `/infra:*` | `/infra:start` | Terraform / Kubernetes / Helm / Kustomize / Argo CD / GitLab CI / Cosign / Vault / ESO / Prometheus / Kyverno across AWS-Azure-GCP × local-test-staging-production, grounded in `okf-k8s-tf`. Skills under `skills/infra/`, rules under `rules/infra/` | 4 |
| **Status & utility** | `/architect:report-status` | One dashboard (`tools/nexus-status.sh`; `Tab` cycles four views), `render-mermaid`, `update-knowledge`, `revise-knowledge`, `report-token-cost`, `investigate-db-design` (DDL/design documents), `investigate-db-live` (catalogs and statistics), `explain` (any generated artifact) | 7 |

Which phases `/architect:pipeline` runs is the manifest's; which the dashboard files under Code
Generation is `CODEGEN_PHASES` in `tools/lib/pipeline_status_data.py`.

## Pipeline Dependencies

```
[define-requirements (optional; the greenfield entry point)]
investigate -> [analyze-ui (optional)] -> analyze -> [evaluate-mmi, evaluate-ddd, evaluate-ux (optional)] -> integrate-evaluations
            \-> [map-domains, analyze-data-model (optional)]
  -> redesign -> [create-domain-story (optional, per domain),
                  design-aggregate (optional, per bounded context),
                  design-state-machine (optional, per aggregate)]
  -> design-microservices -> [design-scalardb | design-data-layer, design-api -> design-graphql (conditional)]
  -> [review-consistency, review-scalardb|review-data-integrity, review-api-security, review-operations, review-risk, review-business]
  -> review-synthesizer -> report -> review-report
```

Dependency manifest (architect): `skills/common/skill-dependencies.yaml`. The **product** plugin
has its own: `skills/product/common/skill-dependencies.yaml` (vision → success-metrics/revenue →
scope → validate-assumptions [gate] → persona/journey/positioning → create-domain-story/design-system
→ ui-mock/features/example-map/data-model/frontend → map-domains/api → sla/nfr → design-architecture
→ review → report; `adapt-change` on demand), ending in the handoff to `/architect:define-requirements`.

The manifest covers the core pipeline only. Twenty-four further architect skills —
`investigate-security`, `select-scalardb-edition`, `design-scalardb-analytics`,
`design-implementation`, `generate-test-specs`, `generate-characterization-tests`,
`generate-scalardb-code`, `generate-api-code`, `generate-graphql-code`, `generate-contract-tests`,
`generate-acceptance-tests`, `generate-infra-code`, `generate-docs`, `verify-implementation`,
`design-sql-migration`, `implement-sql-migration`, `verify-sql-migration`, `design-infrastructure`,
`design-security`, `design-observability`, `design-disaster-recovery`, `estimate-cost`,
`estimate-token-cost`, `report-token-cost` — form a **manual extension tier**: not executed by
`/architect:pipeline` nor by `/architect:start`, invoked individually, typically after the core
pipeline. That list is exactly `EXTENSION_PHASES` in `tools/lib/pipeline_status_data.py`, which the
status dashboard renders as its own group, so the two are edited together.

The extension tier is **not** everything outside the manifest. Three further groups sit outside
both, none run by `/architect:pipeline`: orchestration and setup (`start`, `pipeline`,
`init-output`); status and utility (`report-status`, `render-mermaid`, `update-knowledge`,
`revise-knowledge`, `investigate-db-design`, `investigate-db-live`, `explain`); and two pipelines
in their own right — **Backlog Delivery** (`deliver-backlog`, `export-backlog`,
`implement-backlog`, `review-issue`, `merge-issue`, `capture-followup`, `report-backlog-status`)
and **Database Migration** (`migrate-database`, `migrate-oracle`, `migrate-mysql`,
`migrate-postgresql`).

Within that tier the codegen skills have a fixed follow-on order — **generate code → test it →
document it → verify it**: `generate-api-code` (REST/OpenAPI) or `generate-graphql-code` (Spring
GraphQL), and `generate-scalardb-code` (`domain/` + `infrastructure/`) emit the service between
them; `generate-contract-tests` turns the contract into executable tests and
`generate-acceptance-tests` the Gherkin scenarios into the ATDD outer loop; `generate-infra-code`
emits the IaC plus the CI workflow that enforces the eight-stage quality gate (and
`/product:generate-frontend` the frontend); then `generate-docs` documents what was emitted and
`verify-implementation` checks it against the design — with `--gate`, running that same gate
in-session (`rules/ai-code-quality-gate.md`). On the legacy path `generate-characterization-tests`
sits before all of this, pinning the modules a transformation step touches; on the
backlog-delivery path the same step is Step 5b of `implement-backlog`. SQL migration is a sequence
of its own inside the tier: `design-sql-migration` decides one route per inventoried statement,
`implement-sql-migration` generates the migration module behind an offline gate, and
`verify-sql-migration` proves the routes on data.

**Product → architect handoff.** Both pipelines run in the same project directory. Detect the
handoff by globbing for **files** under `reports/00_core/`, `reports/01_ux/`, `reports/02_spec/`,
`reports/03_domain/`, `reports/04_quality/` and `work/traceability.json` (`/product:init-output`
creates two of those directories empty); when any exist, `define-requirements` reads them instead
of re-eliciting — `docs/design.md` §1.3 maps each artifact to its deliverable, §1.4 lists what
product deliberately does not supply. Three files under `work/` are shared, so **every write is
additive** (`skills/common/progress-registry.md` § One Registry, Two Pipelines):

| File | Rule |
|------|------|
| `pipeline-progress.json` | One `phases` map keyed by bare phase name, holding both pipelines. Never re-register it, drop another manifest's entry, or reset another pipeline's `options` (notably `output_language`). Stamp `"plugin": "product"\|"architect"` on every entry — `map-domains`, `design-api`, `create-domain-story` and `report` exist in both manifests. Where it is absent, confirm a `completed` against the phase's `outputs:` on disk |
| `traceability.json` | One graph. `define-requirements` appends `FR-`/`NFR-` to what product wrote; never a second file, never truncated to `[]`. `id_prefix` on each manifest phase says which skill mints which prefix |
| `context.md` | Decisions, plus **the** Open Questions store for both plugins; `reports/00_requirements/open-questions.md` is a view rendered from it. New IDs are `max(OQ-###) + 1` over the store. Create only when absent; never overwrite |

`/product:adapt-change` walks the shared graph; it **reports** architect nodes in its blast radius
and stops, never re-running an architect skill (`docs/design.md` §7.5).

**The infra plugin is outside all of this** — no manifest, not a phase, not on the dashboard. It
overlaps three architect skills on purpose:

| Architect | Infra | Boundary |
|-----------|-------|----------|
| `/architect:design-infrastructure` → `reports/08_infrastructure/infrastructure-design.md` | `/infra:design` | Upstream/downstream: architect decides the *logical* infrastructure; infra turns it into a concrete multi-cloud, four-environment configuration grounded in `okf-k8s-tf` |
| `/architect:generate-infra-code` → `generated/` | `/infra:implement` | Output location: codegen emits scaffolding plus the quality-gate CI workflow into `generated/`; `/infra:implement` writes merge-bound code into the **real infrastructure repository** |
| `/architect:design-security`, `design-observability`, `design-disaster-recovery` | `/infra:design` sections | Policy vs. means: architect sets the authorization model, SLI/SLO and RTO/RPO; infra decides Vault / ESO / Prometheus / Kyverno and their deployment |
| `/architect:review-operations` | `/infra:review` | Artefact: architect reviews design documents; infra reviews Terraform, manifests and CI, adding ownership overlap, image digest continuity, secret exposure |

## Model Assignment

| Model | Use for | Examples |
|-------|---------|----------|
| **opus** | Architecture decisions, tradeoff analysis, risk, strategy | analyze, redesign, design-microservices, review-risk, product strategy skills, `infra:design` / `infra:review` |
| **sonnet** | Standard analysis, document generation, reviews, implementation | investigate, review-consistency, evaluate-mmi, `infra:implement` |
| **haiku** | Template generation, status checks, simple transforms | init-output, render-mermaid, report, report-status |

The per-skill tier is **data, not prose**: `skills/common/skill-dependencies.yaml` and
`skills/product/common/skill-dependencies.yaml` for pipeline phases, each SKILL.md's `model` for
everything else (`docs/skill-reference.md` lists them). Where the assignment takes effect is
measured in `docs/skill-authoring.md` § Where `model` takes effect; two rules follow, enforced by
`skills/common/subagent-model.test.py`:

- **Every sub-agent call names its `model`**, the calling skill's own tier unless it says otherwise.
- **`/architect:pipeline` runs every phase as a sub-agent on the manifest's `model`**, never inline, in the foreground, three phases at a time.

`/architect:start` and `/product:start` declare `model: inherit`: dialogue-driven phases run
inline on the session's model (they suggest `/model opus` when it is smaller) and every other
phase goes to a sub-agent on its manifest model, whose questions are settled before a dependent
phase starts. No phase declares `effort`. `implement-backlog` is a thin sonnet orchestrator
delegating to tiered sub-agents (haiku digests, sonnet implementation, opus for planning and
consistency verdicts); runtimes without model switching keep the delegation structure at the
session model.

## Output Conventions

All outputs are git-ignored in the project being worked on: `reports/` (analysis and design
documents), `generated/` (code per service), `work/` (pipeline state, intermediate files). Naming
and frontmatter: `rules/output-conventions.md`. In brief:

- **Output language** is per project — `work/pipeline-progress.json` `options.output_language`: `en` (default) or `ja`; `/architect:start` asks at initialization. It governs report prose only; frontmatter keys, Mermaid node IDs, skills and rules stay English.
- **Files**: kebab-case; every output carries YAML frontmatter with `schema_version`; every diagram is Mermaid (hook-validated); each step writes its file on completion (immediate output).
- **Open Questions**: an unknown a skill cannot resolve from its inputs is **asked** — `AskUserQuestion` with derived candidate options, "Other" carrying what they cannot express — and only what the user defers, cannot answer in-session or was never asked (`--auto`) becomes a `TBD`, recorded with its `OQ-` ID, status and owner (`rules/open-questions.md`).
- **Dependency versions**: any generated file that pins a version uses one **looked up** from its registry — never from memory or a skill example — stable, non-EOL, mutually compatible; confirmation per `--confirm-versions` / `--no-confirm-versions` / `options.confirm_versions` (unset → interactive asks, `--auto` adopts); decisions in `work/version-decisions.json` (`rules/dependency-versions.md`).
- **ScalarDB grounding**: every ScalarDB / ScalarDL / ScalarDB Saga decision is grounded in the version-pinned bundle `knowledge/okf-scalardb-scalardl/okf/` (submodule; `tools/update-okf-bundle.sh` fetches / `update` / `status`): pin product, version and edition first, answer from that release's docs (`rules/okf-knowledge-bundle.md`). Without ScalarDB, its skills are skipped and `review-data-integrity` replaces `review-scalardb`.
- **Infrastructure grounding**: every infrastructure decision is grounded in `knowledge/okf-k8s-tf/` (vendored, no remote): fix environment and cloud first, keep fact / guidance / open question apart, cite the document, say "outside the bundle's scope" for `local` and anything production-specific (`rules/okf-k8s-tf-bundle.md`, `rules/infra/*.md`).
- **API contract**: the specification under `reports/03_design/api-specifications/` is the contract; code adds nothing it does not declare, each `operationId` binds to one handler in the contract map, drift is reported, never reconciled silently (`rules/api-contract-fidelity.md`). Every non-2xx response is RFC 9457 Problem Details from the project's type registry (`rules/api-error-standard.md`).
- **Quality gate**: generated or AI-written code passes the eight-stage gate before human review — every stage with evidence, a skipped stage recorded with its reason, a FAIL blocking the handoff (`rules/ai-code-quality-gate.md`). Merge-bound code is written test-first, `test:` → `feat:` → `refactor:` per unit (`rules/tdd-workflow.md`).

## Tool Priority

1. **Serena MCP** (`get_symbols_overview`, `find_symbol`) — structural understanding
2. **Glob/Grep** — file discovery and pattern search
3. **Read** — targeted file reading
4. **Agent (sub-agent)** — large-scale exploration across many files

## Rules & References

Read on demand with the Read tool when the condition applies; deliberately not imported, to keep
session context small — do not load ScalarDB rules for non-ScalarDB work.

| Resource | Location | When to read |
|----------|----------|--------------|
| product input requirements | docs/product-input-requirements.md | Inputs the user supplies before the product pipeline |
| architect input requirements | docs/architect-input-requirements.md | Inputs the user supplies before the architect pipeline |
| DDD technique coverage | docs/ddd-coverage.md | "Does the toolkit do <DDD technique>?", or adding/changing a DDD skill — update the row in the same commit |
| report documentation site | docs/docs-site.md | Serving a project's `reports/` as a local site (`tools/docs-site.sh`) |
| multi-cloud infrastructure guide | docs/infrastructure.md | Using `/infra:*` — setup, the four premises, the boundary with architect |
| skill authoring | docs/skill-authoring.md | Writing or changing a SKILL.md, its frontmatter, hooks or model tier — the measurements behind the rules |
| contract suites | docs/test-suites.md | Changing anything a suite guards, or adding a suite |
| product ↔ architect integration | docs/design.md | Touching the handoff (§1) or `adapt-change` (§7) |
| product skill rules | rules/product/*.md (20 files) | Editing a `/product:*` skill, or `create-domain-story --mode=event-storming`; each SKILL.md names the one it needs — never load the set |
| infra skill rules | rules/infra/*.md (environments, multi-cloud) | Editing an `/infra:*` skill, or a question on the four environments or the portability boundary |
| Open Questions protocol | rules/open-questions.md | Any point where a skill would write `TBD` |
| Output conventions | rules/output-conventions.md | Writing or changing what a skill emits under `reports/` |
| Token pricing & usage | rules/token-pricing.md | Estimating run cost, or reading `work/token-usage.json` |
| Dependency version selection | rules/dependency-versions.md | Writing any file that pins a version |
| OKF bundle: Kubernetes/Terraform | rules/okf-k8s-tf-bundle.md | Any infrastructure design, implementation or review |
| OKF bundle: ScalarDB/ScalarDL/Saga | rules/okf-knowledge-bundle.md | Any ScalarDB / ScalarDL / ScalarDB Saga decision |
| API contract fidelity | rules/api-contract-fidelity.md | Designing an API surface, generating API code or contract tests, verifying against the contract |
| API error standard | rules/api-error-standard.md | Error responses, exception handlers, the ScalarDB exception → HTTP mapping |
| API security checks | rules/api-security-checks.md | Reviewing an API design or API-layer code — OWASP API Top 10 (2023), tenant isolation |
| API style selection | rules/api-style-selection.md | Choosing REST / GraphQL / hybrid / gRPC / AsyncAPI per surface; `api-style-decisions.json` is canonical |
| GraphQL contract fidelity | rules/graphql-contract-fidelity.md | Designing a GraphQL schema, generating resolvers or GraphQL contract tests |
| GraphQL security checks | rules/graphql-security-checks.md | Reviewing GraphQL design or resolvers — read after api-security-checks |
| AI code quality gate | rules/ai-code-quality-gate.md | Gating generated or AI-written code before human review |
| TDD workflow | rules/tdd-workflow.md | Writing merge-bound code or generating a domain layer |
| SQL migration | rules/sql-migration.md | `design-` / `implement-` / `verify-sql-migration` — one route per statement, evidence, verification states |
| Database investigation | rules/database-investigation.md | Design-document and live catalog investigation |
| ScalarDB exception handling | rules/scalardb-exception-handling.md | Exception handling, retry logic |
| ScalarDB CRUD patterns | rules/scalardb-crud-patterns.md | CRUD API operations |
| ScalarDB JDBC patterns | rules/scalardb-jdbc-patterns.md | JDBC/SQL operations |
| ScalarDB cross-service transactions | rules/scalardb-2pc-patterns.md | Shared cluster / Global Transaction API / 2PC / Saga choice; two-phase commit |
| ScalarDB Saga patterns | rules/scalardb-saga-patterns.md | Cross-service eventually consistent transactions |
| ScalarDB config validation | rules/scalardb-config-validation.md | Configuration correctness |
| ScalarDB schema design | rules/scalardb-schema-design.md | Schema and key design |
| ScalarDB Java best practices | rules/scalardb-java-best-practices.md | Java coding standards |
| ScalarDB coding patterns | rules/scalardb-coding-patterns.md | Code generation, design-scalardb, generate-scalardb-code |
| ScalarDB edition profiles | rules/scalardb-edition-profiles.md | Edition selection |
| Evaluation frameworks | rules/evaluation-frameworks.md | MMI/DDD scoring |
| Aggregate design | rules/aggregate-design.md | Modeling, reviewing or generating the tactical model inside a bounded context |
| Architecture Decision Records | rules/architecture-decision-records.md | Making or reviewing a design decision a later phase depends on; the additive `ADR-` allocation |
| Existing UI analysis | rules/ui-analysis.md | `analyze-ui`, and consuming its inventory |
| UX evaluation | rules/ux-evaluation.md | `evaluate-ux`, and merging its score |
| State transition modeling | rules/state-modeling.md | An object with a lifecycle — states, events, the state × event matrix |
| Mermaid best practices | rules/mermaid-best-practices.md | Creating diagrams |
| Spring Boot integration | rules/spring-boot-integration.md | Java code generation |
| Output structure contract | templates/output-structure.md | File dependencies |
| Dependency manifests | skills/common/skill-dependencies.yaml, skills/product/common/skill-dependencies.yaml | Phase order, declared outputs, `model`, `id_prefix`, `conditions` — the source, not prose |
| Sub-agent patterns | skills/common/sub-agent-patterns.md | Spawning sub-agents |
| Progress registry | skills/common/progress-registry.md | `pipeline-progress.json` schema and resume behavior |
| Backlog checklist contract | skills/common/backlog-checklists.md | Ticking Epic/Sub-Epic/Issue checkboxes during backlog delivery |
| ScalarDB references | skills/common/references/ | `api-reference.md`, `interface-matrix.md` (6 interface combinations), `exception-hierarchy.md`, `sql-reference.md`, `schema-format.md`, `configuration-reference.md`, `code-patterns/` (complete app templates) |
