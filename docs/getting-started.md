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

See the [Skill Reference](skill-reference.md) for the full product skill catalog.

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
# 5-perspective parallel review (after design is complete)
# /architect:pipeline runs this automatically, but you can also run it individually
```

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

## 5. ScalarDB Application Development

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

## 6. Database Migration to ScalarDB

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
