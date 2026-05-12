---
description: |
  Unified database migration router. Analyzes Oracle, MySQL, or PostgreSQL schemas
  and generates ScalarDB migration documentation, Java code, and AQ integration.
  /architect:migrate-database to start. Routes to database-specific workflows.
model: sonnet
user_invocable: true
---
# Command: migrate-database (Unified Migration Entry Point)

## Purpose

Unified entry point for all database-to-ScalarDB migrations. Asks the user which database type they want to migrate, then delegates to the appropriate database-specific command which handles everything: configuration detection, parameter collection, schema analysis, and migration documentation generation.

---

## Execution Instructions

You MUST follow these steps exactly in order. Do NOT skip any step.

---

### STEP 1: Ask Which Database to Migrate

Use the `AskUserQuestion` tool to determine the source database:

```json
{
  "questions": [
    {
      "question": "Which database do you want to migrate to ScalarDB?",
      "header": "Database",
      "options": [
        {"label": "Oracle", "description": "Migrate Oracle schema to ScalarDB"},
        {"label": "MySQL", "description": "Migrate MySQL schema to ScalarDB"},
        {"label": "PostgreSQL", "description": "Migrate PostgreSQL schema to ScalarDB"}
      ],
      "multiSelect": false
    }
  ]
}
```

Save the user's response.

---

### STEP 2: Delegate to the Database-Specific Skill

Based on the user's selection, invoke the corresponding skill using the `Skill` tool:

| User Selection | Skill to Invoke |
|----------------|-----------------|
| **Oracle** | `Skill: architect:migrate-oracle` |
| **MySQL** | `Skill: architect:migrate-mysql` |
| **PostgreSQL** | `Skill: architect:migrate-postgresql` |

The delegated command handles the entire workflow autonomously:

**Phase A: Interactive Configuration (Steps 1-6) — Main Context**
1. Reads or detects missing `.claude/configuration/databases.env`
2. Collects connection parameters (Batch 1 of 2) via `AskUserQuestion`
3. Collects authentication & options (Batch 2 of 2) via `AskUserQuestion`
4. Maps user responses to configuration values
5. Writes or updates `databases.env`
6. Ensures output directory exists

**Phase B: Subagent Processing — Isolated Contexts**

*Oracle (Steps 7-11 — 6 subagents):*

| Step | Subagent | Type | What It Does |
|------|----------|------|--------------|
| 7 | Connection Tester | Bash | Verifies DB is reachable via SQL*Plus |
| 8 | Schema Extractor | Bash | Runs `oracle_db_extractor.py` |
| 9 | Report Generator | general-purpose | Reads JSON + template, writes schema report |
| 10 | Migration Analyst + AQ Migrator + SP/Trigger Migrator | general-purpose ×3 | Parallel: migration docs + AQ Java code + SP/trigger Java code |
| 11 | *(main context)* | — | Displays combined summary + metrics table |

*MySQL / PostgreSQL (Steps 7-11 — 5 subagents):*

| Step | Subagent | Type | What It Does |
|------|----------|------|--------------|
| 7 | Connection Tester | Bash | Verifies DB is reachable via Python connector |
| 8 | Schema Extractor | Bash | Runs `*_db_extractor.py` |
| 9 | Report Generator | general-purpose | Reads JSON + template, writes schema report |
| 10 | Migration Analyst + SP Migrator | general-purpose x2 | Parallel: migration docs + Java code |
| 11 | *(main context)* | — | Displays combined summary |

Error cascading applies: if any subagent fails, later subagents are not spawned.

Do NOT perform any additional steps after invoking the skill — the delegated command produces the final output.

---

### STEP 3: Error Handling

- **User selects "Other" with an unrecognized database type:**
  Inform the user: "Currently, only Oracle, MySQL, and PostgreSQL are supported for ScalarDB migration. Please choose one of the three supported databases."
  Then re-ask the question from Step 1.

- **User cancels or does not respond:**
  Stop execution and inform the user they can restart with `/architect:migrate-database` or use a direct command (`/architect:migrate-oracle`, `/architect:migrate-mysql`, `/architect:migrate-postgresql`).

---

## Related Commands

| Command | Description |
|---------|-------------|
| `/architect:migrate-oracle` | Direct Oracle migration (skips database selection) |
| `/architect:migrate-mysql` | Direct MySQL migration (skips database selection) |
| `/architect:migrate-postgresql` | Direct PostgreSQL migration (skips database selection) |

## Related Files

- **Config**: `.claude/configuration/databases.env`
- **Output**: `.claude/output/` (generated reports)
- **Subagent Prompts**: `${CLAUDE_PLUGIN_ROOT}/skills/common/subagents/{oracle,mysql,postgresql}/`
