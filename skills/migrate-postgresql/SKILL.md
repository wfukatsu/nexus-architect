---
name: migrate-postgresql
description: |
  PostgreSQL to ScalarDB migration. Schema extraction, migration analysis,
  and SP/trigger to Java conversion. /architect:migrate-postgresql to start.
model: sonnet
user_invocable: true
---

Orchestrates the complete PostgreSQL to ScalarDB migration workflow through an interactive chat interface. Collects database connection parameters from the user via questions, updates the configuration file, then runs the analysis and migration skills.

---

## Execution Instructions

You MUST follow these steps exactly in order. Do NOT skip any step.

---

### STEP 0: Discover Plugin Installation Directory (PLUGIN_ROOT)

Run the following Bash command to get the plugin installation directory:

```bash
echo "$CLAUDE_PLUGIN_ROOT"
```

- If the output is a **non-empty path**, set `PLUGIN_ROOT` to that value.
- If the output is **empty**, run this fallback to locate it:

```bash
find ~/.claude/plugins -name "plugin.json" -path "*/scalardb-migration/*" 2>/dev/null | head -1 | xargs -I{} dirname {} | xargs -I{} dirname {}
```

Store the result as `PLUGIN_ROOT`. All subagent template paths in Steps 7–11 use this variable (e.g., `PLUGIN_ROOT/subagents/postgresql/0-test-connection.md`).

---

### STEP 1: Read Current Configuration (or Detect First Run)

First, attempt to read the current configuration file:

```
Read file: .claude/configuration/databases.env
```

**Two possible outcomes:**

**A) File EXISTS** → Set `CONFIG_EXISTS = true`
- Note down the current PostgreSQL values (POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_SCHEMA, POSTGRES_INCLUDE_PLPGSQL_SOURCE, OUTPUT_DIR)
- These will be shown in "Keep current" option descriptions

**B) File DOES NOT EXIST** → Set `CONFIG_EXISTS = false`
- Inform the user: "No existing configuration found. This appears to be a first-time setup — I'll collect all connection parameters from you."
- Ensure the configuration directory exists using Bash: `mkdir -p .claude/configuration`
- All parameters will need to be collected fresh (no "Keep current" option available)

---

### STEP 2: Collect Connection Parameters (Batch 1 of 2)

Build the questions based on CONFIG_EXISTS:

**If CONFIG_EXISTS = true:** Include "Keep current" options with actual values in descriptions (e.g., `"Keep current"` with description `"Keep: localhost"`).

**If CONFIG_EXISTS = false:** Replace "Keep current" options with additional useful defaults instead. Do NOT offer "Keep current" since there is nothing to keep.

Use the `AskUserQuestion` tool:

```json
{
  "questions": [
    {
      "question": "What is the PostgreSQL database host?",
      "header": "Host",
      "options": [
        {"label": "localhost", "description": "Database running on local machine"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_POSTGRES_HOST>"}
                      : {"label": "127.0.0.1", "description": "Loopback IP address"}
      ],
      "multiSelect": false
    },
    {
      "question": "What is the PostgreSQL port?",
      "header": "Port",
      "options": [
        {"label": "5432 (Default)", "description": "Standard PostgreSQL port"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_POSTGRES_PORT>"}
                      : {"label": "5433", "description": "Alternative PostgreSQL port"}
      ],
      "multiSelect": false
    },
    {
      "question": "What is the PostgreSQL database name to analyze?",
      "header": "Database",
      "options": [
        {"label": "postgres", "description": "Default PostgreSQL database"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_POSTGRES_DATABASE>"}
                      : {"label": "template1", "description": "PostgreSQL template database"}
      ],
      "multiSelect": false
    },
    {
      "question": "What is the PostgreSQL username?",
      "header": "Username",
      "options": [
        {"label": "postgres", "description": "Default PostgreSQL superuser"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_POSTGRES_USER>"}
                      : {"label": "admin", "description": "Common admin username"}
      ],
      "multiSelect": false
    }
  ]
}
```

**Note:** The pseudo-code `CONFIG_EXISTS ? ... : ...` means you must construct the actual JSON dynamically based on whether the config file existed. Replace `<CURRENT_*>` placeholders with actual values read from the file.

