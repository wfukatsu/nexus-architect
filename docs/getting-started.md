# Getting Started

## Setup

```bash
# Clone the repository
git clone https://github.com/wfukatsu/nexus-architect.git
cd nexus-architect

# Python dependencies (optional)
pip install -r requirements.txt

# Mermaid CLI (optional, for diagram rendering)
npm install -g @mermaid-js/mermaid-cli
```

## Basic Usage

### Claude Code vs. Codex

In Claude Code, install the plugins and use the slash commands directly.

In Codex, open a session at the repository root and use the same command text in chat. `AGENTS.md` maps `/product:<name>`, `/architect:<name>`, and `/scalardb:<name>` to the matching `SKILL.md` file (`/product:<name>` resolves to `skills/product/<name>/SKILL.md`). See [Using Nexus Architect with Codex](codex-usage.md) for details.

### 1. Deciding Product Direction (greenfield)

Start here for a new product: a validation-driven pipeline from vision to SLA/NFR that hands off to `/architect:define-requirements`.

```bash
# Interactive pipeline (gates on the riskiest assumptions before deep design)
/product:start

# Pick a smaller scope with a profile
/product:start --profile=mvp

# Include the React + Storybook frontend codegen step (or omit it with --no-frontend)
/product:start --frontend

# Then hand off to system implementation design
/architect:define-requirements
```

After the UI mocks, `/product:start` can optionally run `/product:generate-frontend` to turn the mocks plus the active design system into a runnable React + Storybook scaffold under `generated/frontend/` (Atomic Design, token-styled). It is selectable: confirmed interactively, or forced with `--frontend` / `--no-frontend`.

Need a name for the product? `/product:name-product` builds an **acronym name** — a short pronounceable Latin-letter name whose every letter is the initial of an English word, so the name expands into a phrase that states the product's value (e.g. `N`ext-generation `E`xtensible e`X`change `U`nified `S`ystem). It draws the expansion words from your vision and positioning, shortlists candidates, and recommends one. It runs after the vision in the `full` profile, or standalone any time:

```bash
/product:name-product                     # from the current vision/positioning
/product:name-product --seed=SCALAR       # find an English word for each letter of a base word
/product:name-product --style=initialism  # spelled-out letters (e.g. SDK) instead of a pronounceable word
```

See the [Skill Reference](skill-reference.md) for the full product skill catalog, and the [product Input Requirements](product-input-requirements.md) for the inputs you should prepare before running the pipeline.

#### What the handoff actually does

