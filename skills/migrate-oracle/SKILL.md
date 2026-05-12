---
description: |
  Oracle to ScalarDB migration. Schema extraction, migration analysis, AQ integration,
  and SP/trigger to Java conversion. /architect:migrate-oracle to start.
model: sonnet
user_invocable: true
---

Orchestrates the complete Oracle to ScalarDB migration workflow through an interactive chat interface. Collects database connection parameters from the user via questions, updates the configuration file, then runs the analysis and migration skills.

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
find ~/.claude/plugins -name "plugin.json" -path "*/architect/*" 2>/dev/null | head -1 | xargs -I{} dirname {} | xargs -I{} dirname {}
```

Store the result as `PLUGIN_ROOT`. All subagent template paths in Steps 7–12 use this variable (e.g., `PLUGIN_ROOT/skills/common/subagents/oracle/0-test-connection.md`).

---

### STEP 1: Read Current Configuration (or Detect First Run)

First, attempt to read the current configuration file:

```
Read file: .claude/configuration/databases.env
```

**Two possible outcomes:**

**A) File EXISTS** → Set `CONFIG_EXISTS = true`
- Note down the current Oracle values (ORACLE_HOST, ORACLE_PORT, ORACLE_SERVICE, ORACLE_USER, ORACLE_PASSWORD, ORACLE_SCHEMA, OUTPUT_DIR, ORACLE_INCLUDE_PLSQL_SOURCE)
- These will be shown in "Keep current" option descriptions

**B) File DOES NOT EXIST** → Set `CONFIG_EXISTS = false`
- Inform the user: "No existing configuration found. This appears to be a first-time setup — I'll collect all connection parameters from you."
- Ensure the configuration directory exists using Bash: `mkdir -p .claude/configuration`
- All parameters will need to be collected fresh (no "Keep current" option available)

---

### STEP 2: Collect Connection Parameters (Batch 1 of 2)

Build the questions based on CONFIG_EXISTS:

**If CONFIG_EXISTS = true:** Include "Keep current" options with actual values in descriptions (e.g., `"Keep current"` with description `"Keep: 98.130.78.220"`).

**If CONFIG_EXISTS = false:** Replace "Keep current" options with additional useful defaults instead. Do NOT offer "Keep current" since there is nothing to keep.

Use the `AskUserQuestion` tool:

```json
{
  "questions": [
    {
      "question": "What is the Oracle database host?",
      "header": "Host",
      "options": [
        {"label": "localhost", "description": "Database running on local machine"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_ORACLE_HOST>"}
                      : {"label": "127.0.0.1", "description": "Loopback IP address"}
      ],
      "multiSelect": false
    },
    {
      "question": "What is the Oracle listener port?",
      "header": "Port",
      "options": [
        {"label": "1521 (Default)", "description": "Standard Oracle listener port"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_ORACLE_PORT>"}
                      : {"label": "1522", "description": "Alternative Oracle port"}
      ],
      "multiSelect": false
    },
    {
      "question": "What is the Oracle service name or SID?",
      "header": "Service",
      "options": [
        {"label": "ORCL", "description": "Default Oracle service name"},
        {"label": "FREEPDB1", "description": "Oracle Free/XE pluggable database"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_ORACLE_SERVICE>"}
                      : {"label": "XE", "description": "Oracle Express Edition"}
      ],
      "multiSelect": false
    },
    {
      "question": "What is the Oracle database username?",
      "header": "Username",
      "options": [
        {"label": "HR", "description": "Human Resources sample schema"},
        {"label": "SYSTEM", "description": "Oracle system administrator"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_ORACLE_USER>"}
                      : {"label": "ADMIN", "description": "Common admin username"}
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
      "question": "Which Oracle schema to analyze? (Leave empty for connected user's default schema)",
      "header": "Schema",
      "options": [
        {"label": "Use default", "description": "Use connected user's own schema (leave ORACLE_SCHEMA empty)"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_ORACLE_SCHEMA or '(empty)'>"}
                      : {"label": "HR", "description": "Human Resources sample schema"}
      ],
      "multiSelect": false
    },
    {
      "question": "Include PL/SQL source code in the analysis report?",
      "header": "PL/SQL",
      "options": [
        {"label": "No (Recommended)", "description": "Skip PL/SQL source code - faster, smaller report"},
        {"label": "Yes", "description": "Include full PL/SQL source code in the report"}
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
| **ORACLE_HOST** | "localhost" -> `localhost`, "127.0.0.1" -> `127.0.0.1`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **ORACLE_PORT** | "1521 (Default)" -> `1521`, "1522" -> `1522`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **ORACLE_SERVICE** | "ORCL" -> `ORCL`, "FREEPDB1" -> `FREEPDB1`, "XE" -> `XE`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **ORACLE_USER** | "HR" -> `HR`, "SYSTEM" -> `SYSTEM`, "ADMIN" -> `ADMIN`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **ORACLE_PASSWORD** | "Keep current" -> keep existing, "No password" -> empty string, "Type below" -> user must use "Other", "Other" -> user's typed value |
| **ORACLE_SCHEMA** | "Use default" -> empty string, "HR" -> `HR`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **ORACLE_INCLUDE_PLSQL_SOURCE** | "No (Recommended)" -> `false`, "Yes" -> `true` |
| **OUTPUT_DIR** | "Default (.claude/output)" -> absolute path to project's `.claude/output` directory, "Keep current" -> keep existing, "Custom path" -> user must use "Other", "Other" -> user's typed value |

Also set: `ACTIVE_DATABASE=oracle`

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
ACTIVE_DATABASE=oracle

# SHARED OUTPUT CONFIGURATION (ABSOLUTE PATH REQUIRED)
OUTPUT_DIR=<collected_output_dir>

# ScalarDB target version
SCALARDB_TARGET_VERSION=3.17

# =============================================================================
# POSTGRESQL CONFIGURATION (defaults - not yet configured)
# =============================================================================
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=your_database
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_SCHEMA=public
POSTGRES_REPORT_FILENAME=postgresql_schema_report.md
POSTGRES_SCALARDB_NAMESPACE=
POSTGRES_INCLUDE_PLPGSQL_SOURCE=true
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
# ORACLE CONFIGURATION
# =============================================================================
ORACLE_HOST=<collected_host>
ORACLE_PORT=<collected_port>
ORACLE_SERVICE=<collected_service>
ORACLE_USER=<collected_user>
ORACLE_PASSWORD=<collected_password>
ORACLE_SCHEMA=<collected_schema>
ORACLE_REPORT_FILENAME=oracle_schema_report.md
ORACLE_SCALARDB_NAMESPACE=<lowercase of collected_user or collected_schema>
ORACLE_INCLUDE_PLSQL_SOURCE=<collected_plsql_source>
ORACLE_SQLPLUS_PATH=
ORACLE_HOME=
ORACLE_TNS_ADMIN=

# =============================================================================
# END OF CONFIGURATION
# =============================================================================
```

**If CONFIG_EXISTS = true (updating existing):**

Use the **Edit** tool to update `.claude/configuration/databases.env` with the collected values:

1. Set `ACTIVE_DATABASE=oracle`
2. Update `OUTPUT_DIR` if changed
3. Update all `ORACLE_*` parameters with the mapped values from Step 4
4. Do NOT modify the PostgreSQL or MySQL sections

**After writing/updating, display a confirmation summary to the user:**

```
Configuration <Created / Updated>:
  Host:     <value>
  Port:     <value>
  Service:  <value>
  User:     <value>
  Password: ******** (hidden)
  Schema:   <value or "default (connected user)">
  PL/SQL:   <true/false>
  Output:   <path>
```

---

### STEP 6: Ensure Output Directory Exists

Use Bash to create the output directory if it doesn't exist:

```bash
mkdir -p <OUTPUT_DIR>
```

---

### STEP 7: Subagent 0 — Connection Test via SQL*Plus (Bash)

Spawn a **Bash** subagent using the `Task` tool to test the database connection directly using SQL*Plus before running the heavy extraction process.

1. Read the prompt template at: `${PLUGIN_ROOT}/skills/common/subagents/oracle/0-test-connection.md`
2. Substitute the runtime variables with values from Steps 1-4:
   - `<ORACLE_HOST>` → the collected ORACLE_HOST value
   - `<ORACLE_PORT>` → the collected ORACLE_PORT value
   - `<ORACLE_SERVICE>` → the collected ORACLE_SERVICE value
   - `<ORACLE_USER>` → the collected ORACLE_USER value
   - `<ORACLE_PASSWORD>` → the collected ORACLE_PASSWORD value
   - `<ORACLE_SQLPLUS_PATH>` → the collected ORACLE_SQLPLUS_PATH value (empty string if not set)
   - `<OUTPUT_DIR>` → the collected OUTPUT_DIR value
3. Call the Task tool with `subagent_type: "Bash"`, `description: "Test Oracle DB connection"`, and the substituted prompt

**Check the subagent result:**
- Extract `DURATION_SECONDS` from the subagent's response → store as `S0_DURATION`
- Extract `total_tokens` from the `<usage>` block in the Task result (if present) → store as `S0_TOKENS`
- If STATUS is **SUCCESS** → Display the Oracle version banner to the user. Proceed to Step 8.
- If STATUS is **FAILURE** → Display the error message with the appropriate resolution hint and **STOP HERE — do NOT proceed to Step 8 or any later step.**
  - `ORA-12541` → Oracle listener not running or wrong host/port
  - `ORA-12514` → Wrong service name or SID
  - `ORA-01017` → Wrong username or password
  - `SQL*Plus not found` → SQL*Plus is not installed or ORACLE_SQLPLUS_PATH is not set in `.claude/configuration/databases.env`

---

### STEP 8: Subagent 1 — Schema Extraction (Bash)

Spawn a **Bash** subagent using the `Task` tool to run the Python extractor script.

1. Read the prompt template at: `${PLUGIN_ROOT}/skills/common/subagents/oracle/1-extract-schema.md`
2. Substitute the runtime variables as documented in the template (replace `<INCLUDE_SOURCE_FLAG>` based on ORACLE_INCLUDE_PLSQL_SOURCE from Step 4)
3. Call the Task tool with `subagent_type: "Bash"`, `description: "Extract Oracle schema"`, and the substituted prompt

**Check the subagent result:**
- Extract `DURATION_SECONDS` from the subagent's response → store as `S1_DURATION`
- Extract `total_tokens` from the `<usage>` block in the Task result (if present) → store as `S1_TOKENS`
- If STATUS is **FAILURE** → Display the error to the user with resolution hints (check host/port/service, verify credentials, ensure Oracle listener is running). **STOP HERE — do NOT proceed to Step 9 or Step 10.**
- If STATUS is **SUCCESS** → Note the OUTPUT_FILE path and proceed to Step 9.

---

### STEP 9: Subagent 2 — Schema Report Generation (general-purpose)

Spawn a **general-purpose** subagent using the `Task` tool to generate the schema report from the extracted JSON.

1. Read the prompt template at: `${PLUGIN_ROOT}/skills/common/subagents/oracle/2-generate-report.md`
2. Substitute the runtime variables as documented in the template (replace all `<OUTPUT_DIR>` with the actual absolute output directory path from Step 4)
3. Call the Task tool with `subagent_type: "general-purpose"`, `description: "Generate Oracle schema report"`, and the substituted prompt

**Check the subagent result:**
- Extract `DURATION_SECONDS` from the subagent's response → store as `S2_DURATION`
- Extract `total_tokens` from the `<usage>` block in the Task result (if present) → store as `S2_TOKENS`
- If STATUS is **FAILURE** → Display the error to the user. Note that `raw_schema_data.json` is still available for manual inspection. **STOP HERE — do NOT proceed to Step 10.**
- If STATUS is **SUCCESS** → Note the summary and proceed to Step 10.

---

### STEP 10: Subagents 3, 4, 5 — Parallel Execution (general-purpose × 3)

Subagents 3, 4, and 5 all depend only on the outputs of Subagent 2 (`oracle_schema_report.md` + `raw_schema_data.json`). They have no dependencies on each other, so spawn all three **in a single message** to run in parallel.

Record `S345_START` = current time.

**In one message**, issue all three Task() calls simultaneously:

**Task A — Subagent 3: Migration Analysis**

1. Read the prompt template at: `${PLUGIN_ROOT}/skills/common/subagents/oracle/3-migration-analysis.md`
2. Substitute all `<OUTPUT_DIR>` with the actual absolute output directory path from Step 4
3. Call: `Task(subagent_type: "general-purpose", description: "Generate Oracle migration docs", prompt: <substituted>)`

**Task B — Subagent 4: AQ Migration**

1. Read the prompt template at: `${PLUGIN_ROOT}/skills/common/subagents/oracle/4-aq-migration.md`
2. Substitute all `<OUTPUT_DIR>` with the actual absolute output directory path from Step 4
3. Call: `Task(subagent_type: "general-purpose", description: "Generate AQ setup SQL & consumer Java", prompt: <substituted>)`

**Task C — Subagent 5: Stored Procedure & Trigger Migration**

1. Read the prompt template at: `${PLUGIN_ROOT}/skills/common/subagents/oracle/5-sp-trigger-migration.md`
2. Substitute all `<OUTPUT_DIR>` with the actual absolute output directory path from Step 4
3. Call: `Task(subagent_type: "general-purpose", description: "Generate SP & trigger migration code", prompt: <substituted>)`

**Wait for all three Tasks to complete**, then:
- From Subagent 3 result: extract `DURATION_SECONDS` → store as `S3_DURATION`; extract `total_tokens` from `<usage>` block → store as `S3_TOKENS`
- From Subagent 4 result: extract `DURATION_SECONDS` → store as `S4_DURATION`; extract `total_tokens` from `<usage>` block → store as `S4_TOKENS`
- From Subagent 5 result: extract `DURATION_SECONDS` → store as `S5_DURATION`; extract `total_tokens` from `<usage>` block → store as `S5_TOKENS`
- Record `S345_WALL = max(S3_DURATION, S4_DURATION, S5_DURATION)`

**Check results independently (failures are isolated — one does not block the others):**
- **Subagent 3 fails** → Display error. Note schema analysis outputs remain on disk. Continue checking 4 and 5.
- **Subagent 4 fails** → Display error. Note prior outputs remain on disk. Continue checking 5.
- **Subagent 5 fails** → Display error. Note prior outputs remain on disk.
- Any SUCCESS → Note the relevant counts (COMPLEXITY_SCORE, QUEUES_CREATED, FILES_GENERATED) for the summary.

---

### STEP 11: Display Final Summary with Metrics

**Compute totals before rendering:**
- `TOTAL_DURATION = S0_DURATION + S1_DURATION + S2_DURATION + S345_WALL`
  *(Phases 3, 4 & 5 ran in parallel, so only the longest one adds to wall-clock time)*
- `TOTAL_TOKENS = S0_TOKENS + S1_TOKENS + S2_TOKENS + S3_TOKENS + S4_TOKENS + S5_TOKENS`
  *(If any token value is unavailable, mark it as "N/A" and omit it from the total)*

Display the combined results from all six subagents to the user:

```
Oracle to ScalarDB Migration - Complete

Phase 0: Connection Test
  - Connection method: SQL*Plus (direct database connection)
  - <Subagent 0 SUMMARY line (database product and version)>

Phase 1: Schema Extraction
  - Connected to Oracle at <host>:<port>/<service>
  - <Subagent 1 SUMMARY line>

Phase 2: Schema Report
  - Generated: oracle_schema_report.md
  - <Subagent 2 SUMMARY lines>

Phase 3+4+5: Parallel Migration (ran simultaneously after Phase 2)
  Wall-clock time: <S345_WALL>s  (SA3: <S3_DURATION>s | SA4: <S4_DURATION>s | SA5: <S5_DURATION>s)

  [Phase 3] Migration Analysis
  - Generated: scalardb_migration_analysis.md
  - Generated: scalardb_migration_steps.md
  - Migration Complexity: <Subagent 3 COMPLEXITY_SCORE>
  - <Subagent 3 SUMMARY lines>

  [Phase 4] AQ Migration
  - Generated: aq_setup.sql (Oracle AQ setup — payload types, queues, triggers, enqueue SPs)
  - Generated: scalardb_aq_migration_report.md
  - Java consumer files: <OUTPUT_DIR>/generated-java/
  - Queues created: <Subagent 4 QUEUES_CREATED>
  - Files generated: <Subagent 4 FILES_GENERATED>
  - <Subagent 4 SUMMARY lines>

  [Phase 5] Stored Procedure & Trigger Migration (Direct)
  - Generated: scalardb_sp_migration_report.md
  - Java files: <OUTPUT_DIR>/generated-java/
  - Files generated: <Subagent 5 FILES_GENERATED>
  - <Subagent 5 SUMMARY lines>

Output Directory: <OUTPUT_DIR>

Next Steps:
  1. Review scalardb_migration_analysis.md for compatibility details
  2. Follow scalardb_migration_steps.md for implementation guide
  3. Import database into ScalarDB (required before AQ consumer can work)
  4. Run aq_setup.sql against Oracle to create queues and AQ triggers
  5. Review scalardb_aq_migration_report.md for AQ integration guide
  6. Review generated-java/ for consumer and direct migration code
  7. Review scalardb_sp_migration_report.md for SP & trigger migration details
```

Then display the metrics table:

```
Execution Summary
─────────────────────────────────────────────────────────────────────
 Phase                             │ Subagent Type    │ Tokens  │ Time
─────────────────────────────────────────────────────────────────────
 Phase 0: Connection Test          │ Bash             │ S0_TOK  │ S0s
 Phase 1: Schema Extraction        │ Bash             │ S1_TOK  │ S1s
 Phase 2: Schema Report            │ General-purpose  │ S2_TOK  │ S2s
 Phase 3: Migration Analysis     ┐ │ General-purpose  │ S3_TOK  │ S3s
 Phase 4: AQ Migration           │ │ General-purpose  │ S4_TOK  │ S4s
 Phase 5: SP/Trigger Migration   ┘ │ General-purpose  │ S5_TOK  │ S5s
                  (parallel wall-clock)                        │ S345s
─────────────────────────────────────────────────────────────────────
 TOTAL                             │ 6 subagents      │ TOT_TOK │ TOTs
─────────────────────────────────────────────────────────────────────
```
*(If any token value is unavailable, mark it as "N/A" and omit it from the total)*

---

## Error Handling

- If AskUserQuestion fails or user cancels → stop execution and inform the user
- If configuration write/update fails → show error and do not proceed to subagents
- If **Subagent 0 fails** (API connection test) → show error with resolution hints (check host/port/service, verify credentials, ensure Oracle listener is running, verify network connectivity), **STOP** (do not spawn Subagent 1, 2, 3, 4, or 5)
- If **Subagent 1 fails** (DB connection/extraction error) → show error with resolution hints, **STOP** (do not spawn Subagent 2, 3, 4, or 5)
- If **Subagent 2 fails** (report generation error) → show error, note that `raw_schema_data.json` is available on disk, **STOP** (do not spawn Subagent 3, 4, or 5 — Subagents 4 and 5 need the schema report for table/column context)
- If **Subagent 3 fails** (migration analysis error) → show error, note that schema report is still on disk. Subagents 4 and 5 ran in parallel and are unaffected.
- If **Subagent 4 fails** (AQ migration error) → show error, note that all prior outputs are still on disk. Subagents 3 and 5 ran in parallel and are unaffected.
- If **Subagent 5 fails** (SP & trigger migration error) → show error, note that all prior outputs are still on disk. Subagents 3 and 4 ran in parallel and are unaffected.

Partial outputs are always preserved — if extraction succeeds but later steps fail, earlier output files remain on disk for manual inspection.

---

## Subagent Architecture

This command uses **6 subagents** — 3 sequential then 3 parallel — to isolate heavy processing from the main conversation:

```
SA0 (Bash) → SA1 (Bash) → SA2 (general-purpose) → ┌─ SA3 (general-purpose) ─┐
                                                     ├─ SA4 (general-purpose) ─┤ → Summary
                                                     └─ SA5 (general-purpose) ─┘
```

| Subagent | Type | Phase | Purpose | Returns |
|----------|------|-------|---------|---------|
| 0 | Bash | Sequential | Test DB connection via SQL*Plus | SUCCESS/FAILURE + DB version |
| 1 | Bash | Sequential | Run `oracle_db_extractor.py` | SUCCESS/FAILURE + file path |
| 2 | general-purpose | Sequential | Generate `oracle_schema_report.md` from JSON + template | Executive summary |
| 3 | general-purpose | **Parallel** | Generate migration analysis + steps from report + reference docs | Complexity score + findings |
| 4 | general-purpose | **Parallel** | Generate AQ setup SQL + Java consumer code from triggers/SPs | Queues + files generated |
| 5 | general-purpose | **Parallel** | Generate Java code from PL/SQL + SP & trigger migration report | Files generated + complexity |

SA3, SA4, and SA5 are spawned simultaneously in a single message after SA2 completes. Expected speedup vs. sequential: ~33–55% reduction in wall-clock time for phases 3–5.

The SKILL.md files are **read directly by subagents** as instruction documents (the Skill tool is not invoked).

---

## Related Files

- **Subagent Prompts**: `${PLUGIN_ROOT}/skills/common/subagents/oracle/` (6 prompt templates: `0-test-connection.md` through `5-sp-trigger-migration.md`)
- **Analysis Skill**: `${PLUGIN_ROOT}/skills/migrate-oracle/analyze-oracle-schema/SKILL.md`
- **Report Template**: `${PLUGIN_ROOT}/skills/migrate-oracle/analyze-oracle-schema/analyze-oracle-dbms_report.md`
- **Extractor Script**: `${PLUGIN_ROOT}/skills/migrate-oracle/analyze-oracle-schema/scripts/oracle_db_extractor.py`
- **Migration Skill**: `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-to-scalardb/SKILL.md`
- **Migration Templates**: `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-to-scalardb/templates/`
- **ScalarDB Reference**: `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-to-scalardb/reference/scalardb_reference.md`
- **AQ Migration Skill**: `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-aq-to-scalardb/SKILL.md`
- **AQ Migration Reference**: `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-aq-to-scalardb/reference/aq-migration-strategy-guide.md`
- **AQ Migration Template**: `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-aq-to-scalardb/templates/scalardb_aq_migration_report.md`
- **AQ Official Docs**: `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-aq-to-scalardb/reference/AQ-official-docs/`
- **SP & Trigger Migration Skill**: `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-sp-trigger-to-scalardb/SKILL.md`
- **SP & Trigger Migration Reference**: `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-sp-trigger-to-scalardb/reference/migration-strategy-guide-sp-triggers-to-scalardb.md`
- **SP & Trigger Migration Template**: `${PLUGIN_ROOT}/skills/migrate-oracle/migrate-oracle-sp-trigger-to-scalardb/templates/scalardb_sp_migration_report.md`
- **Config**: `.claude/configuration/databases.env`
