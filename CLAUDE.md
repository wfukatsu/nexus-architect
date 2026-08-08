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

This repo is not an application — it is a **Claude Code plugin marketplace** whose product is a corpus of ~90 skill instruction files. There is no compile/build step and no application to run; "developing" here means editing skills, rules, and hooks.

**Packaging.** `.claude-plugin/marketplace.json` defines three plugins (`architect`, `scalardb`, `product`), each with its own version, and lists the skill directories it ships. Skills physically live in a flat `skills/` tree (product skills are nested under `skills/product/`); a plugin "owns" a skill only by listing its path in `marketplace.json`. **Adding a skill requires two edits: create `skills/<name>/SKILL.md` AND register its path in the plugin's `skills` array in `marketplace.json`.** An unregistered SKILL.md will not surface as a slash command.

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

**Tests / release.** No unit-test framework; verification is per-artifact and runnable from the CLI — `hooks/*.sh` self-test via file-path CLI mode, `tools/omnigent/load-skill.test.sh` covers the loader, `skills/generate-docs/marker-mechanics.test.py` asserts the ownership-marker contract that skill states in prose (run with no argument for the embedded fixture, or pass a real README), `skills/implement-backlog/output-location.test.sh` asserts the Output Location interlock — the git-ignore gate, the working-branch commit, and empty-commit detection — against a scratch repository, `skills/capture-followup/followup-contract.test.py` asserts the follow-up ID/manifest contract (F-index allocation, namespace disjointness with positional IDs, `origin` node shape, default-parent resolution) against an embedded fixture manifest (or pass a real one), `tools/lib/backlog_status_data.test.py` asserts the backlog-status derivation contract (tracker-first status precedence with the `labels` array ignored, stage derivation, tree ordering, roll-ups), `tools/lib/pipeline_status_data.test.py` asserts the pipeline-status derivation contract (both shipped `skill-dependencies.yaml` files parsing through the built-in mini-YAML reader, registry-over-filesystem status precedence and the drift it raises, upstream-change invalidation of `completed` phases and its propagation down the dependency chain, declared-output counting, `skip_phases`/`conditions` exclusion, dependency and next-phase selection, extension-tier grouping and its per-skill output declarations staying in step with each SKILL.md, the pipeline/codegen section split — codegen phases leaving their plugin's tree while the dependencies they cross still resolve, the codegen tree grouping by plugin and offering each phase's own slash command, and which plugins a project has evidence of having run — the backlog view's pipeline strip agreeing with the pipeline view, cost attribution), and `tools/nexus-status.test.sh` asserts the dashboard's CLI contract on scratch projects (project resolution and the 0/1/2 exit codes, `--view=auto` selection plus the four addressable views — `product`/`architect` each showing only their own pipeline and `codegen` showing neither's, every output mode incl. `--md` frontmatter and `--ascii` purity, `--group`/`--phase`/`--epic` narrowing `--json` as well as the tree, an unknown `--phase`/`--epic` failing as usage rather than rendering empty — in the live dashboard as well as the one-shot renderers, cross-view agreement, and the refresh poll noticing an overwritten depth-3 report), and `tools/lib/status_tui.test.py` asserts the curses shell's interaction contract without needing a terminal (the `c` key copying rather than launching an opener while the menu's own open entry still opens, the open-label contract between the shell and both data modules, the action-menu hint keeping its close key when `--exec` is off and `e` behaving for open/runnable entries either way, the help panel de-duplicating the legend the pipeline tabs share and scrolling instead of overflowing, an empty tree naming the filter that emptied it rather than declaring the pipeline unrun, a `failed` phase outside the counted set still reaching the header, and `q` being the only key that quits so a stray escape sequence cannot). All exit 1 on failure. Releases are manual git-flow (`release/x.y.z` branch → bump versions in `marketplace.json` → update both `CHANGELOG.md` and `CHANGELOG_ja.md` → merge to `main` → annotated tag → GitHub release); all three plugins share one version number, so bump them together.

## Output Language

Output language is configurable per project. Set in `work/pipeline-progress.json`:
```json
{ "options": { "output_language": "ja" } }
```
Supported: `en` (English, default), `ja` (Japanese). The `/architect:start` orchestrator asks the user to select a language at project initialization.

## Command Reference

### Product Direction (`/product:*`)
Validation-driven pipeline from product vision to SLA/NFR. Skills are namespaced under `skills/product/`; rules under `rules/product/`. Use `/product:start` for interactive/automated execution; hands off to `/architect:define-requirements` for system implementation design.

- `/product:start [target] [--auto] [--profile=mvp|core-only|ux-to-spec|full] [--frontend|--no-frontend] [--lang=ja|en]` — Interactively start product-direction design; runs the validation-driven pipeline in dependency order, gating on the riskiest assumptions. After the UI mocks, offers a selectable `generate-frontend` step (React + Storybook codegen); `--frontend`/`--no-frontend` force the choice
- `/product:init-output [project]` — Initialize the product output tree, pipeline progress file, and traceability graph
- `/product:define-vision` — Define product core (Vision/Mission/Values) as a Product Vision via dialogue
- `/product:name-product` — Name the product as an alphabetic acronym: a short pronounceable Latin-letter name whose every letter is the initial of an English word, so the name expands into a value phrase; grounded in vision/positioning, shortlists candidates and recommends one
- `/product:define-success-metrics` — One North Star Metric plus 3–5 input metrics
- `/product:research-landscape` — Market/competitor research: market sizing (TAM/SAM/SOM), trends
- `/product:design-revenue` — Revenue/business model and a recomputable benefit-evaluation template
- `/product:define-scope` — Normalize constraints and decide product scope (in/out)
- `/product:validate-assumptions` — Extract riskiest assumptions, attach cheapest test, Go/No-Go gate (re-runnable)
- `/product:generate-persona` — Jobs-to-be-Done–anchored personas (job stories + persona cards)
- `/product:map-journey` — Customer journey as a stages × layers grid (touchpoints, actions, emotions)
- `/product:design-positioning` — Positioning (Dunford 5-component canvas), touchpoint × device × timing matrix
- `/product:create-domain-story` — Persona-anchored Domain Storytelling (actors=personas, activities=job stories/journey); the axis UI mocks render
- `/product:design-system` — Build or `--import` a separately-managed design system (DTCG tokens + components + guidelines); the visual language UI mocks render at lo/mid fidelity
- `/product:generate-ui-mock` — Navigable UI mocks for key screens, driven by domain stories and styled by the design system (each activity → a screen, wired into a clickable flow you can step through in story order; tokens injected)
- `/product:generate-frontend` — Turn UI mocks + design system into a runnable React + TypeScript frontend: Atomic Design decomposition (tokens→atoms→molecules→organisms→templates→pages), token-styled components (CSS Modules + CSS variables), react-router wiring from the story flow, and a Storybook story per component variant/state (emits `generated/frontend/`). Dependency versions are resolved from the registries and confirmed per `--confirm-versions`/`--no-confirm-versions`
- `/product:define-features` — Extract features from UI mocks (each screen action becomes a Command/feature)
- `/product:define-data-model` — Derive data model from UI mocks and features (explicit → implicit, 2 passes)
- `/product:map-domains` — Abstract features/entities into bounded contexts (DDD strategic; Core/Supporting/Generic)
- `/product:design-api` — Logical API surface in three API-Led layers (System/Process/Experience)
- `/product:design-sla` — Per-service SLI/SLO/SLA with error budgets from customer expectations
- `/product:define-nfr` — Turn SLOs into measurable NFRs (availability, latency p95/p99, ...)
- `/product:design-architecture` — Synthesize contexts/APIs/data/NFRs into a runtime architecture (container, critical-path sequence, deployment views) and assess platform-technology fitness (Kong, ScalarDB, ScalarDB Analytics, ScalarDL) with Adopt/Conditional/Reject decisions
- `/product:review` — Review product artifacts through four lenses (consistency, traceability, ...)
- `/product:report [--auto] [--lang=ja|en]` — Consolidate artifacts into one self-contained HTML report (validation status first)
- `/product:report-status [--once] [--phase=<name>] [--exec] [--json] [--md] [--ascii] [--lang=ja|en]` — Show where the product pipeline stands on the terminal: the phase tree grouped by pipeline stage, each phase's status and declared-output completion (a finished phase whose upstream changed afterwards reads `stale`, not `completed`), the validation gate's verdict and open-assumption count, per-phase cost, and a next-command action menu; the Product view of the same `tools/nexus-status.sh` dashboard as `/architect:report-status`, which `Tab` cycles with Architect, Code Generation and Backlog Delivery (pass `--once` for an in-session render). `/product:generate-frontend` is tracked in the Code Generation view, not here
- `/product:adapt-change` — Re-propagation engine: compute affected scope from a change and re-run only impacted skills

### Orchestration
- `/architect:start [target_path]` — Interactively start system analysis and design
- `/architect:pipeline [target_path]` — Automated pipeline execution (--resume-from, --rerun-from, --skip-{phase}, --no-scalardb, --lang=en|ja)
- `/architect:init-output [project]` — Initialize output directories

### Requirements
- `/architect:define-requirements [target_path] [--input=<file|dir>] [--auto] [--no-scalardb]` — Requirements definition: FR/NFR classification, data/transaction requirements, Scalar product applicability — ScalarDB / ScalarDB Saga (greenfield entry point)

### Investigation & Analysis
- `/architect:investigate [target_path]` — Tech stack, structure, debt, DDD readiness
- `/architect:investigate-security [target_path]` — OWASP Top 10, access control
- `/architect:analyze [target_path]` — Ubiquitous language, actors, domain mapping
- `/architect:analyze-data-model [target_path]` — Data model, DB design, ER diagrams

### Evaluation
- `/architect:evaluate-mmi [target_path]` — MMI 4-axis qualitative evaluation
- `/architect:evaluate-ddd [target_path]` — DDD 12-criteria 3-layer evaluation
- `/architect:integrate-evaluations` — Merge MMI+DDD, improvement plan

### Design
- `/architect:map-domains` — Domain classification, BC mapping
- `/architect:redesign` — Bounded context redesign
- `/architect:create-domain-story [--domain=<name>] [--auto]` — Domain Storytelling: visualize business processes per domain (interactive 7-stage facilitation or auto-generation from analysis files)
- `/architect:design-microservices` — Target architecture
- `/architect:select-scalardb-edition` — ScalarDB edition selection
- `/architect:design-scalardb` — ScalarDB schema and transaction design
- `/architect:design-scalardb-analytics` — HTAP analytics platform design
- `/architect:design-data-layer` — Generic DB design (non-ScalarDB)
- `/architect:design-api` — REST/GraphQL/gRPC/AsyncAPI specs

### Implementation & Codegen
- `/architect:design-implementation` — Implementation specs
- `/architect:generate-test-specs` — BDD/unit/integration test specs
- `/architect:generate-scalardb-code` — Spring Boot + ScalarDB code generation
- `/architect:generate-infra-code` — K8s/Terraform/Helm code generation
- `/architect:generate-docs [target] [--scope=changed|service|repo] [--source-root=<path>] [--readme-only] [--issue=<id>] [--dry-run] [--auto] [--lang=en|ja]` — Create/update the documentation for code that was generated or implemented: per-service READMEs and `docs/` pages (overview, build & run, configuration, layout, API, operations, traceability) derived from the code that actually exists, with design reports supplying the *why*. Updates in place via ownership markers (`<!-- nexus:begin:<section> -->`) so human-authored prose is preserved, verifies every documented command against a real build target, and reports design-vs-code drift instead of smoothing it over. Runs after the codegen skills (scaffold mode) and as Step 5b of `implement-backlog` (delivery mode — commits the doc changes to the working branch so they land in the same PR/MR)

### Infrastructure
- `/architect:design-infrastructure` — K8s, IaC, multi-environment
- `/architect:design-security` — Auth, secrets management
- `/architect:design-observability` — Monitoring, tracing, alerting
- `/architect:design-disaster-recovery` — RTO/RPO, backup, DR

### Review (5 parallel reviews — scalardb and data-integrity are mutually exclusive)
- `/architect:review-consistency` — Structural coherence (CON-)
- `/architect:review-scalardb` — ScalarDB constraints (SDB-) — runs when scalardb_enabled
- `/architect:review-data-integrity` — Data integrity (DIN-) — runs when scalardb_disabled
- `/architect:review-operations` — Operational readiness (OPS-)
- `/architect:review-risk` — Distributed system risks (RSK-)
- `/architect:review-business` — Business requirements (BIZ-)
- `/architect:review-synthesizer` — Consolidation and quality gate

### Reporting
- `/architect:report` — Markdown to HTML consolidated report
- `/architect:review-report` — Review quality of generated HTML report (completeness, score accuracy, Mermaid syntax, language, structure)
- `/architect:render-mermaid [target_path]` — Mermaid to PNG/SVG + syntax fix
- `/architect:estimate-cost` — Infrastructure, license, operational costs
- `/architect:estimate-token-cost` — Token usage and USD cost of running the pipeline (a-priori from LOC, calibrated by recorded actuals)
- `/architect:report-token-cost [--once] [--follow] [--session=ID] [--since=7d] [--breakdown=cost] [--ascii] [--ambiguous-width=2] [--md] [--json]` — Report the **recorded actual** cost from `work/token-usage.json` + `work/token-usage.jsonl` on the terminal (totals, per-phase cost, per-model cost with in/out/cache-read/cache-write columns, daily timeline, per-session cost with session names, recent events); wraps `tools/token-cost-report.sh`, which on a terminal defaults to an interactive two-pane dashboard polling every 10s — select a phase/model/session/day/event above, read its detail below, where a session shows its transcript log (`--follow` streams events instead, `--session=ID` prints one session + its log non-interactively). The live modes run in the user's own terminal, so pass `--once` for an in-session render
- `/architect:report-status [--once] [--view=product|architect|codegen|backlog] [--group=core|extension] [--phase=<name>] [--exec] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en]` — Show where the architect pipeline stands on the terminal: the phase tree grouped by category (the manual extension tier is its own foldable group), each phase's status (`pending/in_progress/completed/failed/skipped`, registry-first then derived from its declared outputs — plus `stale`, derived, when a dependency wrote something after the phase finished, propagated down the chain so fixing an early phase un-completes everything below it), how many of those outputs exist, whether it wrote something or burned tokens in the last 5 minutes, its unmet dependencies and its recorded cost; wraps `tools/nexus-status.sh`, which on a terminal defaults to a live dashboard polling `work/pipeline-progress.json` every 10s with a per-phase action menu (clipboard copy, or run via `claude` with `--exec`), an `a` key that asks Claude about the selected phase, and `Tab` to cycle its **four views** — Product and Architect (product and architect are separate pipelines, so one tab each), Code Generation (`generate-scalardb-code` / `generate-infra-code` / `generate-docs` / `/product:generate-frontend`, grouped by plugin, since codegen belongs to neither pipeline tree) and Backlog Delivery. The live mode runs in the user's own terminal, so pass `--once` for an in-session render
- `/architect:update-knowledge [--latest] [--status]` — Fetch or update the OKF ScalarDB/ScalarDL/ScalarDB Saga knowledge bundle from remote (wraps `tools/update-okf-bundle.sh`; no flag = ensure present, `--latest` = pull newest, `--status` = show resolved path/commits/versions)

### Backlog Delivery
- `/architect:deliver-backlog [--epic=<id>] [--issue=<id>] [--from=implement|review|merge] [--auto] [--yes-merge] [--max-fix-rounds=N] [--export] [--dry-run] [--lang=en|ja]` — Orchestrator that drives the implementation skill group over a backlog: runs implement → review → (human approval) → merge for each Issue under an Epic, in order, resuming from `backlog-manifest.json`. Semi-autonomous — stops at the human gates (PR/MR approval, merge, blocker decisions); never auto-merges unless `--yes-merge`. Wraps `implement-backlog`, `review-issue`, `merge-issue`
- `/architect:export-backlog [--target=gitlab|github] [--project=<path>|--repo=<owner/name>] [--group=<gitlab-group>] [--dry-run] [--update] [--lang=en|ja]` — Turn the generated reports into a work-item hierarchy on GitLab/GitHub: Epic (What/Why) → Sub-Epic (What/Key Results) → Issue (How). Synthesizes a review-first plan (`reports/backlog/backlog-plan.md` + `backlog-manifest.json`), gates on explicit approval, then creates items idempotently via `glab`/`gh`
- `/architect:implement-backlog [item] [--epic=<id>] [--build-context] [--review-epic[=<id>]] [--out=<path>] [--confirm-versions|--no-confirm-versions] [--refresh-versions] [--dry-run] [--auto] [--lang=en|ja]` — Implement a backlog item (Issue/Sub-Epic/Epic) created by export-backlog while keeping the whole Epic consistent. Reads the parent Epic and sibling Sub-Epics/Issues, cross-checks a shared engineering-context pack (`reports/backlog/shared-context/`), writes code into the target project's real source tree (resolved per its Output Location precedence and verified not git-ignored — never `generated/`, since this code is committed, reviewed and merged), appends progress (comments + `status::*` labels) to the Epic/Sub-Epic/Issue, and runs a lightweight + on-demand whole-Epic consistency review. Executes as a thin sonnet orchestrator delegating heavy steps to model-tiered sub-agents (haiku/sonnet/opus) to minimize token cost. With no item, picks the `status::doing` items and confirms with the user
- `/architect:review-issue [item] [--epic=<id>] [--max-fix-rounds=N] [--base=<branch>] [--no-fix] [--dry-run] [--auto] [--lang=en|ja]` — Review an implemented Issue for whole-Epic consistency (Issue + parent Sub-Epic/Epic + related Issues), auto-fix `[B]` blockers by spawning fix subagents and re-reviewing until they clear (bounded by `--max-fix-rounds` + no-progress detection; on non-convergence it writes a "decision needed" note on the Issue, sets `status::blocked`, and asks the user), then open a PR/MR linked to the Issue and hand off for approval
- `/architect:merge-issue [item|mr|pr] [--strategy=merge|squash|rebase] [--delete-branch] [--yes-merge] [--dry-run] [--auto] [--lang=en|ja]` — After the user approves the Issue's PR/MR, run a merge preflight (open, Mergeable verdict with no open blockers, approvals present, CI green, no conflicts), gate on explicit confirmation, execute the merge via `glab`/`gh`, then close the Issue (`status::done`) and roll up progress to the Sub-Epic/Epic (triggering the whole-Epic review when a Sub-Epic completes)
- `/architect:report-backlog-status [--once] [--sync] [--exec] [--epic=<id>] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en]` — The Backlog Delivery view of the same `tools/nexus-status.sh` dashboard (`tools/backlog-status.sh` is a thin alias; `Tab` cycles the Product / Architect / Code Generation views). Show backlog delivery progress as an Epic → Sub-Epic → Issue tree on the terminal: each item's delivery status (`todo/doing/review/done/blocked`, derived tracker-first then `impl.status` — never the seed `labels`) and its Implemented/Reviewed/Merged stages, plus a follow-up-queue count and a pipeline phase strip; wraps `tools/backlog-status.sh`, which on a terminal defaults to a live dashboard polling `backlog-manifest.json` every 10s with a per-item action menu that generates the next slash command (clipboard copy, or run via `claude` with `--exec`; `s`/`--sync` overlays live `glab`/`gh` labels and flags drift). The live mode runs in the user's own terminal, so pass `--once` for an in-session render
- `/architect:capture-followup [title] [--parent=<local_id|#iid>] [--from=<file|issue-ref>] [--queue-only] [--flush] [--dry-run] [--auto] [--lang=en|ja]` — Capture follow-up work discovered during backlog delivery (deferred tasks, out-of-scope findings, doc drift, split-off scope, waived acceptance criteria) into a reviewable queue (`reports/backlog/followup-queue.md`), then — after an approval gate — register the entries as tracker Issues labeled `status::todo`, linked to the in-flight Sub-Epic/Epic, and appended to `backlog-manifest.json` under the `F`-suffixed local-ID namespace (`I1.2.F1`) with an `origin` trail. Fed by `implement-backlog` / `review-issue` / `merge-issue` via `--queue-only`; the created Issues enter the `deliver-backlog` loop as ordinary work

### ScalarDB Development (`/scalardb:*`)
- `/scalardb:model` — Interactive schema design wizard (keys, indexes, data types)
- `/scalardb:config` — Configuration file generator (Core/Cluster, CRUD/JDBC, 1PC/2PC)
- `/scalardb:scaffold` — Complete starter project generator (all 6 interface combos)
- `/scalardb:error-handler` — Exception handling code generator and code reviewer
- `/scalardb:crud-ops` — CRUD API operation patterns (Get, Scan, Insert, Upsert, Update, Delete)
- `/scalardb:jdbc-ops` — JDBC/SQL operation patterns (SELECT, INSERT, JOIN, aggregates)
- `/scalardb:local-env` — Local Docker Compose environment setup
- `/scalardb:docs` — ScalarDB documentation search and lookup
- `/scalardb:build-app` — Build complete ScalarDB application from requirements
- `/scalardb:review-code` — Review Java code for ScalarDB correctness (16 checks)
- `/scalardb:migrate` — Migration advisor (Core→Cluster, CRUD→JDBC, 1PC→2PC)

### Database Migration (Oracle/MySQL/PostgreSQL → ScalarDB)
- `/architect:migrate-database` — Unified migration router (detects DB type, delegates)
- `/architect:migrate-oracle` — Oracle → ScalarDB (schema extraction, analysis, AQ integration, SP/trigger Java conversion)
- `/architect:migrate-mysql` — MySQL → ScalarDB (schema extraction, analysis, SP/trigger Java conversion)
- `/architect:migrate-postgresql` — PostgreSQL → ScalarDB (schema extraction, analysis, SP/trigger Java conversion)

## Pipeline Dependencies

```
investigate -> analyze -> [evaluate-mmi, evaluate-ddd] -> integrate-evaluations
  -> redesign -> [create-domain-story (optional, per domain)]
  -> design-microservices -> [design-scalardb | design-data-layer, design-api]
  -> [review-consistency, review-scalardb|review-data-integrity, review-operations, review-risk, review-business]
  -> review-synthesizer -> report -> review-report
```

Dependency manifest (architect): @skills/common/skill-dependencies.yaml

The manifest covers the core pipeline only. The remaining architect skills —
`investigate-security`, `select-scalardb-edition`, `design-scalardb-analytics`,
`design-implementation`, `generate-test-specs`, `generate-scalardb-code`,
`generate-infra-code`, `generate-docs`, `design-infrastructure`, `design-security`,
`design-observability`, `design-disaster-recovery`, `estimate-cost`,
`estimate-token-cost`, `report-token-cost` — form a
**manual extension tier**: they are not executed by `/architect:pipeline` — nor by
`/architect:start`, which also runs only the manifest's phases — and are invoked
individually, typically after the core pipeline. See the invocation chains in
README §Code Generation & Delivery and docs/getting-started.md §5–6.

Within that tier the codegen skills have a fixed follow-on order — **generate code →
`generate-docs`**: `generate-scalardb-code` / `generate-infra-code` (and
`/product:generate-frontend`) emit the scaffold, then `generate-docs` documents what
was emitted. On the backlog-delivery path the same step is automatic: it runs as Step 5b
of `implement-backlog`, inside the implement → review → merge chain.

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

The **product** plugin follows the same tiers (per-skill `model` in `skills/product/common/skill-dependencies.yaml`): **opus** (16 skills) for strategy/judgment (`define-vision`, `define-success-metrics`, `research-landscape`, `design-revenue`, `name-product`, `validate-assumptions`, `generate-persona`, `design-positioning`, `create-domain-story`, `design-system`, `define-data-model`, `map-domains`, `design-api`, `design-architecture`, `review`, `adapt-change`), **sonnet** (10 skills) for structured generation and orchestration (`define-scope`, `map-journey`, `generate-ui-mock`, `generate-frontend`, `define-features`, `design-sla`, `define-nfr`, `report`, plus the `start` orchestrator and `init-output`).

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
| Token pricing & usage tracking | rules/token-pricing.md | Estimating run cost, or reading the `work/token-usage.json` ledger recorded during execution |
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
- **Dependency versions**: Any generated file that pins a version (build.gradle/pom, package.json, image tags, Helm/Terraform/K8s) uses a version that was **looked up** from its registry — never recalled from memory or copied from a skill example — and is a stable, non-EOL, mutually compatible release. Whether the resolved set is confirmed with the user is the user's choice: `--confirm-versions` / `--no-confirm-versions` per run, `options.confirm_versions` as the project default (unset → interactive runs ask, `--auto` runs adopt). See @rules/dependency-versions.md
- **ScalarDB-optional**: When ScalarDB is not used, ScalarDB-specific skills are skipped and review-data-integrity replaces review-scalardb
- **ScalarDB/ScalarDL/ScalarDB Saga grounding**: Implementation-method decisions (API usage, config keys, transaction patterns, saga/TCC definitions, edition-gated features) are grounded in the version-pinned OKF knowledge bundle at `knowledge/okf-scalardb-scalardl/` (git submodule) — pin product/version/edition first, answer only from that release's docs. See @rules/okf-knowledge-bundle.md