Save all responses. For "Keep current" responses, use the existing values from the config file. For "Other" responses, use the custom text the user typed.

---

### STEP 3: Collect Authentication & Options (Batch 2 of 2)

Use the `AskUserQuestion` tool, again adapting based on CONFIG_EXISTS:

```json
{
  "questions": [
    {
      "question": "What is the database password? (Select 'Other' to type your password)",
      "header": "Password",
      "options": [
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Use the password already in config"}
                      : {"label": "No password", "description": "Connect without a password (empty)"},
        CONFIG_EXISTS ? {"label": "No password", "description": "Connect without a password (empty)"}
                      : {"label": "Type below", "description": "Select 'Other' to enter your password"}
      ],
      "multiSelect": false
    },
    {
      "question": "Which PostgreSQL schema to analyze?",
      "header": "Schema",
      "options": [
        {"label": "public (Default)", "description": "Default PostgreSQL schema"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_POSTGRES_SCHEMA or '(empty)'>"}
                      : {"label": "pg_catalog", "description": "PostgreSQL system catalog schema"}
      ],
      "multiSelect": false
    },
    {
      "question": "Include PL/pgSQL function and procedure source code in the report?",
      "header": "PL/pgSQL",
      "options": [
        {"label": "Yes (Recommended)", "description": "Include PL/pgSQL source code for migration analysis"},
        {"label": "No", "description": "Skip source code - faster analysis, smaller report"}
      ],
      "multiSelect": false
    },
    {
      "question": "Where should output files be saved? (Must be an absolute path)",
      "header": "Output Dir",
      "options": [
        {"label": "Default (.claude/output)", "description": "Use the project's .claude/output directory"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_OUTPUT_DIR>"}
                      : {"label": "Custom path", "description": "Select 'Other' to type a custom absolute path"}
      ],
      "multiSelect": false
    }
  ]
}
```

Save all responses.

---

### STEP 4: Map Responses to Configuration Values

Process the collected answers into configuration values using these rules:

| Parameter | Response Mapping |
|-----------|-----------------|
| **POSTGRES_HOST** | "localhost" -> `localhost`, "127.0.0.1" -> `127.0.0.1`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **POSTGRES_PORT** | "5432 (Default)" -> `5432`, "5433" -> `5433`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **POSTGRES_DATABASE** | "postgres" -> `postgres`, "template1" -> `template1`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **POSTGRES_USER** | "postgres" -> `postgres`, "admin" -> `admin`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **POSTGRES_PASSWORD** | "Keep current" -> keep existing, "No password" -> empty string, "Type below" -> user must use "Other", "Other" -> user's typed value |
| **POSTGRES_SCHEMA** | "public (Default)" -> `public`, "pg_catalog" -> `pg_catalog`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **POSTGRES_INCLUDE_PLPGSQL_SOURCE** | "Yes (Recommended)" -> `true`, "No" -> `false` |
| **OUTPUT_DIR** | "Default (.claude/output)" -> absolute path to project's `.claude/output` directory, "Keep current" -> keep existing, "Custom path" -> user must use "Other", "Other" -> user's typed value |

Also set: `ACTIVE_DATABASE=postgresql`

---

### STEP 5: Write or Update Configuration File

**If CONFIG_EXISTS = false (first run):**

Use the **Write** tool to create `.claude/configuration/databases.env` with the complete template populated with collected values:

