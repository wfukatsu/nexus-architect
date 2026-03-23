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

### 1. Analyzing a Legacy System

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

### 2. Full Pipeline Execution

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

### 3. Running Reviews

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

## 4. ScalarDB Application Development

```bash
# Design a schema interactively
/architect:scalardb-model

# Generate a complete starter project
/architect:scalardb-scaffold

# Build a full application from requirements
/architect:scalardb-build-app

# Review code for ScalarDB correctness
/architect:scalardb-review-code
```

See [ScalarDB Development Guide](scalardb-development.md) for details.

## 5. Database Migration to ScalarDB

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
