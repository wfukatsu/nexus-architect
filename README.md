# Nexus Architect

System architecture toolkit for Claude Code and Codex. Claude Code uses this repository as four plugins with 105 skills; Codex uses the same skill files through `AGENTS.md` compatibility rules.

- **product** (27 skills) — Product direction: validation-driven, dialogue-based pipeline from product vision to SLA/NFR; hands off to architect for system implementation design
- **architect** (61 skills) — Legacy refactoring, greenfield design, database migration, consulting deliverables
- **scalardb** (11 skills) — ScalarDB application development toolkit

## Installation

### As a Claude Code Plugin (Recommended)

```bash
# 1. Add the marketplace
claude plugin marketplace add wfukatsu/nexus-architect

# 2. Install the plugins
claude plugin install product@nexus-architect --scope user
claude plugin install architect@nexus-architect --scope user
claude plugin install scalardb@nexus-architect --scope user
```

After installation, commands are available as `/product:skill-name`, `/architect:skill-name`, and `/scalardb:skill-name`.

To update to the latest version:

```bash
claude plugin update product@nexus-architect
claude plugin update architect@nexus-architect
claude plugin update scalardb@nexus-architect
```

### Manual Installation

```bash
# 1. Clone the repository (with the ScalarDB/ScalarDL knowledge bundle submodule)
git clone --recurse-submodules https://github.com/wfukatsu/nexus-architect.git

# 2. Add as a local marketplace
claude plugin marketplace add ./nexus-architect

# 3. Install the plugins
claude plugin install product@nexus-architect --scope user
claude plugin install architect@nexus-architect --scope user
claude plugin install scalardb@nexus-architect --scope user
```

### Verify Installation

In a Claude Code session, type any command to confirm:

```bash
/product:start
/architect:start
/scalardb:model
```

If the skills are recognized, the installation is successful.

### Using with Codex

Codex can use the same skill files without installing Claude Code plugins.

```bash
# 1. Clone the repository (with the ScalarDB/ScalarDL knowledge bundle submodule)
git clone --recurse-submodules https://github.com/wfukatsu/nexus-architect.git
cd nexus-architect

# 2. Optional Python dependencies
pip install -r requirements.txt
```

Open Codex at the repository root. `AGENTS.md` tells Codex how to translate Claude Code conventions:

- `/product:<name>` -> `skills/product/<name>/SKILL.md` (product skills are nested under `skills/product/`)
- `/architect:<name>` -> `skills/<name>/SKILL.md`
- `/scalardb:<name>` -> `skills/<name>/SKILL.md`
- `CLAUDE_PLUGIN_ROOT` -> the repository root
- `.claude/docs/*` -> `skills/common/references/*`
- `.claude/rules/*` -> `rules/*` (product rules are nested under `rules/product/*`)
- `${CLAUDE_PLUGIN_ROOT}/subagents/*` -> `skills/common/subagents/*`

Then invoke the same command text in chat:

```bash
/product:start
/architect:start ./path/to/target
/architect:pipeline ./path/to/target
/scalardb:model
/scalardb:review-code ./path/to/app
```

When a skill asks to use Claude tools, Codex follows these mappings:

| Claude Code reference | Codex behavior |
|---|---|
| `Read`, `Glob`, `Grep`, `LS` | Use shell reads, `rg`, `rg --files`, `find`, or `ls` |
| `Write`, `Edit`, `MultiEdit` | Edit files with `apply_patch` |
| `Bash` | Run shell commands |
| `AskUserQuestion` | Present numbered choices in chat, add an "or type your own answer" line, and wait for the reply |
| `Task`, `Subagent` | Run in the main Codex thread unless the user explicitly asks for sub-agents |
| `WebFetch`, `WebSearch` | Use Codex web access, Context7, or approved `curl` |

After editing generated reports or Mermaid diagrams in Codex, run the hooks manually when relevant:

