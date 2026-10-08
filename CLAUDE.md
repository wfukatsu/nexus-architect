# CLAUDE.md

Guidance for Claude Code in the **nexus-architect** repository.

## What This Is

Four-plugin system architecture toolkit:
- **product** — Product direction agent: validation-driven, dialogue-based pipeline from product vision to SLA/NFR; hands off to architect for system implementation design
- **architect** — System architecture agent for legacy refactoring, greenfield design, and consulting deliverables
- **scalardb** — ScalarDB application development toolkit
- **infra** — Multi-cloud (AWS / Azure / GCP) x four-environment (local / test / staging / production) infrastructure agent: design, implementation and review of Terraform / Kubernetes / GitOps, grounded in the vendored OKF `okf-k8s-tf` bundle

Workflows:
- **Product direction**: vision -> success metrics / revenue -> scope -> validate -> personas/journey/positioning -> domain-stories/design-system -> UI/features/data/frontend -> domains/API -> SLA/NFR -> architecture/tech-fitness -> review/report (handoff to `/architect:define-requirements`)
- **Legacy refactoring**: investigate -> analyze -> evaluate -> redesign -> implement
- **Greenfield design**: requirements -> domain modeling -> ScalarDB design -> infra -> deploy
- **Consulting deliverables**: reports, cost estimates, domain stories
- **Infrastructure**: triage (bundle / freshness / environment / cloud) -> design -> implement -> review, per environment and per cloud

Product direction skills: `/product:skill-name`. Architecture skills: `/architect:skill-name`. ScalarDB development tools: `/scalardb:skill-name`. Infrastructure skills: `/infra:skill-name`.
Use `/product:start` to design product direction, `/architect:start` for interactive system analysis/design selection, `/architect:pipeline` for automated execution, or `/infra:start` for infrastructure design, implementation and review.

## Repository Mechanics

This repo is not an application — it is a **Claude Code plugin marketplace** whose product is a corpus of ~120 skill instruction files (116 registered as slash commands, plus the nested migration sub-skills below). There is no compile/build step and no application to run; "developing" here means editing skills, rules, and hooks.

**Packaging.** `.claude-plugin/marketplace.json` defines four plugins (`architect`, `scalardb`, `product`, `infra`), each with its own version, and lists the skill directories it ships. Skills physically live in a flat `skills/` tree (product and infra skills are nested under `skills/product/` and `skills/infra/`); a plugin "owns" a skill only by listing its path in `marketplace.json`. **Adding a skill requires two edits: create `skills/<name>/SKILL.md` AND register its path in the plugin's `skills` array in `marketplace.json`.** An unregistered SKILL.md will not surface as a slash command.

The one deliberate exception is the **migration sub-skills**: `skills/migrate-{oracle,mysql,postgresql}/` each nest their own worker SKILL.md files (`analyze-<db>-schema`, `migrate-<db>-to-scalardb`, `migrate-<db>-sp-trigger-to-scalardb`, plus `migrate-oracle-aq-to-scalardb`) — ten in total, none registered in `marketplace.json`. They are not meant to be slash commands: the parent router skill reads them by `${CLAUDE_PLUGIN_ROOT}/skills/...` path (see OMNIGENT.md §Slash → Path Resolution, *Nested sub-skills*). Leaving one unregistered is intentional there and a bug anywhere else.

**Skill anatomy.** Each skill is a single self-contained `skills/<name>/SKILL.md` with YAML frontmatter:
- `description` — what the skill does and when to use it, at most 300 characters. This is the text the model matches on, and the listing that carries it is capped at 1% of the context window: over the cap Claude Code drops descriptions, least-used skills first. Flags and usage notes do not belong here.
- `argument-hint` — the skill's argument signature (`'[target_path] [--auto]'`), shown at autocomplete. The same signature opens the body as a `**Usage:**` line, because `argument-hint` is an autocomplete hint, not part of the skill's content.
- `model` — `opus` | `sonnet` | `haiku`, or `inherit` on the two interactive orchestrators (see Model Assignment).
- `disable-model-invocation: true` — present on skills that should only run when explicitly called.

A SKILL.md is loaded whole when the skill runs, so it stays under 500 lines: what one step alone needs — a file template, a display format, a long code example — goes in a `reference/` file beside it that the step says to read. What must not be skipped (the order of steps, stop conditions, exception rules) stays in the body. `tools/docs_consistency.test.py` enforces the ceiling.

