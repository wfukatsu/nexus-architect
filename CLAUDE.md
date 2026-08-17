# CLAUDE.md

Guidance for Claude Code in the **nexus-architect** repository.

## What This Is

Three-plugin system architecture toolkit:
- **product** — Product direction agent: validation-driven, dialogue-based pipeline from product vision to SLA/NFR; hands off to architect for system implementation design
- **architect** — System architecture agent for legacy refactoring, greenfield design, and consulting deliverables
- **scalardb** — ScalarDB application development toolkit

Workflows:
- **Product direction**: vision -> success metrics / revenue -> scope -> validate -> personas/journey/positioning -> domain-stories/design-system -> UI/features/data/frontend -> domains/API -> SLA/NFR -> architecture/tech-fitness -> review/report (handoff to `/architect:define-requirements`)
- **Legacy refactoring**: investigate -> analyze -> evaluate -> redesign -> implement
- **Greenfield design**: requirements -> domain modeling -> ScalarDB design -> infra -> deploy
- **Consulting deliverables**: reports, cost estimates, domain stories

Product direction skills: `/product:skill-name`. Architecture skills: `/architect:skill-name`. ScalarDB development tools: `/scalardb:skill-name`.
Use `/product:start` to design product direction, `/architect:start` for interactive system analysis/design selection, or `/architect:pipeline` for automated execution.

## Repository Mechanics

This repo is not an application — it is a **Claude Code plugin marketplace** whose product is a corpus of ~110 skill instruction files (99 registered as slash commands, plus the nested migration sub-skills below). There is no compile/build step and no application to run; "developing" here means editing skills, rules, and hooks.

**Packaging.** `.claude-plugin/marketplace.json` defines three plugins (`architect`, `scalardb`, `product`), each with its own version, and lists the skill directories it ships. Skills physically live in a flat `skills/` tree (product skills are nested under `skills/product/`); a plugin "owns" a skill only by listing its path in `marketplace.json`. **Adding a skill requires two edits: create `skills/<name>/SKILL.md` AND register its path in the plugin's `skills` array in `marketplace.json`.** An unregistered SKILL.md will not surface as a slash command.

The one deliberate exception is the **migration sub-skills**: `skills/migrate-{oracle,mysql,postgresql}/` each nest their own worker SKILL.md files (`analyze-<db>-schema`, `migrate-<db>-to-scalardb`, `migrate-<db>-sp-trigger-to-scalardb`, plus `migrate-oracle-aq-to-scalardb`) — ten in total, none registered in `marketplace.json`. They are not meant to be slash commands: the parent router skill reads them by `${CLAUDE_PLUGIN_ROOT}/skills/...` path (see OMNIGENT.md §Slash → Path Resolution, *Nested sub-skills*). Leaving one unregistered is intentional there and a bug anywhere else.

**Skill anatomy.** Each skill is a single self-contained `skills/<name>/SKILL.md` with YAML frontmatter:
- `description` — multi-line; first line is the summary, followed by the `/plugin:skill` invocation form and usage notes (this text is what the model matches on).
- `model` — `opus` | `sonnet` | `haiku` (see Model Assignment).
- `user_invocable: true` — exposes it as a slash command.
- `disable-model-invocation: true` — present on skills that should only run when explicitly called.
Skill bodies follow a house structure (Desired Outcome → Decision Criteria → Prerequisites table → steps) and reference shared knowledge via `@rules/...`, `@templates/...`, `@skills/common/...` paths — resolved repo-relative. Keep all SKILL.md prose, rules, and embedded prompts in **English**; the per-project `output_language` only governs generated report content, never the skills themselves.

**Hooks (fire automatically — do not bypass).** `hooks/hooks.json` wires PostToolUse/Stop/SubagentStop hooks:
- `validate-mermaid.sh` + `validate-frontmatter.sh` run on every Write/Edit/MultiEdit. They validate files written under `reports/`: frontmatter must start with `---`, Mermaid must parse. In hook mode a failure exits 2 (feeds the error back for self-correction); the same scripts exit 1 when run from the CLI with file-path arguments.
- `record_token_usage.py` runs on Write/Edit/MultiEdit/Task/Agent and at Stop/SubagentStop, appending to `work/token-usage.json` (the ledger consumed by `/architect:estimate-token-cost`; see @rules/token-pricing.md).