```bash
hooks/validate-frontmatter.sh reports/before/example/technology-stack.md
hooks/validate-mermaid.sh reports/before/example/codebase-structure.md
```

Claude Code continues to use the plugin metadata and slash commands unchanged. See [Using Nexus Architect with Codex](docs/codex-usage.md) for the full Codex guide.

## Quick Start

```bash
# Product direction (greenfield: start here, then hand off to /architect:define-requirements)
/product:start

# Interactive workflow (recommended)
/architect:start ./path/to/target

# Automated full pipeline
/architect:pipeline ./path/to/target

# Individual skills
/architect:investigate ./path/to/target
/architect:analyze ./path/to/target
/architect:evaluate-mmi ./path/to/target

# Code generation (after the design pipeline — see Code Generation & Delivery below)
/architect:design-implementation
/architect:generate-scalardb-code
/architect:generate-api-code
/architect:generate-graphql-code
/architect:generate-contract-tests
/architect:generate-docs
/architect:verify-implementation --gate

# Backlog delivery (merge-bound code: implement -> review -> merge, per Issue)
/architect:export-backlog --target=github --repo=<owner>/<name>
/architect:deliver-backlog --epic=E1

# ScalarDB development
/scalardb:scaffold
/scalardb:model
/scalardb:build-app
```

## Commands

**105 slash commands across four plugins.** The full catalogue — every command with its model, its
prerequisites and its complete flag signature — lives in one place:

> **[docs/skill-reference.md](docs/skill-reference.md)** · [日本語](docs/skill-reference_ja.md)

It is the single source of truth; this table is the map of which group does what, and the counts
partition all 105.