```properties
# =============================================================================
# CONSOLIDATED DATABASE CONFIGURATION
# =============================================================================
# Single configuration file for all database migration skills
# =============================================================================

# ACTIVE DATABASE SELECTION
ACTIVE_DATABASE=postgresql

# SHARED OUTPUT CONFIGURATION (ABSOLUTE PATH REQUIRED)
OUTPUT_DIR=<collected_output_dir>

# ScalarDB target version
SCALARDB_TARGET_VERSION=3.17

# =============================================================================
# POSTGRESQL CONFIGURATION
# =============================================================================
POSTGRES_HOST=<collected_host>
POSTGRES_PORT=<collected_port>
POSTGRES_DATABASE=<collected_database>
POSTGRES_USER=<collected_user>
POSTGRES_PASSWORD=<collected_password>
POSTGRES_SCHEMA=<collected_schema>
POSTGRES_REPORT_FILENAME=postgresql_schema_report.md
POSTGRES_SCALARDB_NAMESPACE=<lowercase of collected_database or collected_schema>
POSTGRES_INCLUDE_PLPGSQL_SOURCE=<collected_plpgsql_source>
POSTGRES_PSQL_PATH=
POSTGRES_CONNECTION_TIMEOUT=30
POSTGRES_QUERY_TIMEOUT=300

# =============================================================================
# MYSQL CONFIGURATION (defaults - not yet configured)
# =============================================================================
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=your_database
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_REPORT_FILENAME=mysql_schema_report.md
MYSQL_SCALARDB_NAMESPACE=
MYSQL_INCLUDE_SOURCE=false
MYSQL_CHARSET=utf8mb4
MYSQL_CONNECTION_TIMEOUT=30

# =============================================================================
# ORACLE CONFIGURATION (defaults - not yet configured)
# =============================================================================
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE=ORCL
ORACLE_USER=your_username
ORACLE_PASSWORD=your_password
ORACLE_SCHEMA=
ORACLE_REPORT_FILENAME=oracle_schema_report.md
ORACLE_SCALARDB_NAMESPACE=
ORACLE_INCLUDE_PLSQL_SOURCE=false
ORACLE_SQLPLUS_PATH=
ORACLE_HOME=
ORACLE_TNS_ADMIN=

# =============================================================================
# END OF CONFIGURATION
# =============================================================================
```

**If CONFIG_EXISTS = true (updating existing):**

Use the **Edit** tool to update `.claude/configuration/databases.env` with the collected values:

1. Set `ACTIVE_DATABASE=postgresql`
2. Update `OUTPUT_DIR` if changed
3. Update all `POSTGRES_*` parameters with the mapped values from Step 4
4. Do NOT modify the MySQL or Oracle sections

**After writing/updating, display a confirmation summary to the user:**

```
Configuration <Created / Updated>:
  Host:      <value>
  Port:      <value>
  Database:  <value>
  User:      <value>
  Password:  ******** (hidden)
  Schema:    <value>
  PL/pgSQL:  <true/false>
  Output:    <path>
```

---

### STEP 6: Ensure Output Directory Exists

Use Bash to create the output directory if it doesn't exist:

```bash
mkdir -p <OUTPUT_DIR>
```

---

### STEP 7: Subagent 0 — Connection Test via API (Bash)

Spawn a **Bash** subagent using the `Task` tool to test the PostgreSQL database connection via the external API.

1. Read the prompt template at: `${CLAUDE_PLUGIN_ROOT}/subagents/postgresql/0-test-connection.md`
2. Substitute the runtime variables: replace `<POSTGRES_HOST>`, `<POSTGRES_PORT>`, `<POSTGRES_DATABASE>`, `<POSTGRES_USER>`, `<POSTGRES_PASSWORD>`, and `<OUTPUT_DIR>` with the actual values from Steps 4-5
3. Call the Task tool with `subagent_type: "Bash"`, `description: "Test PostgreSQL connection"`, and the substituted prompt

**After the subagent completes:**
- Extract `DURATION_SECONDS` from the subagent's response → store as `S0_DURATION`
- Extract `total_tokens` from the `<usage>` block in the Task result (if present) → store as `S0_TOKENS`

**Check the subagent result:**
- If STATUS is **FAILURE** → Display the error to the user with resolution hints (check host/port/database name, verify credentials, check `pg_hba.conf` allows connections, ensure PostgreSQL server is running). **STOP HERE — do NOT proceed to Step 8, 9, or 10.**
- If STATUS is **SUCCESS** → Note the database product and version, then proceed to Step 8.

---

### STEP 8: Subagent 1 — Schema Extraction (Bash)

Spawn a **Bash** subagent using the `Task` tool to run the Python extractor script.