**Multi-runtime.** The same skills are driven by three orchestrators, each with its own entry doc that must be kept in sync: `CLAUDE.md` (Claude Code, slash commands), `AGENTS.md` (Codex — maps Claude tool names to shell equivalents), `OMNIGENT.md` (generic multi-agent loader in `tools/omnigent/`). When you change how skills are invoked or structured, update all three.

**Tests.** No unit-test framework; verification is per-artifact, runnable from the CLI, and every
suite exits 1 on failure. Each guards a contract that is otherwise only stated in prose — when you
change the thing, run the suite that owns it.

`bash tools/run-tests.sh` runs all of them (`-v` to stream their output, or a substring to run one).
It **discovers** suites — any `*.test.py` / `*.test.sh` in the tree — so a new suite is picked up
without editing the runner or CI. `.github/workflows/contracts.yml` runs the same command on every
push and pull request: per @rules/ai-code-quality-gate.md the CI half is the enforced one, and a
contract that runs only when someone remembers is not enforced at all.

| Suite | Guards |
|-------|--------|
| `hooks/*.sh <file>` (file-path CLI mode) | The two output validators themselves: frontmatter present, Mermaid parses |
| `tools/omnigent/load-skill.test.sh` | The omnigent loader's skill resolution |
| `skills/generate-docs/marker-mechanics.test.py` | The `<!-- nexus:begin:<section> -->` ownership-marker contract that skill states in prose (no argument = embedded fixture; or pass a real README) |
| `skills/implement-backlog/output-location.test.sh` | The Output Location interlock against a scratch repo: git-ignore gate, working-branch commit, empty-commit detection |
| `skills/capture-followup/followup-contract.test.py` | The follow-up ID/manifest contract: `F`-index allocation, disjointness from positional IDs, `origin` node shape, default-parent resolution |
| `tools/lib/backlog_status_data.test.py` | Backlog-status derivation: tracker-first precedence (seed `labels` ignored), stage derivation, tree order, roll-ups |
| `tools/lib/pipeline_status_data.test.py` | Pipeline-status derivation, and with it the two manifests themselves: mini-YAML parsing, the `id_prefix` registry (declared, used in its own SKILL.md, non-colliding — `NFR-` the sole deliberate cross-manifest claim), registry-over-filesystem precedence and its drift, the four shared phase names resolved by `plugin` (or corroborated by outputs), the `<plugin>:<phase>` token buckets, upstream-change invalidation propagating down the chain, extension-tier and codegen grouping staying in step with each SKILL.md |
| `tools/graphql_skills.test.py` | The Spring for GraphQL chain (71 checks): the conditional phases downstream of `design-api`, `api-style-decisions.json` as the canonical decision that withdraws the wrong generator and fails closed when invalid, and the design-safety rules (database never selects GraphQL, field coordinate as join key, tenant-safe loading, query DoS budgets) |
| `tools/nexus-status.test.sh` | The dashboard's CLI contract on scratch projects: project resolution, 0/1/2 exit codes, the four addressable views, every output mode, `--group`/`--phase`/`--epic` narrowing `--json` too, unknown filters failing as usage, cross-view agreement, refresh poll |
| `tools/docs_consistency.test.py` | The documentation split itself: both catalogues describing all 99 registered commands, the signature block matching each SKILL.md (no flag invented by prose, none dropped, none re-spelled, every flag a skill documents about itself offered, and — for the skills that wrap a shell tool — no flag that tool's parser would reject), the grouped tables in CLAUDE.md/README summing to the registry, the extension-tier and codegen prose equal to `EXTENSION_PHASES`/`CODEGEN_PHASES`, AGENTS.md knowing every skill, the catalogue pointer staying un-`@`-imported, no flag mentioned anywhere without belonging to a documented surface, and the Japanese catalogue keeping row order plus each row's model tier / flags / tool references |
| `tools/lib/status_tui.test.py` | The curses shell's interaction contract without a terminal: `c` copies rather than opens, the action-menu/help behaviour with and without `--exec`, an empty tree naming its filter, `q` as the only quit key |

**The one suite that runs real code.** `samples/scalardb-transaction-tests/` is a runnable Gradle
project (`./gradlew integrationTest`, 25 tests, ~10s) asserting the ScalarDB transaction rules
against a **real engine** over in-process SQLite — no container, no external service. It is outside
the CLI suite above because it needs network for dependency resolution. Run it after a ScalarDB
version bump: every rule it backs was written or corrected because one of these tests failed.

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

**99 slash commands across three plugins.** The catalogue — every command with its model, its
prerequisites and its full flag signature — is `docs/skill-reference.md` (`_ja` for Japanese), read
on demand with the Read tool and deliberately **not** `@`-imported, since an always-loaded catalogue
is the cost this section exists to avoid. Do not duplicate it here: this table is the map of *which
group does what*, so you know where to look, and the counts below are a partition of all 99.

| Group | Entry point | What it does | n |
|-------|-------------|--------------|---|
| **Product Direction** `/product:*` | `/product:start` | Validation-driven pipeline from product vision to SLA/NFR, gating on the riskiest assumptions; hands off to `/architect:define-requirements`. Skills are namespaced under `skills/product/`, rules under `rules/product/` | 27 |
| **Orchestration & setup** | `/architect:start`, `/architect:pipeline` | Interactive or automated execution of the architect core pipeline, plus `init-output` | 3 |
| **Core pipeline** `/architect:*` | run by the orchestrators | requirements → investigate → analyze → evaluate → redesign → design → review → report. The phases, their order, their declared outputs and their models are the manifest's, not prose: @skills/common/skill-dependencies.yaml | 25 |
| **Extension tier** | invoked individually | Implementation specs, code generation (REST / GraphQL / ScalarDB / contract tests / IaC / docs), verification and the quality gate, infrastructure / security / observability / DR design, cost estimation. Enumerated under Pipeline Dependencies below | 19 |
| **Backlog Delivery** | `/architect:deliver-backlog` | export → implement → review → merge over GitLab/GitHub work items. Unlike codegen it writes **merge-bound code into the project's real source tree**, never `generated/`, and stops at every human gate | 7 |
| **Database Migration** | `/architect:migrate-database` | Oracle / MySQL / PostgreSQL → ScalarDB: schema extraction, analysis, SP/trigger conversion (the router delegates to nested sub-skills that are not slash commands) | 4 |
| **ScalarDB Development** `/scalardb:*` | `/scalardb:build-app` | Schema modeling, configuration, scaffolding, CRUD/JDBC patterns, exception handling, code review, migration advice | 11 |
| **Status & utility** | `/architect:report-status` | One dashboard (`tools/nexus-status.sh`) whose `Tab` cycles four views — Product, Architect, Code Generation, Backlog Delivery — plus `render-mermaid` and `update-knowledge`. Recorded spend is `/architect:report-token-cost` | 3 |

Two things this table deliberately does not tell you, because the machine-readable source does:
which phases `/architect:pipeline` actually runs (the manifest) and which phases the dashboard files
under Code Generation (`CODEGEN_PHASES` in `tools/lib/pipeline_status_data.py`).

## Pipeline Dependencies

```
[define-requirements (optional; the greenfield entry point)]
investigate -> analyze -> [evaluate-mmi, evaluate-ddd] -> integrate-evaluations
            \-> [map-domains, analyze-data-model (optional)]
  -> redesign -> [create-domain-story (optional, per domain)]
  -> design-microservices -> [design-scalardb | design-data-layer, design-api -> design-graphql (conditional)]
  -> [review-consistency, review-scalardb|review-data-integrity, review-api-security, review-operations, review-risk, review-business]
  -> review-synthesizer -> report -> review-report
```

Dependency manifest (architect): @skills/common/skill-dependencies.yaml

The manifest covers the core pipeline only. Nineteen further architect skills —
`investigate-security`, `select-scalardb-edition`, `design-scalardb-analytics`,
`design-implementation`, `generate-test-specs`, `generate-scalardb-code`,
`generate-api-code`, `generate-graphql-code`, `generate-contract-tests`, `generate-infra-code`, `generate-docs`,
`verify-implementation`, `design-infrastructure`,
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
and utility skills (`report-status`, `render-mermaid`, `update-knowledge`), and the two
skill groups that are pipelines in their own right —
**Backlog Delivery** (`deliver-backlog`, `export-backlog`, `implement-backlog`,
`review-issue`, `merge-issue`, `capture-followup`, `report-backlog-status`) and **Database Migration**
(`migrate-database`, `migrate-oracle`, `migrate-mysql`, `migrate-postgresql`). None of
them are run by `/architect:pipeline` either.

Within that tier the codegen skills have a fixed follow-on order — **generate code →
test it → document it → verify it**: `generate-api-code` (REST/OpenAPI) or
`generate-graphql-code` (Spring GraphQL), and `generate-scalardb-code` (`domain/` + `infrastructure/`) emit the
service between them, `generate-contract-tests` turns the contract into executable tests,
`generate-infra-code` emits the IaC plus the CI workflow that enforces the eight-stage quality
gate (and `/product:generate-frontend` the frontend), then `generate-docs` documents what was
emitted and `verify-implementation` checks it against the design — with `--gate`, running that
same gate in-session. Read `rules/ai-code-quality-gate.md` before gating generated code; like
every rule in Rules & References it is read on demand, not `@`-imported. On the backlog-delivery path the same step is automatic: it runs as Step 5b
of `implement-backlog`, inside the implement → review → merge chain.

**Product → architect handoff.** The two pipelines run in the same project directory and share
three files under `work/`: `pipeline-progress.json` (one `phases` map holding both pipelines'
entries, keyed by bare phase name — hence the `plugin` field, since `map-domains`, `design-api`,
`create-domain-story` and `report` are defined by both manifests), `traceability.json` (one graph;
`define-requirements` appends `FR-`/`NFR-` to what product wrote, and `id_prefix` on each manifest
phase says which skill mints which prefix), and `context.md` (decisions, plus **the** Open Questions store for both plugins — `reports/00_requirements/open-questions.md` is a view rendered from it, and `OQ-` IDs are allocated `max + 1` over the store so the two pipelines cannot mint the same one). **Every
write to them is additive** — see @skills/common/progress-registry.md § One Registry, Two Pipelines
and @docs/design.md §1 for the contract, §7.5 for why `adapt-change` reports at the boundary rather
than crossing it.

The **product** plugin has its own pipeline and manifest: `skills/product/common/skill-dependencies.yaml` (vision -> success-metrics/revenue -> scope -> validate-assumptions [gate] -> persona/journey/positioning -> create-domain-story/design-system -> ui-mock/features/data-model/frontend -> map-domains/api -> sla/nfr -> design-architecture -> review -> report; `adapt-change` on demand). It ends by handing off to `/architect:define-requirements`.

## Output Conventions

All outputs are git-ignored:

```
reports/                    # Analysis and design documents
generated/                  # Generated code per service
work/                       # Pipeline state, intermediate files
```

Naming and frontmatter rules: @rules/output-conventions.md

## Model Assignment

| Model | Use For | Examples |
|-------|---------|----------|
| **opus** | Architecture decisions, tradeoff analysis, risk | analyze, review-risk, redesign, design-microservices |
| **sonnet** | Standard analysis, document generation, reviews | investigate, review-consistency, evaluate-mmi |
| **haiku** | Template generation, status checks, simple transforms | init-output, render-mermaid, report |

The **product** plugin follows the same tiers (per-skill `model` in `skills/product/common/skill-dependencies.yaml`): **opus** (16 skills) for strategy/judgment (`define-vision`, `define-success-metrics`, `research-landscape`, `design-revenue`, `name-product`, `validate-assumptions`, `generate-persona`, `design-positioning`, `create-domain-story`, `design-system`, `define-data-model`, `map-domains`, `design-api`, `design-architecture`, `review`, `adapt-change`), **sonnet** (10 skills) for structured generation and orchestration (`define-scope`, `map-journey`, `generate-ui-mock`, `generate-frontend`, `define-features`, `design-sla`, `define-nfr`, `report`, plus the `start` orchestrator and `init-output`), and **haiku** (1 skill) for the status renderer (`report-status`). That last one is the plugin's 27th skill and the only one the manifest does not list — it is not a pipeline phase, so its `model` lives in its own SKILL.md frontmatter.

## Tool Priority

1. **Serena MCP** (get_symbols_overview, find_symbol) — structural understanding
2. **Glob/Grep** — file discovery and pattern search
3. **Read** — targeted file reading
4. **Task (sub-agent)** — large-scale exploration across many files

## Rules & References

Read these files on demand with the Read tool when the "When to Read" condition applies.
They are intentionally NOT auto-imported (no `@` prefix) to keep session context small —
do not load ScalarDB rules for non-ScalarDB work.

| Resource | Location | When to Read |
|----------|----------|--------------|
| product input requirements | docs/product-input-requirements.md | Inputs the user must supply before running the product pipeline |
| architect input requirements | docs/architect-input-requirements.md | Inputs the user must supply before running the architect pipeline (legacy or greenfield) |
| product skill rule set | rules/product/*.md (18 files: vision-frameworks, success-metrics, scope-prioritization, revenue-models, assumption-validation, persona-jtbd, journey-mapping, positioning-kano-hook, naming-frameworks, design-system, ui-to-domain, atomic-react-storybook, ddd-strategic, api-led-connectivity, sla-nfr, architecture-and-tech-fitness, review-and-report, adaptation-engine) | Editing a `/product:*` skill. Each product SKILL.md `@`-references the one it needs, so read a file here only when working on that skill — never load the set |
| Open Questions protocol | rules/open-questions.md | Any point where a skill would write `TBD` — how to ask the user with AskUserQuestion (free text via the appended "Other"), what never to ask, and how to record what stays open |
| Token pricing & usage tracking | rules/token-pricing.md | Estimating run cost, or reading the `work/token-usage.json` ledger recorded during execution |
| API contract fidelity | rules/api-contract-fidelity.md | Designing an API surface, generating API-layer code or contract tests, or verifying code against the contract — OpenAPI as the single contract, the `operationId` binding, the contract map, the drift protocol, the contract test stack |
| API error standard | rules/api-error-standard.md | Designing error responses, generating an exception handler, or reviewing either — RFC 9457 Problem Details, the problem type registry, and the ScalarDB exception to HTTP mapping (incl. the `UnknownTransactionStatusException` branch) |
| API security checks | rules/api-security-checks.md | Reviewing an API design or API-layer code — OWASP API Security Top 10 (2023) as concrete checks, plus tenant-isolation and transaction-boundary security |
| API style selection | rules/api-style-selection.md | Choosing REST / GraphQL / hybrid / gRPC / AsyncAPI per API surface — the per-surface decision unit, the evidence it rests on, and `reports/03_design/api-style-decisions.json` as the canonical machine-readable contract (the `.md` is a generated view; the database product never derives the style) |
| GraphQL contract fidelity | rules/graphql-contract-fidelity.md | Designing a GraphQL schema, generating resolvers or GraphQL contract tests, or verifying code against the SDL — the `.graphqls` files as the contract, the `<parentType>.<fieldName>` field coordinate as the implementation join key, schema evolution, the error carrier, the contract-map shape, the drift protocol |
| GraphQL security checks | rules/graphql-security-checks.md | Reviewing a GraphQL design or GraphQL resolver code — read **after** rules/api-security-checks.md: nested-field authorization, tenant isolation, query-depth/complexity denial of service, DataLoader cache partitioning, subscriptions, introspection/tooling, error leakage |
| AI code quality gate | rules/ai-code-quality-gate.md | Gating generated or AI-written code before human review — the eight stages, their evidence requirements, and the verdict rules |
| Dependency version selection | rules/dependency-versions.md | Writing any file that pins a version (build.gradle/pom, package.json, image tags, Helm/Terraform/K8s) — how to look up the current stable release and whether to confirm it with the user |
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
| Mermaid best practices | rules/mermaid-best-practices.md | Creating diagrams |
| Spring Boot integration | rules/spring-boot-integration.md | Java code generation |
| Output structure contract | templates/output-structure.md | File dependencies |
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
- **Open Questions**: An unknown a skill cannot resolve from its inputs is **asked** — `AskUserQuestion` with derived candidate options, where the harness-appended "Other" carries any answer the options cannot express (free-form values are asked as bands, or in prose when bands are meaningless). Only what the user defers, cannot answer in-session, or was never asked (`--auto`) becomes a `TBD`, recorded with its question ID, status and owner. See @rules/open-questions.md
- **Dependency versions**: Any generated file that pins a version (build.gradle/pom, package.json, image tags, Helm/Terraform/K8s) uses a version that was **looked up** from its registry — never recalled from memory or copied from a skill example — and is a stable, non-EOL, mutually compatible release. Whether the resolved set is confirmed with the user is the user's choice: `--confirm-versions` / `--no-confirm-versions` per run, `options.confirm_versions` as the project default (unset → interactive runs ask, `--auto` runs adopt). See @rules/dependency-versions.md
- **ScalarDB-optional**: When ScalarDB is not used, ScalarDB-specific skills are skipped and review-data-integrity replaces review-scalardb
- **ScalarDB/ScalarDL/ScalarDB Saga grounding**: Implementation-method decisions (API usage, config keys, transaction patterns, saga/TCC definitions, edition-gated features) are grounded in the version-pinned OKF knowledge bundle at `knowledge/okf-scalardb-scalardl/` (git submodule) — pin product/version/edition first, answer only from that release's docs. See @rules/okf-knowledge-bundle.md