| Group | Start here | What it does | n |
|-------|-----------|--------------|---|
| **Product Direction** `/product:*` | `/product:start` | Validation-driven pipeline from product vision to SLA/NFR, gating on the riskiest assumptions before deep design; hands off to `/architect:define-requirements` | 27 |
| **Orchestration & setup** | `/architect:start`, `/architect:pipeline` | Interactive or automated execution of the architect core pipeline, plus `init-output` | 3 |
| **Core pipeline** `/architect:*` | run by the orchestrators | requirements → investigate → analyze → evaluate → redesign → design → review → report — see [Pipeline Dependency Graph](#pipeline-dependency-graph) | 27 |
| **Extension tier** | invoked individually | Implementation specs, code generation (REST / GraphQL / ScalarDB / contract tests / IaC / docs), verification and the eight-stage quality gate, infrastructure / security / observability / DR design, cost estimation — see [Code Generation & Delivery](#code-generation--delivery) | 19 |
| **Backlog Delivery** | `/architect:deliver-backlog` | export → implement → review → merge over GitLab/GitHub work items; writes merge-bound code into the project's real source tree and stops at every human gate | 7 |
| **Database Migration** | `/architect:migrate-database` | Oracle / MySQL / PostgreSQL → ScalarDB: schema extraction, analysis, SP/trigger conversion — see [Database Migration Guide](docs/database-migration.md) | 4 |
| **ScalarDB Development** `/scalardb:*` | `/scalardb:build-app` | Schema modeling, configuration, scaffolding, CRUD/JDBC patterns, exception handling, code review, migration advice — see [ScalarDB Development Guide](docs/scalardb-development.md) | 11 |
| **Multi-Cloud Infrastructure** `/infra:*` | `/infra:start` | Terraform / Kubernetes / Helm / Kustomize / Argo CD / GitLab CI / Cosign / Vault / ESO / Prometheus / Kyverno across AWS-Azure-GCP × local-test-staging-production, grounded in the vendored `okf-k8s-tf` bundle — see [Multi-Cloud Infrastructure Guide](docs/infrastructure.md) | 4 |
| **Status & utility** | `/architect:report-status` | One terminal dashboard (`tools/nexus-status.sh`) whose `Tab` cycles four views — Product, Architect, Code Generation, Backlog Delivery — plus `render-mermaid` and `update-knowledge`. Recorded spend: `/architect:report-token-cost` | 3 |

## Workflows

### Product Direction

Decide product direction before system design: validate the riskiest assumptions early, then derive UX, spec, domains, API, and SLA/NFR. Hands off to the greenfield path via `/architect:define-requirements`.

```
vision -> success-metrics / revenue -> scope -> validate-assumptions [gate]
  -> personas/journey/positioning -> ui-mock/features/data-model
  -> domains/API -> SLA/NFR -> review -> report -> /architect:define-requirements
```

### Product → Architect Handoff

The arrow above is a contract, not a suggestion. Run `/architect:define-requirements` in the same
project directory and it detects the product reports, so system design continues from the product
spec instead of re-eliciting it. Full contract: [docs/design.md §1](docs/design.md).

| | Crosses the boundary | Stays behind, by design |
|---|---|---|
| Requirements | `FEAT-` → `FR-`, link recorded | The binding transaction-consistency class per business process |
| Non-functional | `NFR-` reused **verbatim**, never re-numbered | The physical DB inventory (engines, versions, volumes) |
| Structure | Bounded contexts, scope, constraints | The actor/role/permission matrix |
| Open items | The validation gate's verdict and open assumptions | — |
| People | Personas seed the actor list — a seed only | — |

The three right-hand items are physical decisions a logical product spec should not make, so
`define-requirements` elicits them. A partial product run (`--profile=mvp`) still hands off; the
requirements state which product artifacts were found and which were absent.

Both pipelines then share three files under `work/`: the progress registry, one traceability graph
(`FEAT-` → `FR-` → downstream, in a single chain), and one Open Questions store. Every write is
additive — running architect never resets product's state, and an answer recorded on either side
is visible to the other.

### Legacy Refactoring

Analyze existing systems, evaluate architecture maturity, and design microservices transformation.

```
investigate -> analyze -> evaluate -> redesign -> implement -> review -> report
```

### Greenfield Design

Design new systems from requirements through ScalarDB architecture to deployment.

```
requirements -> domain modeling -> ScalarDB design -> infra -> deploy
```

### Code Generation & Delivery

Code generation is a **manual extension tier**: `/architect:pipeline` and `/architect:start` stop at
the review/report phase, and the codegen skills are invoked individually afterwards. There are two
paths, and they differ in what the output *is*.

**A. Scaffold — regenerable output under `generated/` (git-ignored).**

```
/architect:pipeline ./path/to/project      # design phases, through review + report
  -> /architect:design-implementation      # requires reports/03_design/
  -> /architect:generate-test-specs        # requires reports/06_implementation/
  -> /architect:design-infrastructure      # requires target-architecture.md   (infra path only)
  -> /architect:generate-scalardb-code     # -> generated/{service}/  (domain/ + infrastructure/)
  -> /architect:generate-api-code          # -> generated/{service}/  (api/, bound to the OpenAPI contract)
  -> /architect:generate-graphql-code      # -> generated/{service}/  (api/graphql/, when GraphQL/hybrid)
  -> /architect:generate-contract-tests    # -> generated/{service}/src/test/  (contract breaks fail the build)
  -> /architect:generate-infra-code        # -> generated/infrastructure/  (+ the quality-gate CI workflow)
  -> /architect:generate-docs              # READMEs + docs/ for what was emitted
  -> /architect:verify-implementation      # design <-> code conformance; --gate runs the quality gate
```

Each step only needs the reports of the step before it, so you can enter the chain partway. A re-run
overwrites what it owns — treat this tree as disposable.

**B. Delivery — merge-bound code in the project's real source tree.**

```
/architect:export-backlog --target=github --repo=<owner>/<name>   # Epic / Sub-Epic / Issue
  -> /architect:deliver-backlog --epic=E1                          # per Issue, in order:
       implement  -> review (auto-fix blockers, open PR/MR)
                  -> [human approval]  -> merge -> roll up
```

`implement-backlog` resolves the source root (never `generated/`, verified not git-ignored), commits
to a working branch, and runs `generate-docs` as Step 5b so code and docs land in the same PR/MR.
`deliver-backlog` stops at the human gates; it never merges without approval (or `--yes-merge`).

Single steps are available too: `/architect:implement-backlog <issue>`, `/architect:review-issue
<issue>`, `/architect:merge-issue <issue>`. Work discovered mid-delivery but deferred is captured
with `/architect:capture-followup` — queued locally, then (after an approval gate) registered as
new Issues linked to the in-flight Sub-Epic/Epic, re-entering the loop as `status::todo`. Watch it
all live with `tools/nexus-status.sh` — one dashboard, `Tab` cycling its four views (**Product**,
**Architect**, **Code Generation**, **Backlog Delivery**): the
**backlog** view (`/architect:report-backlog-status`, or the `tools/backlog-status.sh` alias) shows
the tree, per-item delivery stages and an action menu that hands you the next command; the
**pipeline** view (`/architect:report-status`, `/product:report-status`) shows the phase tree with
each phase's status, declared-output completion, what is running right now and its cost — and marks
a finished phase `stale` once an upstream one changed after it, down the whole dependency chain. Both let
you ask Claude about the selected row (`a`) and launch the generated command (`--exec`).

**C. Frontend** — `/product:generate-frontend` (offered by `/product:start` after the UI mocks) emits
a runnable React + Storybook scaffold under `generated/frontend/`.

**D. ScalarDB only** — `/scalardb:build-app` or `/scalardb:scaffold` generate a working application
without needing the report tree.

### ScalarDB Application Development

Build ScalarDB applications with guided schema design, code generation, and code review.

```
/scalardb:model -> /scalardb:config -> /scalardb:scaffold -> /scalardb:review-code
```

### Database Migration to ScalarDB

Migrate existing Oracle, MySQL, or PostgreSQL databases to ScalarDB with automated schema analysis, migration planning, and Java code generation.

```
migrate-database -> schema extraction -> migration analysis -> SP/trigger conversion -> (AQ integration)
```

## Multi-Cloud Infrastructure

A separate plugin (`/infra:*`), not a phase of the architect pipeline. It designs, builds and
reviews the platform underneath the application across **three clouds × four environments**,
grounding every claim in the vendored `okf-k8s-tf` knowledge bundle rather than model memory.

```
/infra:start  (resolve bundle -> freshness -> fix environment + cloud -> route)
     ├─▶ /infra:design      requirements -> ownership split -> L1..L4 -> env matrix -> promotion path -> ADRs
     ├─▶ /infra:implement   Terraform / manifests / Helm values / Kustomize overlays / GitLab CI
     └─▶ /infra:review      ownership overlap · digest continuity · secret exposure, then everything else
```

Four premises are enforced rather than suggested:

| Premise | What it means in practice |
|---------|---------------------------|
| **Multi-cloud is the default** | No answer assumes one cloud. L1 stays cloud-specific with aligned output names; L2–L4 carry no cloud branch at all ([`rules/infra/multi-cloud.md`](rules/infra/multi-cloud.md)) |
| **Four environments** | `local` / `test` / `staging` / `production`. Base, chart and image digest are identical everywhere; differences are **value differences** in an overlay or in values ([`rules/infra/environments.md`](rules/infra/environments.md)) |
| **One resource, one owner** | A resource managed by two or more of Terraform / Argo CD / CI / manual operation is the highest-priority finding there is |
| **The bundle is the source** | Claims carry a `[foundation/terraform.md]`-style citation; what the bundle does not cover is *said* to be outside it. `local` is absent from the bundle entirely and `production` has no observed implementation — both are stated rather than papered over |

Unlike `/architect:generate-infra-code`, which emits scaffolding into `generated/` as a codegen
step of the design pipeline, `/infra:implement` writes merge-bound code into the project's real
infrastructure repository.

## Pipeline Dependency Graph

```
investigate -> analyze -> [evaluate-mmi, evaluate-ddd] -> integrate-evaluations
  -> redesign -> [create-domain-story (optional, per domain),
                  design-aggregate (optional, per bounded context),
                  design-state-machine (optional, per aggregate)]
  -> design-microservices -> [design-scalardb | design-data-layer, design-api -> design-graphql (conditional)]
  -> [review-consistency, review-scalardb | review-data-integrity,
     review-operations, review-risk, review-business]
  -> review-synthesizer -> report -> review-report
```

Everything after `review-report` — the codegen, infrastructure-design, security/observability/DR,
cost and documentation skills — is the **manual extension tier**: not executed by
`/architect:pipeline`, invoked individually. Within it the codegen order is fixed: generate code,
then `generate-docs`.

## Dependency Versions

Any generated file that pins a version (`build.gradle`/`pom.xml`, `package.json`, image tags,
Helm/Terraform/Kubernetes) uses a version that was **looked up from its registry at generation
time** — never recalled from memory — and that is a stable, non-EOL, mutually compatible release.
The decision table is recorded in the artifact and in `work/version-decisions.json`.

Whether the resolved set is confirmed with you is your choice:

```bash
/architect:implement-backlog I1.2.3 --confirm-versions      # always show the table and ask
/product:generate-frontend --no-confirm-versions            # adopt the resolved stable set silently
/architect:generate-scalardb-code --refresh-versions        # ignore the cache, re-resolve
```

```json
// work/pipeline-progress.json — project-level default (asked at /architect:start)
{ "options": { "confirm_versions": true } }
```

Unset means interactive runs ask and `--auto` runs adopt. Some cases always ask: a failed lookup, a
brand-new major as the only option, an EOL current pin, no compatible set, or a licensed/private
registry. See [`rules/dependency-versions.md`](rules/dependency-versions.md).

## ScalarDB / ScalarDL / ScalarDB Saga Knowledge Bundle

Every ScalarDB / ScalarDL / ScalarDB Saga implementation decision (API usage, config keys,
transaction patterns, exception retryability, edition-gated features) is grounded in the
[OKF-ScalarDB-ScalarDL](https://github.com/wfukatsu/OKF-ScalarDB-ScalarDL) knowledge bundle — the
complete official documentation from developers.scalar-labs.com plus the documentation ScalarDB Saga
keeps in its source repository, split **per product and per version** (ScalarDB 3.14–3.19,
ScalarDB Saga 3.19, ScalarDL 3.10–3.13, ScalarDB Community 3.4–3.13; 2,015 concepts).

It is vendored as a git submodule at `knowledge/okf-scalardb-scalardl/`. One command fetches or
updates it from remote (also available as `/architect:update-knowledge`):

```bash
tools/update-okf-bundle.sh           # ensure the bundle is available (fetches only if absent)
tools/update-okf-bundle.sh update    # pull the newest bundle from remote
tools/update-okf-bundle.sh status    # resolved path, local/remote commits, bundled versions
```

Skills follow the protocol in [`rules/okf-knowledge-bundle.md`](rules/okf-knowledge-bundle.md):
pin the project's product, version, and edition first; answer only from that release's docs; cite
the canonical `resource` URL; never mix versions. When the submodule is absent, the script falls
back to a shallow clone under `~/.cache/nexus-architect/`, then skills fall back to the online
docs (explicitly labeled as not version-pinned).

## Kubernetes / Terraform Knowledge Bundle

The `/infra:*` skills have their own OKF bundle, `okf-k8s-tf` — 23 documents covering Terraform,
Kubernetes, Helm, Kustomize, Argo CD, GitLab CI/CD, Docker + Cosign, Vault, External Secrets,
Prometheus/Grafana and Kyverno.

It differs from the ScalarDB bundle in one way that matters: **it is vendored, not a submodule**,
because its origin repository was deleted. There is no remote to update from, and the copy in
`knowledge/okf-k8s-tf/` is the source of record
([`knowledge/OKF-K8S-TF-PROVENANCE.md`](knowledge/OKF-K8S-TF-PROVENANCE.md)).

```bash
tools/update-okf-bundle.sh status --bundle=k8s-tf   # resolved path, OKF version, documents, earliest stale_after
```

Skills follow [`rules/okf-k8s-tf-bundle.md`](rules/okf-k8s-tf-bundle.md): fix the environment and
cloud before reading anything; keep the bundle's three tiers apart in the output — observed
implementation (fact), design guidance (recommendation with a source), open question (unresolved);
cite the document behind each claim; and respect `stale_after`, which is earlier for
`security/kyverno.md` because Kyverno v1.20 plans to remove `kyverno.io/v1 ClusterPolicy`.

The bundle's "observed implementation" tier is scoped to two specific commits. Where a real
repository is available to read, the repository is the fact and the bundle is the standard — the
difference between them gets reported, not smoothed over.

## Output Language

Output language is configurable per project. Set during `/architect:start` initialization or via flag:

```bash
/architect:pipeline ./path/to/project --lang=ja
```

Supported: `en` (English, default), `ja` (Japanese).

### Documentation language policy

All skill instructions (`SKILL.md`), rule files, and embedded prompts are written in **English**; `output_language` applies only to generated report artifacts. User guides under `docs/` are maintained as EN/JA pairs (`getting-started`, `product-input-requirements`, `architect-input-requirements`, `skill-reference`, `scalardb-development`, `database-migration`, `codex-usage`). Exceptions by design: `docs/design.md` (internal design spec, EN only) and the `docs/codex-*` audit records (point-in-time internal audits, JA only).

## Output Structure

All outputs are written to git-ignored directories:

```
reports/          # Analysis and design documents
generated/        # Generated code per service
work/             # Pipeline state and intermediate files
```

## Requirements

- Claude Code CLI (latest), for Claude Code plugin usage
- Codex, for Codex usage
- Python 3.9+
- Node.js 18+ (optional, for Mermaid rendering)

## Optional MCP Servers

- **Serena**: Advanced code analysis with AST-level understanding
- **Context7**: Latest ScalarDB documentation

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation and first steps |
| [product Input Requirements](docs/product-input-requirements.md) | Inputs you supply to run the product pipeline |
| [architect Input Requirements](docs/architect-input-requirements.md) | Inputs you supply to run the architect pipeline |
| [Skill Reference](docs/skill-reference.md) | Complete skill catalog |
| [ScalarDB Development](docs/scalardb-development.md) | ScalarDB development guide |
| [Multi-Cloud Infrastructure](docs/infrastructure.md) | Infrastructure design, implementation and review guide |
| [Database Migration](docs/database-migration.md) | Migration guide (Oracle/MySQL/PostgreSQL) |
| [Codex Usage](docs/codex-usage.md) | Using the same skills from Codex |
| [Changelog](CHANGELOG.md) | Release notes and version history |

Japanese translations:
[Getting Started (日本語)](docs/getting-started_ja.md) |
[product Input Requirements (日本語)](docs/product-input-requirements_ja.md) |
[architect Input Requirements (日本語)](docs/architect-input-requirements_ja.md) |
[Skill Reference (日本語)](docs/skill-reference_ja.md) |
[ScalarDB Development (日本語)](docs/scalardb-development_ja.md) |
[Multi-Cloud Infrastructure (日本語)](docs/infrastructure_ja.md) |
[Database Migration (日本語)](docs/database-migration_ja.md) |
[Codex Usage (日本語)](docs/codex-usage_ja.md) |
[Changelog (日本語)](CHANGELOG_ja.md)

## License

MIT