1. Read the prompt template at: `${CLAUDE_PLUGIN_ROOT}/subagents/postgresql/1-extract-schema.md`
2. Substitute the runtime variables as documented in the template (replace `<INCLUDE_SOURCE_FLAG>` based on POSTGRES_INCLUDE_PLPGSQL_SOURCE from Step 4)
3. Call the Task tool with `subagent_type: "Bash"`, `description: "Extract PostgreSQL schema"`, and the substituted prompt

**After the subagent completes:**
- Extract `DURATION_SECONDS` from the subagent's response → store as `S1_DURATION`
- Extract `total_tokens` from the `<usage>` block in the Task result (if present) → store as `S1_TOKENS`

**Check the subagent result:**
- If STATUS is **FAILURE** → Display the error to the user with resolution hints (check host/port, verify credentials, ensure PostgreSQL server is running). **STOP HERE — do NOT proceed to Step 9 or Step 10.**
- If STATUS is **SUCCESS** → Note the OUTPUT_FILE path and proceed to Step 9.

---

### STEP 9: Subagent 2 — Schema Report Generation (general-purpose)

Spawn a **general-purpose** subagent using the `Task` tool to generate the schema report from the extracted JSON.

1. Read the prompt template at: `${CLAUDE_PLUGIN_ROOT}/subagents/postgresql/2-generate-report.md`
2. Substitute the runtime variables as documented in the template (replace all `<OUTPUT_DIR>` with the actual absolute output directory path from Step 4)
3. Call the Task tool with `subagent_type: "general-purpose"`, `description: "Generate PostgreSQL schema report"`, and the substituted prompt

**After the subagent completes:**
- Extract `DURATION_SECONDS` from the subagent's response → store as `S2_DURATION`
- Extract `total_tokens` from the `<usage>` block in the Task result (if present) → store as `S2_TOKENS`

**Check the subagent result:**
- If STATUS is **FAILURE** → Display the error to the user. Note that `raw_schema_data.json` is still available for manual inspection. **STOP HERE — do NOT proceed to Step 10.**
- If STATUS is **SUCCESS** → Note the summary and proceed to Step 10.

---

### STEP 10: Subagents 3 & 4 — Migration Analysis + SP & Trigger Migration (Parallel)

**Both subagents run simultaneously** in a single message — send both `Task` tool calls together in one response. They share the same inputs (`postgresql_schema_report.md` and `raw_schema_data.json`) and have no dependency on each other's output.

**Preparation:**
1. Read the prompt template at: `${CLAUDE_PLUGIN_ROOT}/subagents/postgresql/3-migration-analysis.md`
   - Substitute all `<OUTPUT_DIR>` with the actual absolute output directory path from Step 4
2. Read the prompt template at: `${CLAUDE_PLUGIN_ROOT}/subagents/postgresql/4-sp-trigger-migration.md`
   - Substitute all `<OUTPUT_DIR>` with the actual absolute output directory path from Step 4

**Spawn both in one message:**
- Task call A: `subagent_type: "general-purpose"`, `description: "Generate PostgreSQL migration docs"`, substituted prompt from `3-migration-analysis.md`
- Task call B: `subagent_type: "general-purpose"`, `description: "Generate SP & trigger migration code"`, substituted prompt from `4-sp-trigger-migration.md`

**After both subagents complete:**
- From Subagent 3 result: extract `DURATION_SECONDS` → store as `S3_DURATION`; extract `total_tokens` from `<usage>` block → store as `S3_TOKENS`
- From Subagent 4 result: extract `DURATION_SECONDS` → store as `S4_DURATION`; extract `total_tokens` from `<usage>` block → store as `S4_TOKENS`
- Compute parallel wall-clock: `S34_WALL = max(S3_DURATION, S4_DURATION)`

**Error cascading rules:**
- Subagent 2 (Step 9) **failed** → **do NOT spawn either Subagent 3 or 4** (both need postgresql_schema_report.md)
- Subagent 3 **fails** while Subagent 4 **succeeds** → capture both results, report Subagent 3 error, proceed with Subagent 4 output
- Subagent 4 **fails** while Subagent 3 **succeeds** → capture both results, report Subagent 4 error, proceed with Subagent 3 output
- Both fail → display both errors; all prior outputs (schema report, raw JSON) remain on disk

**Check results and proceed to Step 11.**

---

### STEP 11: Display Final Summary with Metrics