There is deliberately no `name`: the directory names the skill. On a plugin skill `name` additionally registers the bare command (`/start` beside `/architect:start` — measured on v2.1.294), and eight names are shared between plugins, `start` by three, so the alias would go to whichever plugin loaded first. The Agent Skills specification asks for the field; the Codex and omnigent runtimes resolve skills by path and do not need it. `tools/docs_consistency.test.py` rejects it.

A registered skill is a slash command by default; there is no key to opt in (`user-invocable` exists only to opt *out* with `false`). `tools/docs_consistency.test.py` rejects any frontmatter key outside the set Claude Code documents — an unrecognised key is silently ignored at load time, which is how `user_invocable` survived on 116 skills while doing nothing.

Skill bodies follow a house structure (Desired Outcome → Decision Criteria → Prerequisites table → steps) and reference shared knowledge via `@rules/...`, `@templates/...`, `@skills/common/...`, `@docs/...` paths. That notation is this repository's, not Claude Code's: `@` imports work in CLAUDE.md only, so in a SKILL.md it is plain text and an installed skill runs with the user's project as its working directory. Every SKILL.md that uses the notation therefore opens with the `Shared files:` line that anchors it to `${CLAUDE_PLUGIN_ROOT}` (the same test checks the line is there and every cited file exists). Keep all SKILL.md prose, rules, and embedded prompts in **English**; the per-project `output_language` only governs generated report content, never the skills themselves.