`/architect:define-requirements` is not a fresh start. Run it in the same project directory and it
finds the product reports itself, so you are confirming and extending rather than re-answering.
The full contract is [design.md §1](design.md#1-product--architect-handoff-contract); the parts
worth knowing before you run it:

**What crosses.** Features become functional requirements and keep the link (`FEAT-012` →
`FR-007`), so a requirement can be traced back to the screen, the job story and the vision it came
from. NFRs are **reused verbatim** — the same `NFR-` IDs, not re-numbered — so the targets product
set are the targets architect designs against. Scope, constraints, bounded contexts and the
validation gate's open assumptions all carry over. Personas seed the actor list, but only as a
seed: they are user segments, not a role/permission matrix.

**What does not, by design.** Three things are deliberately left for architect to elicit, because
they are physical decisions a logical product spec should not make: the binding
transaction-consistency class per business process, the physical DB inventory (engines, versions,
volumes), and the actor/role/permission matrix. Seeing them asked is the contract working, not
product having forgotten something.

**A partial product run still hands off.** Stopping at `--profile=mvp` is fine —
`define-requirements` states which product artifacts it found and which were absent, and any `FR-`
it had to elicit fresh is recorded as such rather than attributed to a feature that was never
written.

**Both pipelines then share three files under `work/`** — the progress registry, one traceability
graph, and one Open Questions store. Every skill writes to them additively, so running architect
never resets product's state, and a question architect answers is answered for a later product
rerun too. If you are writing your own tooling against these files, read
[design.md §1.5](design.md) and `skills/common/progress-registry.md` first.

### 2. Analyzing a Legacy System

```bash
# Interactive workflow (recommended)
/architect:start ./path/to/legacy-project

# Or run individual skills step by step
/architect:investigate ./path/to/legacy-project
/architect:analyze ./path/to/legacy-project
/architect:evaluate-mmi ./path/to/legacy-project
/architect:evaluate-ddd ./path/to/legacy-project
/architect:integrate-evaluations
```

No legacy system at hand? Use the bundled sample monolith at `samples/ec-monolith`
as the target path to try the analysis workflow end to end.

See the [architect Input Requirements](architect-input-requirements.md) for the inputs you should prepare for the legacy and greenfield (`/architect:define-requirements`) paths.

### 3. Full Pipeline Execution

```bash
# Run all phases automatically
/architect:pipeline ./path/to/project

# Run without ScalarDB
/architect:pipeline ./path/to/project --no-scalardb

# Analysis only
/architect:pipeline ./path/to/project --analyze-only

# Resume from a specific phase
/architect:pipeline ./path/to/project --resume-from=design-microservices
```

### 4. Running Reviews

```bash
# 6-perspective parallel review (after design is complete)
# /architect:pipeline runs this automatically, but you can also run it individually
```

### 5. Generating Code

The codegen skills are **not** part of `/architect:pipeline` — it stops after the review and report
phases. Run them yourself afterwards, in this order:

```bash
# 1. Turn the design into coding-ready specs        (requires reports/03_design/)
/architect:design-implementation

# 2. Test specifications                            (requires reports/06_implementation/)
/architect:generate-test-specs
/architect:generate-characterization-tests            # legacy path only: pin current behaviour before a transformation step

# 3. Application code                               (requires reports/06_implementation/ + scalardb-schema.md)
/architect:generate-scalardb-code                   # -> generated/{service}/  domain/ + infrastructure/
/architect:generate-api-code                        # -> generated/{service}/  api/, bound to the OpenAPI contract
/architect:generate-graphql-code                    # -> generated/{service}/  api/graphql/, when GraphQL/hybrid
/architect:generate-contract-tests                  # -> generated/{service}/src/test/
/architect:generate-acceptance-tests                # -> generated/{service}/src/test/  (Gherkin executable, @wip until implemented)

# 4. Infrastructure code                            (requires reports/08_infrastructure/)
/architect:design-infrastructure                    # run this first if you have no infra reports yet
/architect:generate-infra-code                      # -> generated/infrastructure/

# 5. Documentation for what was just emitted
/architect:generate-docs

# 6. Verify the code against the design, and run the quality gate
/architect:verify-implementation --gate
```

Each step needs only the reports produced by the step before it, so you can enter the chain partway
if those reports already exist. Everything here lands under `generated/`, which is git-ignored and
**overwritten on re-run** — treat it as a disposable scaffold, not a codebase you hand-edit.

Two shortcuts that skip the report tree entirely: `/scalardb:build-app` (requirements → running
ScalarDB application) and `/product:generate-frontend` (UI mocks → React + Storybook scaffold under
`generated/frontend/`).

### 6. Delivering Code Through a Backlog

When the code is meant to be reviewed and merged — not regenerated — use the delivery path instead.
It writes into the project's **real source tree** and drives each Issue to a merged PR/MR:

```bash
# Reports -> Epic / Sub-Epic / Issue on the tracker (asks for approval before creating anything)
/architect:export-backlog --target=github --repo=<owner>/<name>
/architect:export-backlog --target=gitlab --project=<group>/<project>

# Drive every Issue under an Epic: implement -> review -> [your approval] -> merge
/architect:deliver-backlog --epic=E1

# Or one step at a time
/architect:implement-backlog I1.2.3     # code + docs on a working branch
/architect:review-issue I1.2.3          # whole-Epic review, blocker auto-fix, opens the PR/MR
/architect:merge-issue I1.2.3           # preflight + confirmation, merge, roll up
```

`deliver-backlog` is semi-autonomous: it stops at the human gates (PR/MR approval, the merge itself,
blocker decisions) and resumes from `reports/backlog/backlog-manifest.json`. Progress shows up on the
tracker as `status::*` labels, progress comments, and ticked checkboxes — acceptance criteria as they
are implemented and verified, and a parent's task-list box when its child merges.

Prerequisites: `gh` or `glab` authenticated for the target project.

### 7. Choosing Dependency Versions

Whenever a generated file pins a version, the version is looked up from its registry at generation
time and a stable, non-EOL, compatible release is chosen — the decision table is written to
`work/version-decisions.json`. You decide whether to approve it:

```bash
/architect:generate-scalardb-code --confirm-versions      # show the table and ask
/product:generate-frontend --no-confirm-versions          # adopt the resolved set silently
/architect:implement-backlog I1.2.3 --refresh-versions    # re-resolve instead of reusing the cache
```

Set it once per project instead in `work/pipeline-progress.json`
(`/architect:start` asks for this alongside the output language):

```json
{ "options": { "confirm_versions": true } }
```

Unset means interactive runs ask and `--auto` runs adopt.

## Checking Output

All outputs are generated in the following directories:

```
reports/          # Analysis and design documents (Markdown)
generated/        # Generated code (Java, K8s manifests, etc.)
work/             # Pipeline state
```

Consolidated HTML report:
```bash
/architect:report
# -> reports/00_summary/full-report.html
```

Browse everything under `reports/` as a local documentation site — sidebar per phase, search,
Mermaid rendered, the OpenAPI/AsyncAPI specs as an API reference (Blume, Node ≥ 22.12):
```bash
tools/docs-site.sh            # sync + dev server, re-syncs as reports/ changes
```
See docs/docs-site.md.

## 8. ScalarDB Application Development

```bash
# Design a schema interactively
/scalardb:model

# Generate a complete starter project
/scalardb:scaffold

# Build a full application from requirements
/scalardb:build-app

# Review code for ScalarDB correctness
/scalardb:review-code
```

See [ScalarDB Development Guide](scalardb-development.md) for details.

## 9. Database Migration to ScalarDB

```bash
# Unified entry point (asks which database)
/architect:migrate-database

# Or go directly to a specific database
/architect:migrate-oracle
/architect:migrate-mysql
/architect:migrate-postgresql
```

Prerequisites: Python 3.9+, database client tools, `pip install python-dotenv mysql-connector-python psycopg2-binary`

See [Database Migration Guide](database-migration.md) for details.

## MCP Servers (Recommended)

- **Serena**: Ideal for AST-level code analysis and symbol search
- **Context7**: Dynamic retrieval of the latest ScalarDB documentation