Display the combined results from all five subagents, then a timing and token usage table.

**Compute totals before rendering:**
- `TOTAL_DURATION = S0_DURATION + S1_DURATION + S2_DURATION + S34_WALL`
  *(Phases 3 & 4 ran in parallel, so only the longer one adds to wall-clock time)*
- `TOTAL_TOKENS = S0_TOKENS + S1_TOKENS + S2_TOKENS + S3_TOKENS + S4_TOKENS`
  *(If any token value is unavailable, mark it as "N/A" and omit it from the total)*

Display to the user:

```
PostgreSQL to ScalarDB Migration — Complete

Phase 0: Connection Test
  - API endpoint: https://test2.jeeni.in/database/test-postgres-connection
  - <Subagent 0 SUMMARY line (database product and version)>

Phase 1: Schema Extraction
  - Connected to PostgreSQL at <host>:<port>/<database>
  - <Subagent 1 SUMMARY line>

Phase 2: Schema Report
  - Generated: postgresql_schema_report.md
  - <Subagent 2 SUMMARY lines>

Phase 3 + 4 (Parallel):
  Migration Analysis:
    - Generated: scalardb_migration_analysis.md
    - Generated: scalardb_migration_steps.md
    - Migration Complexity: <Subagent 3 COMPLEXITY_SCORE>
    - <Subagent 3 SUMMARY lines>
  SP & Trigger Migration:
    - Generated: scalardb_sp_migration_report.md
    - Java files: <OUTPUT_DIR>/generated-java/
    - Files generated: <Subagent 4 FILES_GENERATED>
    - <Subagent 4 SUMMARY lines>

Output Directory: <OUTPUT_DIR>

Next Steps:
  1. Review scalardb_migration_analysis.md for compatibility details
  2. Follow scalardb_migration_steps.md for implementation guide
  3. Review generated-java/ for migrated stored procedure code
  4. Review scalardb_sp_migration_report.md for SP & trigger migration details
```

Then display the metrics table:

```
Execution Summary
─────────────────────────────────────────────────────────────────────
 Phase                          │ Subagent Type    │ Tokens  │ Time
─────────────────────────────────────────────────────────────────────
 Phase 0: Connection Test       │ Bash             │ S0_TOK  │ S0s
 Phase 1: Schema Extraction     │ Bash             │ S1_TOK  │ S1s
 Phase 2: Schema Report         │ General-purpose  │ S2_TOK  │ S2s
 Phase 3: Migration Analysis  ┐ │ General-purpose  │ S3_TOK  │ S3s
 Phase 4: SP/Trigger Migration┘ │ General-purpose  │ S4_TOK  │ S4s
               (parallel wall-clock)                       │ S34s
─────────────────────────────────────────────────────────────────────
 TOTAL                          │ 5 subagents      │ TOT_TOK │ TOTs
─────────────────────────────────────────────────────────────────────
Note: Phases 3 & 4 ran in parallel. Total time reflects wall-clock
      (sequential sum of Phases 0–2 plus the longer of Phases 3/4).
      Token counts extracted from <usage> blocks; N/A if unavailable.
```

---

## Error Handling

- If AskUserQuestion fails or user cancels → stop execution and inform the user
- If configuration write/update fails → show error and do not proceed to subagents
- If **Subagent 0 fails** (API connection test error) → show error with resolution hints (check host/port/database, verify credentials, check `pg_hba.conf`, ensure PostgreSQL server is running), **STOP** (do not spawn Subagent 1, 2, 3, or 4)
- If **Subagent 1 fails** (DB connection/extraction error) → show error with resolution hints, **STOP** (do not spawn Subagent 2, 3, or 4)
- If **Subagent 2 fails** (report generation error) → show error, note that `raw_schema_data.json` is available on disk, **STOP** (do not spawn Subagent 3 or 4 — both need postgresql_schema_report.md)
- If **both Subagents 3 & 4 were spawned in parallel** and one or both fail:
  - Subagent 3 fails, Subagent 4 succeeds → report Subagent 3 error; display Subagent 4 output in summary
  - Subagent 4 fails, Subagent 3 succeeds → report Subagent 4 error; display Subagent 3 output in summary
  - Both fail → report both errors; note that schema report and raw JSON remain on disk