**Hooks (fire automatically — do not bypass).** `hooks/hooks.json` wires PostToolUse/Stop/SubagentStop hooks:
- `validate-mermaid.sh` runs on every Write/Edit and checks any Markdown file's Mermaid blocks, wherever it is written. `validate-frontmatter.sh` is filtered to `reports/` by the handler's `if` (one handler per tool — an `if` rule matches one tool's calls) and requires the file to start with `---` — in a pipeline project only: with no `work/pipeline-progress.json` at or above the file it is inert, as the recorder is, because the plugins are enabled per user and `reports/` is a common directory name (issue #60). In hook mode a failure exits 2 (feeds the error back for self-correction); the same scripts exit 1 when run from the CLI with file-path arguments.
- `record_token_usage.py` runs after Write/Edit/Agent in the background (`async`) and, waiting, at Stop/SubagentStop — `claude -p` kills a background hook at teardown, and the turn-end firing is the one that flushes the pending bucket. It appends to `work/token-usage.json` (the ledger consumed by `/architect:estimate-token-cost`; see `rules/token-pricing.md`).
- **Every enabled plugin registers its own copy.** The four plugins share one source root, so each loads `hooks/hooks.json`, and Claude Code keeps a plugin's copy of a handler separate: unguarded, one Write ran each hook four times and the model read the same error four times. `hooks/claim.sh` (and its Python half in the recorder) lets exactly one copy per `tool_use_id` do the work. Keep that guard in any hook you add.

**Multi-runtime.** The same skills are driven by three orchestrators, each with its own entry doc that must be kept in sync: `CLAUDE.md` (Claude Code, slash commands), `AGENTS.md` (Codex — maps Claude tool names to shell equivalents), `OMNIGENT.md` (generic multi-agent loader in `tools/omnigent/`). When you change how skills are invoked or structured, update all three.

**Tests.** No unit-test framework; verification is per-artifact, runnable from the CLI, and every
suite exits 1 on failure. Each guards a contract that is otherwise only stated in prose — when you
change the thing, run the suite that owns it.

`bash tools/run-tests.sh` runs all of them (`-v` to stream their output, or a substring to run one).
It **discovers** suites — any `*.test.py` / `*.test.sh` in the tree — so a new suite is picked up
without editing the runner or CI. `.github/workflows/contracts.yml` runs the same command on every
push and pull request: per `rules/ai-code-quality-gate.md` the CI half is the enforced one, and a
contract that runs only when someone remembers is not enforced at all.

The same workflow then runs `claude plugin validate . --strict` and `claude plugin validate skills
--strict` with a pinned Claude Code version: what the runtime itself accepts of the manifest and of
the SKILL.md files directly under `skills/`. It does not reach `skills/product/` or `skills/infra/`,
and it does not flag unknown frontmatter keys — the suites own those.

**Behavioural evals are separate and on demand.** `evals/` holds `claude plugin eval` cases that ask
what the suites cannot: given a request in a user's words, is the right entry-point skill chosen.
They need a credential and cost money per run, so they are not in CI — run
`tools/eval-plugin.sh <architect|scalardb|product|infra>` when a `description` changes. The runner
exists because `claude plugin eval` cannot load a plugin defined only as a marketplace entry; it
stages one with that entry's name and skills (`evals/README.md`).

One workflow is not a gate: `.github/workflows/refresh-okf-k8s-tf.yml` collects the vendored
k8s-tf bundle's public upstream every Monday 23:00 JST with no model involved — sources that moved
to a new address rewritten, documents awaiting re-verification listed — and proposes the result as a pull
request. Revising those documents is judgement, and is `/architect:revise-knowledge`, run on demand.

What each suite guards is `docs/test-suites.md` — one row per suite, read on demand and deliberately
not `@`-imported. A new suite gets its row there in the same commit; `tools/docs_consistency.test.py`
fails one the table does not name. One of them is not in the runner: `samples/scalardb-transaction-tests/`
is a Gradle project asserting the ScalarDB transaction rules against a real engine
(`./gradlew integrationTest`), run after a ScalarDB version bump.

**Release.** Manual git-flow: `release/x.y.z` branch → bump versions in `marketplace.json` → update
both `CHANGELOG.md` and `CHANGELOG_ja.md` → merge to `main` → annotated tag → GitHub release. All
three plugins share one version number, so bump them together.

## Output Language

Output language is configurable per project. Set in `work/pipeline-progress.json`:
```json
{ "options": { "output_language": "ja" } }
```
Supported: `en` (English, default), `ja` (Japanese). The `/architect:start` orchestrator asks the user to select a language at project initialization.

## Command Reference

**116 slash commands across four plugins.** The catalogue — every command with its model, its
prerequisites and its full flag signature — is `docs/skill-reference.md` (`_ja` for Japanese), read
on demand with the Read tool and deliberately **not** `@`-imported, since an always-loaded catalogue
is the cost this section exists to avoid. Do not duplicate it here: this table is the map of *which
group does what*, so you know where to look, and the counts below are a partition of all 116.

| Group | Entry point | What it does | n |
|-------|-------------|--------------|---|
| **Product Direction** `/product:*` | `/product:start` | Validation-driven pipeline from product vision to SLA/NFR, gating on the riskiest assumptions; hands off to `/architect:define-requirements`. Skills are namespaced under `skills/product/`, rules under `rules/product/` | 28 |
| **Orchestration & setup** | `/architect:start`, `/architect:pipeline` | Interactive or automated execution of the architect core pipeline, plus `init-output` | 3 |
| **Core pipeline** `/architect:*` | run by the orchestrators | requirements → investigate → analyze → evaluate → redesign → design → review → report. The phases, their order, their declared outputs and their models are the manifest's, not prose: `skills/common/skill-dependencies.yaml` | 29 |
| **Extension tier** | invoked individually | Implementation specs, code generation (REST / GraphQL / ScalarDB / contract tests / acceptance tests / characterization tests / IaC / docs), verification and the quality gate, infrastructure / security / observability / DR design, cost estimation, SQL migration to ScalarDB (design / generation / verification). Enumerated under Pipeline Dependencies below | 24 |
| **Backlog Delivery** | `/architect:deliver-backlog` | export → implement → review → merge over GitLab/GitHub work items. Unlike codegen it writes **merge-bound code into the project's real source tree**, never `generated/`, and stops at every human gate | 7 |
| **Database Migration** | `/architect:migrate-database` | Oracle / MySQL / PostgreSQL → ScalarDB: schema extraction, analysis, SP/trigger conversion (the router delegates to nested sub-skills that are not slash commands) | 4 |
| **ScalarDB Development** `/scalardb:*` | `/scalardb:build-app` | Schema modeling, configuration, scaffolding, CRUD/JDBC patterns, exception handling, code review, migration advice | 11 |
| **Multi-Cloud Infrastructure** `/infra:*` | `/infra:start` | Terraform / Kubernetes / Helm / Kustomize / Argo CD / GitLab CI / Cosign / Vault / ESO / Prometheus / Kyverno across AWS-Azure-GCP x local-test-staging-production, grounded in the vendored `okf-k8s-tf` bundle. Skills are namespaced under `skills/infra/`, rules under `rules/infra/` | 4 |
| **Status & utility** | `/architect:report-status` | One dashboard (`tools/nexus-status.sh`) whose `Tab` cycles four views — Product, Architect, Code Generation, Backlog Delivery — plus `render-mermaid`, `update-knowledge` and `revise-knowledge` (Claude re-verifies the k8s-tf bundle documents the weekly refresh listed). Recorded spend is `/architect:report-token-cost`. Standalone database investigation is `investigate-db-design` (DDL/design documents) and `investigate-db-live` (catalogs and statistics) | 6 |

Two things this table deliberately does not tell you, because the machine-readable source does:
which phases `/architect:pipeline` actually runs (the manifest) and which phases the dashboard files
under Code Generation (`CODEGEN_PHASES` in `tools/lib/pipeline_status_data.py`).

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

Dependency manifest (architect): `skills/common/skill-dependencies.yaml`

The manifest covers the core pipeline only. Twenty-four further architect skills —
`investigate-security`, `select-scalardb-edition`, `design-scalardb-analytics`,
`design-implementation`, `generate-test-specs`, `generate-characterization-tests`, `generate-scalardb-code`,
`generate-api-code`, `generate-graphql-code`, `generate-contract-tests`, `generate-acceptance-tests`, `generate-infra-code`, `generate-docs`,
`verify-implementation`, `design-sql-migration`, `implement-sql-migration`, `verify-sql-migration`, `design-infrastructure`,
`design-security`, `design-observability`, `design-disaster-recovery`, `estimate-cost`,
`estimate-token-cost`, `report-token-cost` — form a
**manual extension tier**: they are not executed by `/architect:pipeline` — nor by
`/architect:start`, which also runs only the manifest's phases — and are invoked
individually, typically after the core pipeline. That list is not prose: it is exactly the
`EXTENSION_PHASES` set in `tools/lib/pipeline_status_data.py`, which is what the status
dashboard renders as its own foldable group, so the two are edited together. See the
invocation chains in README §Code Generation & Delivery and docs/getting-started.md §5–6.

The extension tier is **not** everything outside the manifest. Three further groups sit
outside it and outside the pipeline, each documented in its own section above rather than
here: the orchestration and setup skills (`start`, `pipeline`, `init-output`), the status
and utility skills (`report-status`, `render-mermaid`, `update-knowledge`, `revise-knowledge`, `investigate-db-design`, `investigate-db-live`), and the two
skill groups that are pipelines in their own right —
**Backlog Delivery** (`deliver-backlog`, `export-backlog`, `implement-backlog`,
`review-issue`, `merge-issue`, `capture-followup`, `report-backlog-status`) and **Database Migration**
(`migrate-database`, `migrate-oracle`, `migrate-mysql`, `migrate-postgresql`). None of
them are run by `/architect:pipeline` either.

Within that tier the codegen skills have a fixed follow-on order — **generate code →
test it → document it → verify it**: `generate-api-code` (REST/OpenAPI) or
`generate-graphql-code` (Spring GraphQL), and `generate-scalardb-code` (`domain/` + `infrastructure/`) emit the
service between them, `generate-contract-tests` turns the contract into executable tests and `generate-acceptance-tests` the Gherkin scenarios into the ATDD outer loop,
`generate-infra-code` emits the IaC plus the CI workflow that enforces the eight-stage quality
gate (and `/product:generate-frontend` the frontend), then `generate-docs` documents what was
emitted and `verify-implementation` checks it against the design — with `--gate`, running that
same gate in-session. Read `rules/ai-code-quality-gate.md` before gating generated code; like
every rule in Rules & References it is read on demand, not `@`-imported. On the legacy path,
`generate-characterization-tests` sits before all of this: it pins the current behaviour of the
modules a transformation-plan step touches, and the step is gated on that suite before and after. On the backlog-delivery path the same step is automatic: it runs as Step 5b
of `implement-backlog`, inside the implement → review → merge chain. SQL migration is a sequence of its own
inside the tier: `design-sql-migration` decides one route per inventoried statement, `implement-sql-migration`
generates the migration module from that manifest behind an offline gate, and `verify-sql-migration` proves the
routes on data.

**The infra plugin is outside all of this.** `/infra:*` is not a phase of any manifest, is not run
by `/architect:pipeline`, and does not appear in the status dashboard. It overlaps three architect
skills on purpose, and the boundary is what keeps two systems from writing the same artifact:

| Architect | Infra | Boundary |
|-----------|-------|----------|
| `/architect:design-infrastructure` → `reports/08_infrastructure/infrastructure-design.md` | `/infra:design` | Upstream/downstream. Architect decides the *logical* infrastructure as one phase of the design pipeline; infra turns it into a concrete multi-cloud, four-environment configuration grounded in the `okf-k8s-tf` bundle |
| `/architect:generate-infra-code` → `generated/` | `/infra:implement` | Output location. Codegen emits scaffolding plus the quality-gate CI workflow into `generated/`; `/infra:implement` writes merge-bound code into the project's **real infrastructure repository** |
| `/architect:design-security`, `design-observability`, `design-disaster-recovery` | `/infra:design` sections | Policy vs. means. Architect sets the authorization model, SLI/SLO and RTO/RPO; infra decides Vault / ESO / Prometheus / Kyverno and how they are deployed |
| `/architect:review-operations` | `/infra:review` | Artefact. Architect reviews operational readiness in design documents; infra reviews Terraform, manifests and CI, and adds the checks architect has none of — ownership overlap, image digest continuity, secret exposure |

**Product → architect handoff.** The two pipelines run in the same project directory and share
three files under `work/`: `pipeline-progress.json` (one `phases` map holding both pipelines'
entries, keyed by bare phase name — hence the `plugin` field, since `map-domains`, `design-api`,
`create-domain-story` and `report` are defined by both manifests), `traceability.json` (one graph;
`define-requirements` appends `FR-`/`NFR-` to what product wrote, and `id_prefix` on each manifest
phase says which skill mints which prefix), and `context.md` (decisions, plus **the** Open Questions store for both plugins — `reports/00_requirements/open-questions.md` is a view rendered from it, and `OQ-` IDs are allocated `max + 1` over the store so the two pipelines cannot mint the same one). **Every
write to them is additive** — see `skills/common/progress-registry.md` § One Registry, Two Pipelines
and `docs/design.md` §1 for the contract, §7.5 for why `adapt-change` reports at the boundary rather
than crossing it.

The **product** plugin has its own pipeline and manifest: `skills/product/common/skill-dependencies.yaml` (vision -> success-metrics/revenue -> scope -> validate-assumptions [gate] -> persona/journey/positioning -> create-domain-story/design-system -> ui-mock/features/example-map/data-model/frontend -> map-domains/api -> sla/nfr -> design-architecture -> review -> report; `adapt-change` on demand). It ends by handing off to `/architect:define-requirements`.

## Output Conventions

All outputs are git-ignored:

```
reports/                    # Analysis and design documents
generated/                  # Generated code per service
work/                       # Pipeline state, intermediate files
```

Naming and frontmatter rules: `rules/output-conventions.md`

## Model Assignment

| Model | Use For | Examples |
|-------|---------|----------|
| **opus** | Architecture decisions, tradeoff analysis, risk | analyze, review-risk, redesign, design-microservices |
| **sonnet** | Standard analysis, document generation, reviews | investigate, review-consistency, evaluate-mmi |
| **haiku** | Template generation, status checks, simple transforms | init-output, render-mermaid, report |

**Where the assignment takes effect — measured, not assumed** (Claude Code v2.1.293–294; issue #52). A skill's `model` applies when the user types its slash command, for that turn. It does **not** apply when another skill invokes it in the same turn — the phase then runs on the invoking skill's model — and it does not apply inside a sub-agent, which runs on the `model` passed on the call or, with none, on the user's sub-agent default. Two rules follow, and `skills/common/subagent-model.test.py` enforces both:

- **Every sub-agent call names its `model`**, the calling skill's own tier unless it says otherwise (`skills/common/sub-agent-patterns.md` § Always pass `model`).
- **`/architect:pipeline` runs every phase as a sub-agent on the manifest's `model`**, never inline (`skills/pipeline/SKILL.md` § Phase Execution). The price is that a phase cannot ask the user: what it would have asked is recorded `unasked` in the Open Questions store. Phase calls pass `run_in_background: false`, and tell the phase to do the same for its own sub-agents: a non-interactive run otherwise launches parallel calls in the background and loses the ones still running when a turn ends.

- **The interactive orchestrators declare `model: inherit`.** `/architect:start` and `/product:start` run dialogue-driven phases inline, because only the main conversation can ask the user, and an inline phase runs on what the conversation runs on — a tier on the orchestrator would be the tier of every one of them. Inline phases therefore run on the session's model (the orchestrators suggest `/model opus` when it is smaller); `/architect:start` sends every phase that is not dialogue-driven to a sub-agent on its manifest model and then asks the user what that phase could not, and `/product:start --auto` does the same for all of its phases.

The **product** plugin follows the same tiers (per-skill `model` in `skills/product/common/skill-dependencies.yaml`): **opus** (17 skills) for strategy/judgment (`define-vision`, `define-success-metrics`, `research-landscape`, `design-revenue`, `name-product`, `validate-assumptions`, `generate-persona`, `design-positioning`, `create-domain-story`, `design-system`, `example-map`, `define-data-model`, `map-domains`, `design-api`, `design-architecture`, `review`, `adapt-change`), **sonnet** (9 skills) for structured generation (`define-scope`, `map-journey`, `generate-ui-mock`, `generate-frontend`, `define-features`, `design-sla`, `define-nfr`, `report`, plus `init-output`), **inherit** for the `start` orchestrator (see above), and **haiku** (1 skill) for the status renderer (`report-status`). That last one is the plugin's 28th skill and the only one the manifest does not list — it is not a pipeline phase, so its `model` lives in its own SKILL.md frontmatter.

The **infra** plugin has no manifest at all — its four skills are a router plus three modes, not a
pipeline — so every `model` lives in its own SKILL.md frontmatter: **opus** for `design` and
`review`, **sonnet** for `implement` and the `start` router. The criterion is stated in
`skills/infra/start/SKILL.md` § Model Policy and is worth repeating because it differs from the
tiers above: how hard the error is to undo, times how many tokens it generates. Design and review
emit little and cost much when wrong; implementation emits the most and is held by written
conventions plus verification commands.

## Tool Priority

1. **Serena MCP** (get_symbols_overview, find_symbol) — structural understanding
2. **Glob/Grep** — file discovery and pattern search
3. **Read** — targeted file reading
4. **Agent (sub-agent)** — large-scale exploration across many files

## Rules & References

Read these files on demand with the Read tool when the "When to Read" condition applies.
They are intentionally NOT auto-imported (no `@` prefix) to keep session context small —
do not load ScalarDB rules for non-ScalarDB work.

| Resource | Location | When to Read |
|----------|----------|--------------|
| product input requirements | docs/product-input-requirements.md | Inputs the user must supply before running the product pipeline |
| architect input requirements | docs/architect-input-requirements.md | Inputs the user must supply before running the architect pipeline (legacy or greenfield) |
| DDD technique coverage | docs/ddd-coverage.md | Answering "does the toolkit do <DDD technique>?", or adding/changing a DDD-related skill — update the row in the same commit |
| report documentation site | docs/docs-site.md | Serving or building a project's `reports/` as a local site (`tools/docs-site.sh`, Blume) — what the sync converts, how routes and links are derived, why pages are MDX |
| multi-cloud infrastructure guide | docs/infrastructure.md | Using the `/infra:*` plugin — setup, the four enforced premises, the worked flow, and the boundary with the architect infrastructure skills |
| product skill rule set | rules/product/*.md (20 files: vision-frameworks, success-metrics, scope-prioritization, revenue-models, assumption-validation, persona-jtbd, journey-mapping, positioning-kano-hook, naming-frameworks, design-system, ui-to-domain, example-mapping, event-storming, atomic-react-storybook, ddd-strategic, api-led-connectivity, sla-nfr, architecture-and-tech-fitness, review-and-report, adaptation-engine) | Editing a `/product:*` skill, or the architect skill that borrows one (`create-domain-story --mode=event-storming` reads `event-storming.md`). Each SKILL.md `@`-references the one it needs, so read a file here only when working on that skill — never load the set |
| Open Questions protocol | rules/open-questions.md | Any point where a skill would write `TBD` — how to ask the user with AskUserQuestion (free text via the appended "Other"), what never to ask, and how to record what stays open |
| Token pricing & usage tracking | rules/token-pricing.md | Estimating run cost, or reading the `work/token-usage.json` ledger recorded during execution |
| API contract fidelity | rules/api-contract-fidelity.md | Designing an API surface, generating API-layer code or contract tests, or verifying code against the contract — OpenAPI as the single contract, the `operationId` binding, the contract map, the drift protocol, the contract test stack |
| Database investigation | rules/database-investigation.md | Design-document and live catalog/statistics investigation, scoped adapters, evidence, partial coverage and credential handling |
| SQL migration | rules/sql-migration.md | Designing, implementing or verifying the move of existing SQL to ScalarDB (`design-sql-migration`, `implement-sql-migration`, `verify-sql-migration`) — one route per inventoried statement, dynamic SQL, the edition gate for ScalarDB SQL, evidence and verification states the manifest validator enforces |
| API error standard | rules/api-error-standard.md | Designing error responses, generating an exception handler, or reviewing either — RFC 9457 Problem Details, the problem type registry, and the ScalarDB exception to HTTP mapping (incl. the `UnknownTransactionStatusException` branch) |
| API security checks | rules/api-security-checks.md | Reviewing an API design or API-layer code — OWASP API Security Top 10 (2023) as concrete checks, plus tenant-isolation and transaction-boundary security |
| API style selection | rules/api-style-selection.md | Choosing REST / GraphQL / hybrid / gRPC / AsyncAPI per API surface — the per-surface decision unit, the evidence it rests on, and `reports/03_design/api-style-decisions.json` as the canonical machine-readable contract (the `.md` is a generated view; the database product never derives the style) |
| GraphQL contract fidelity | rules/graphql-contract-fidelity.md | Designing a GraphQL schema, generating resolvers or GraphQL contract tests, or verifying code against the SDL — the `.graphqls` files as the contract, the `<parentType>.<fieldName>` field coordinate as the implementation join key, schema evolution, the error carrier, the contract-map shape, the drift protocol |
| GraphQL security checks | rules/graphql-security-checks.md | Reviewing a GraphQL design or GraphQL resolver code — read **after** rules/api-security-checks.md: nested-field authorization, tenant isolation, query-depth/complexity denial of service, DataLoader cache partitioning, subscriptions, introspection/tooling, error leakage |
| AI code quality gate | rules/ai-code-quality-gate.md | Gating generated or AI-written code before human review — the eight stages, their evidence requirements, and the verdict rules |
| TDD workflow | rules/tdd-workflow.md | Writing merge-bound application code (`implement-backlog` Step 5, `review-issue` fixes) or generating a domain layer — the Red → Green → Refactor commit series, the ATDD outer loop and walking skeleton, the Fake-per-port / injected-Clock structure that makes test-first possible, the exemptions, and what the gate records |
| Dependency version selection | rules/dependency-versions.md | Writing any file that pins a version (build.gradle/pom, package.json, image tags, Helm/Terraform/K8s) — how to look up the current stable release and whether to confirm it with the user |
| OKF knowledge bundle (Kubernetes/Terraform/GitOps platform docs, vendored) | rules/okf-k8s-tf-bundle.md | Any infrastructure design, implementation or review — resolve the bundle, fix environment and cloud, keep fact / guidance / open question separate, cite what it covers and say when something is outside it |
| infra skill rule set | rules/infra/*.md (2 files: environments, multi-cloud) | Editing an `/infra:*` skill, or answering an infrastructure question that turns on the four environments or the portability boundary. Each infra SKILL.md `@`-references the one it needs |
| OKF knowledge bundle (ScalarDB/ScalarDL/ScalarDB Saga official docs, version-pinned) | rules/okf-knowledge-bundle.md | Any ScalarDB/ScalarDL/ScalarDB Saga design, implementation, review, or migration decision — resolve the bundle, pin product/version/edition, ground the answer in that release's docs |
| ScalarDB exception handling | rules/scalardb-exception-handling.md | Exception handling, retry logic |
| ScalarDB CRUD patterns | rules/scalardb-crud-patterns.md | CRUD API operations |
| ScalarDB JDBC patterns | rules/scalardb-jdbc-patterns.md | JDBC/SQL operations |
| ScalarDB cross-service transactions | rules/scalardb-2pc-patterns.md | Choosing between shared cluster / Global Transaction API / 2PC / Saga; two-phase commit protocol |
| ScalarDB Saga patterns | rules/scalardb-saga-patterns.md | Cross-service eventually consistent transactions — saga/TCC definitions, idempotency, server config, escalation handling |
| ScalarDB config validation | rules/scalardb-config-validation.md | Configuration correctness |
| ScalarDB schema design | rules/scalardb-schema-design.md | Schema and key design |
| ScalarDB Java best practices | rules/scalardb-java-best-practices.md | Java coding standards |
| ScalarDB coding patterns | rules/scalardb-coding-patterns.md | Code generation, design-scalardb, generate-scalardb-code |
| ScalarDB edition profiles | rules/scalardb-edition-profiles.md | Edition selection |
| Evaluation frameworks | rules/evaluation-frameworks.md | MMI/DDD scoring |
| Aggregate design | rules/aggregate-design.md | Modeling, reviewing or generating code for the tactical model inside a bounded context — what earns an aggregate, value objects before entities, the seven well-formedness rules, one command / one aggregate / one transaction, and the concrete example every invariant carries |
| Architecture Decision Records | rules/architecture-decision-records.md | Making or reviewing a design decision a later phase depends on (`redesign`, `design-microservices`, `design-scalardb` / `design-data-layer`, `design-api`, `review-consistency`) — what earns a record, the MADR shape and frontmatter the validator checks, the index as a view, and the additive `ADR-` allocation contract shared by five skills |
| Existing UI analysis | rules/ui-analysis.md | Analyzing, or consuming the analysis of, an existing UI (`analyze-ui`, and `evaluate-ux` / `analyze` / `define-requirements` reading its inventory) — what counts as a screen, component, feature and view-layer logic, detection per UI technology, the inventory shape, the nine well-formedness rules, the as-is DTCG token file, the navigation definitions |
| UX evaluation | rules/ux-evaluation.md | Scoring the UX of an existing UI (`evaluate-ux`) or merging that score (`integrate-evaluations`) — static vs runtime evidence, the five axes and their metric caps, the UXI formula and bands, the Nielsen / WCAG 2.2 criteria vocabulary, the finding shape |
| State transition modeling | rules/state-modeling.md | Modeling, reviewing or generating code for an object with a lifecycle — what earns a state machine, the seven well-formedness rules, the state x event matrix, and why a transition is a transaction |
| Mermaid best practices | rules/mermaid-best-practices.md | Creating diagrams |
| Spring Boot integration | rules/spring-boot-integration.md | Java code generation |
| Output structure contract | templates/output-structure.md | File dependencies |
| Dependency manifests | skills/common/skill-dependencies.yaml (architect), skills/product/common/skill-dependencies.yaml (product) | Anything that turns on phase order, a phase's declared outputs, its `model`, `id_prefix` or `conditions` — the manifests are the source, not prose |
| Product ↔ architect integration | docs/design.md | Touching the handoff (§1: artifact mapping, designed gaps, the cross-plugin traceability write-back) or `adapt-change` (§7) |
| Output conventions | rules/output-conventions.md | Writing or changing what a skill emits under `reports/` — frontmatter, file naming, the immediate-output rule |
| Contract suites | docs/test-suites.md | Changing anything a suite guards, or adding a suite |
| Sub-agent patterns | skills/common/sub-agent-patterns.md | Spawning sub-agents |
| Progress registry | skills/common/progress-registry.md | pipeline-progress.json schema and resume behavior |
| Backlog checklist contract | skills/common/backlog-checklists.md | Ticking Epic/Sub-Epic/Issue checkboxes during backlog delivery |
| API reference | skills/common/references/api-reference.md | ScalarDB API details |
| Interface matrix | skills/common/references/interface-matrix.md | 6 interface combinations |
| Exception hierarchy | skills/common/references/exception-hierarchy.md | Exception decision tree |
| SQL reference | skills/common/references/sql-reference.md | SQL grammar and limitations |
| Schema format | skills/common/references/schema-format.md | JSON/SQL schema format |
| Configuration reference | skills/common/references/configuration-reference.md | All ScalarDB config properties by backend |
| Code patterns | skills/common/references/code-patterns/ | Complete app templates for all 6 interface combos |

## Conventions

- **Output language**: Configurable per project (`en` default, `ja` supported)
- **File naming**: kebab-case for all generated files
- **Frontmatter**: Every output file must include YAML frontmatter with `schema_version`
- **Diagrams**: All diagrams use Mermaid syntax (validated by hook)
- **Immediate output**: Each skill step writes its output file upon completion
- **Open Questions**: An unknown a skill cannot resolve from its inputs is **asked** — `AskUserQuestion` with derived candidate options, where the harness-appended "Other" carries any answer the options cannot express (free-form values are asked as bands, or in prose when bands are meaningless). Only what the user defers, cannot answer in-session, or was never asked (`--auto`) becomes a `TBD`, recorded with its question ID, status and owner. See `rules/open-questions.md`
- **Dependency versions**: Any generated file that pins a version (build.gradle/pom, package.json, image tags, Helm/Terraform/K8s) uses a version that was **looked up** from its registry — never recalled from memory or copied from a skill example — and is a stable, non-EOL, mutually compatible release. Whether the resolved set is confirmed with the user is the user's choice: `--confirm-versions` / `--no-confirm-versions` per run, `options.confirm_versions` as the project default (unset → interactive runs ask, `--auto` runs adopt). See `rules/dependency-versions.md`
- **ScalarDB-optional**: When ScalarDB is not used, ScalarDB-specific skills are skipped and review-data-integrity replaces review-scalardb
- **ScalarDB/ScalarDL/ScalarDB Saga grounding**: Implementation-method decisions (API usage, config keys, transaction patterns, saga/TCC definitions, edition-gated features) are grounded in the version-pinned OKF knowledge bundle at `knowledge/okf-scalardb-scalardl/` (git submodule) — pin product/version/edition first, answer only from that release's docs. See `rules/okf-knowledge-bundle.md`