- Always include collected timing and token data in the Step 11 metrics table, even for partial runs (mark failed subagents as "FAILED" in the table)

Partial outputs are always preserved — if extraction succeeds but later steps fail, earlier output files remain on disk for manual inspection.

---

## Subagent Architecture

This command uses **5 subagents** — 3 sequential then 2 in parallel — to isolate heavy processing from the main conversation:

```
Step 7  ──► Subagent 0 (Bash)             Connection Test
Step 8  ──► Subagent 1 (Bash)             Schema Extraction
Step 9  ──► Subagent 2 (General-purpose)  Schema Report
              │
Step 10 ──► ─┼─► Subagent 3 (General-purpose)  Migration Analysis  ─┐
              └─► Subagent 4 (General-purpose)  SP & Trigger Migration ─┤ (parallel)
                                                                       │
Step 11 ◄──────────────────────────────────────────────────────────── ┘
        Display final summary + metrics table
```

| Subagent | Step | Type | Purpose | Returns |
|----------|------|------|---------|---------|
| 0 | 7 | Bash | POST to `test-postgres-connection` API to verify DB is reachable | SUCCESS/FAILURE + DB version + DURATION_SECONDS |
| 1 | 8 | Bash | Run `postgresql_db_extractor.py` | SUCCESS/FAILURE + file path + DURATION_SECONDS |
| 2 | 9 | General-purpose | Generate `postgresql_schema_report.md` from JSON + template | Executive summary + DURATION_SECONDS |
| 3 | 10 ┐ | General-purpose | Generate migration analysis + steps from schema report + reference docs | Complexity score + findings + DURATION_SECONDS |
| 4 | 10 ┘ | General-purpose | Generate Java code from PL/pgSQL + SP & trigger migration report | Files generated + complexity + DURATION_SECONDS |

**Parallelism:** Subagents 3 and 4 are spawned simultaneously in Step 10 (single message, two Task calls). Both read from `postgresql_schema_report.md` and `raw_schema_data.json`; neither depends on the other.

**Metrics tracking:** After each Task call, extract `total_tokens` and `duration_ms` from the `<usage>` block in the result, and `DURATION_SECONDS` from the subagent's self-reported output. Use these to populate the Step 11 summary table.

The SKILL.md files are **read directly by subagents** as instruction documents (the Skill tool is not invoked).

---

## Related Files

- **Subagent Prompts**: `${CLAUDE_PLUGIN_ROOT}/subagents/postgresql/` (5 prompt templates)
- **Analysis Skill**: `${CLAUDE_PLUGIN_ROOT}/skills/analyze-postgresql-schema/SKILL.md`
- **Report Template**: `${CLAUDE_PLUGIN_ROOT}/skills/analyze-postgresql-schema/analyze-postgresql-dbms_report.md`
- **Extractor Script**: `${CLAUDE_PLUGIN_ROOT}/skills/analyze-postgresql-schema/scripts/postgresql_db_extractor.py`
- **Migration Skill**: `${CLAUDE_PLUGIN_ROOT}/skills/migrate-postgresql-to-scalardb/SKILL.md`
- **Migration Templates**: `${CLAUDE_PLUGIN_ROOT}/skills/migrate-postgresql-to-scalardb/templates/`
- **ScalarDB Reference**: `${CLAUDE_PLUGIN_ROOT}/skills/migrate-postgresql-to-scalardb/reference/scalardb_reference.md`
- **SP & Trigger Migration Skill**: `${CLAUDE_PLUGIN_ROOT}/skills/migrate-postgresql-sp-trigger-to-scalardb/SKILL.md`
- **SP & Trigger Migration Reference**: `${CLAUDE_PLUGIN_ROOT}/skills/migrate-postgresql-sp-trigger-to-scalardb/reference/migration-strategy-guide-sp-triggers-to-scalardb.md`
- **SP & Trigger Migration Template**: `${CLAUDE_PLUGIN_ROOT}/skills/migrate-postgresql-sp-trigger-to-scalardb/templates/scalardb_sp_migration_report.md`
- **Config**: `.claude/configuration/databases.env`
