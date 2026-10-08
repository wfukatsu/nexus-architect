---
description: |
  MySQL to ScalarDB migration. Schema extraction, migration analysis, and SP/trigger to Java
  conversion.
model: sonnet
---

Orchestrates the complete MySQL to ScalarDB migration workflow through an interactive chat interface. Collects database connection parameters from the user via questions, updates the configuration file, then runs the analysis and migration skills.

---

## Execution Instructions

Follow these steps in order, without skipping any: each step produces what a later one reads — the plugin root, the configuration, the connection check, the extracted schema — and a step that fails stops the ones after it.

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

Store the result as `PLUGIN_ROOT`. All subagent template paths in Steps 7–11 use this variable (e.g., `PLUGIN_ROOT/skills/common/subagents/mysql/0-test-connection.md`).

---

### STEP 1: Read Current Configuration (or Detect First Run)

First, attempt to read the current configuration file:

```
Read file: .claude/configuration/databases.env
```

**Two possible outcomes:**

**A) File EXISTS** → Set `CONFIG_EXISTS = true`
- Note down the current MySQL values (MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD, MYSQL_INCLUDE_SOURCE, MYSQL_CHARSET, OUTPUT_DIR)
- These will be shown in "Keep current" option descriptions

**B) File DOES NOT EXIST** → Set `CONFIG_EXISTS = false`
- Inform the user: "No existing configuration found. This appears to be a first-time setup — I'll collect all connection parameters from you."
- Ensure the configuration directory exists using Bash: `mkdir -p .claude/configuration`
- All parameters will need to be collected fresh (no "Keep current" option available)

---

### STEP 2: Collect Connection Parameters (Batch 1 of 2)

Build the questions based on CONFIG_EXISTS:

**If CONFIG_EXISTS = true:** Include "Keep current" options with actual values in descriptions (e.g., `"Keep current"` with description `"Keep: localhost"`).

**If CONFIG_EXISTS = false:** Replace "Keep current" options with additional useful defaults instead. Do not offer "Keep current", since there is nothing to keep.

Use the `AskUserQuestion` tool:

```json
{
  "questions": [
    {
      "question": "What is the MySQL database host?",
      "header": "Host",
      "options": [
        {"label": "localhost", "description": "Database running on local machine"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_MYSQL_HOST>"}
                      : {"label": "127.0.0.1", "description": "Loopback IP address"}
      ],
      "multiSelect": false
    },
    {
      "question": "What is the MySQL port?",
      "header": "Port",
      "options": [
        {"label": "3306 (Default)", "description": "Standard MySQL port"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_MYSQL_PORT>"}
                      : {"label": "3307", "description": "Alternative MySQL port"}
      ],
      "multiSelect": false
    },
    {
      "question": "What is the MySQL database name to analyze?",
      "header": "Database",
      "options": [
        {"label": "mysql", "description": "MySQL system database"},
        {"label": "information_schema", "description": "MySQL metadata database"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_MYSQL_DATABASE>"}
                      : {"label": "test", "description": "Common test database"}
      ],
      "multiSelect": false
    },
    {
      "question": "What is the MySQL username?",
      "header": "Username",
      "options": [
        {"label": "root", "description": "MySQL root administrator"},
        CONFIG_EXISTS ? {"label": "Keep current", "description": "Keep: <CURRENT_MYSQL_USER>"}
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
      "question": "Include stored procedure and function source code in the report?",
      "header": "Source Code",
      "options": [
        {"label": "No (Recommended)", "description": "Skip source code - faster analysis, smaller report"},
        {"label": "Yes", "description": "Include full stored procedure/function source code"}
      ],
      "multiSelect": false
    },
    {
      "question": "What character set should be used for the connection?",
      "header": "Charset",
      "options": [
        {"label": "utf8mb4 (Recommended)", "description": "Full Unicode support including emojis"},
        {"label": "utf8", "description": "Basic Unicode (3-byte, no emoji support)"}
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
| **MYSQL_HOST** | "localhost" -> `localhost`, "127.0.0.1" -> `127.0.0.1`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **MYSQL_PORT** | "3306 (Default)" -> `3306`, "3307" -> `3307`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **MYSQL_DATABASE** | "mysql" -> `mysql`, "information_schema" -> `information_schema`, "test" -> `test`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **MYSQL_USER** | "root" -> `root`, "admin" -> `admin`, "Keep current" -> keep existing, "Other" -> user's typed value |
| **MYSQL_PASSWORD** | "Keep current" -> keep existing, "No password" -> empty string, "Type below" -> user must use "Other", "Other" -> user's typed value |
| **MYSQL_INCLUDE_SOURCE** | "No (Recommended)" -> `false`, "Yes" -> `true` |
| **MYSQL_CHARSET** | "utf8mb4 (Recommended)" -> `utf8mb4`, "utf8" -> `utf8` |
| **OUTPUT_DIR** | "Default (.claude/output)" -> absolute path to project's `.claude/output` directory, "Keep current" -> keep existing, "Custom path" -> user must use "Other", "Other" -> user's typed value |

Also set: `ACTIVE_DATABASE=mysql`

---

### STEP 5: Write or Update Configuration File

**If CONFIG_EXISTS = false (first run):**

Read `${PLUGIN_ROOT}/skills/migrate-mysql/reference/databases-env-template.md` and use the **Write** tool to create `.claude/configuration/databases.env` from the template in it, with every `<...>` placeholder replaced by the collected value. The template is needed on this branch only — an existing file is edited, as described next.

**If CONFIG_EXISTS = true (updating existing):**

Use the **Edit** tool to update `.claude/configuration/databases.env` with the collected values:

1. Set `ACTIVE_DATABASE=mysql`
2. Update `OUTPUT_DIR` if changed
3. Update all `MYSQL_*` parameters with the mapped values from Step 4
4. Leave the PostgreSQL and Oracle sections as they are — the file holds every database's configuration, and those belong to other migrations

**After writing/updating, display a confirmation summary to the user:**

```
Configuration <Created / Updated>:
  Host:      <value>
  Port:      <value>
  Database:  <value>
  User:      <value>
  Password:  ******** (hidden)
  Source:    <true/false>
  Charset:   <value>
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

Spawn a **Bash** subagent using the `Agent` tool to test the MySQL database connection via the external API.

1. Read the prompt template at: `${PLUGIN_ROOT}/skills/common/subagents/mysql/0-test-connection.md`
2. Substitute the runtime variables: replace `<MYSQL_HOST>`, `<MYSQL_PORT>`, `<MYSQL_DATABASE>`, `<MYSQL_USER>`, `<MYSQL_PASSWORD>`, and `<OUTPUT_DIR>` with the actual values from Steps 4-5
3. Call the Agent tool with `subagent_type: "Bash"`, `model: "sonnet"`, `description: "Test MySQL connection"`, and the substituted prompt

**After the subagent completes:**
- Extract `DURATION_SECONDS` from the subagent's response → store as `S0_DURATION`
- Extract `total_tokens` from the `<usage>` block in the Agent result (if present) → store as `S0_TOKENS`

**Check the subagent result:**
- If STATUS is **FAILURE** → Display the error to the user with resolution hints (check host/port/database name, verify credentials, ensure MySQL server is running and accepting connections). **Stop here — do not proceed to Step 8, 9, or 10.**
- If STATUS is **SUCCESS** → Note the database product and version, then proceed to Step 8.

---

### STEP 8: Subagent 1 — Schema Extraction (Bash)

Spawn a **Bash** subagent using the `Agent` tool to run the Python extractor script.

1. Read the prompt template at: `${PLUGIN_ROOT}/skills/common/subagents/mysql/1-extract-schema.md`
2. Substitute the runtime variables as documented in the template (replace `<INCLUDE_SOURCE_FLAG>` based on MYSQL_INCLUDE_SOURCE from Step 4)
3. Call the Agent tool with `subagent_type: "Bash"`, `model: "sonnet"`, `description: "Extract MySQL schema"`, and the substituted prompt

**After the subagent completes:**
- Extract `DURATION_SECONDS` from the subagent's response → store as `S1_DURATION`
- Extract `total_tokens` from the `<usage>` block in the Agent result (if present) → store as `S1_TOKENS`

**Check the subagent result:**
- If STATUS is **FAILURE** → Display the error to the user with resolution hints (check host/port, verify credentials, ensure MySQL server is running). **Stop here — do not proceed to Step 9 or Step 10.**
- If STATUS is **SUCCESS** → Note the OUTPUT_FILE path and proceed to Step 9.

---

### STEP 9: Subagent 2 — Schema Report Generation (general-purpose)

Spawn a **general-purpose** subagent using the `Agent` tool to generate the schema report from the extracted JSON.

1. Read the prompt template at: `${PLUGIN_ROOT}/skills/common/subagents/mysql/2-generate-report.md`
2. Substitute the runtime variables as documented in the template (replace all `<OUTPUT_DIR>` with the actual absolute output directory path from Step 4)
3. Call the Agent tool with `subagent_type: "general-purpose"`, `model: "sonnet"`, `description: "Generate MySQL schema report"`, and the substituted prompt

**After the subagent completes:**
- Extract `DURATION_SECONDS` from the subagent's response → store as `S2_DURATION`
- Extract `total_tokens` from the `<usage>` block in the Agent result (if present) → store as `S2_TOKENS`

**Check the subagent result:**
- If STATUS is **FAILURE** → Display the error to the user. Note that `raw_mysql_schema_data.json` is still available for manual inspection. **Stop here — do not proceed to Step 10.**
- If STATUS is **SUCCESS** → Note the summary and proceed to Step 10.

---

### STEP 10: Subagents 3 & 4 — Migration Analysis + SP & Trigger Migration (Parallel)

**Both subagents run simultaneously** in a single message — send both `Agent` tool calls together in one response. They share the same inputs (`mysql_schema_report.md` and `raw_mysql_schema_data.json`) and have no dependency on each other's output.

**Preparation:**
1. Read the prompt template at: `${PLUGIN_ROOT}/skills/common/subagents/mysql/3-migration-analysis.md`
   - Substitute all `<OUTPUT_DIR>` with the actual absolute output directory path from Step 4
2. Read the prompt template at: `${PLUGIN_ROOT}/skills/common/subagents/mysql/4-sp-trigger-migration.md`
   - Substitute all `<OUTPUT_DIR>` with the actual absolute output directory path from Step 4

**Spawn both in one message:**
- Agent call A: `subagent_type: "general-purpose"`, `model: "sonnet"`, `description: "Generate MySQL migration docs"`, substituted prompt from `3-migration-analysis.md`
- Agent call B: `subagent_type: "general-purpose"`, `model: "sonnet"`, `description: "Generate SP & trigger migration code"`, substituted prompt from `4-sp-trigger-migration.md`

**After both subagents complete:**
- From Subagent 3 result: extract `DURATION_SECONDS` → store as `S3_DURATION`; extract `total_tokens` from `<usage>` block → store as `S3_TOKENS`
- From Subagent 4 result: extract `DURATION_SECONDS` → store as `S4_DURATION`; extract `total_tokens` from `<usage>` block → store as `S4_TOKENS`
- Compute parallel wall-clock: `S34_WALL = max(S3_DURATION, S4_DURATION)`

**Error cascading rules:**
- Subagent 2 (Step 9) **failed** → **do not spawn either Subagent 3 or 4** (both need mysql_schema_report.md)
- Subagent 3 **fails** while Subagent 4 **succeeds** → capture both results, report Subagent 3 error, proceed with Subagent 4 output
- Subagent 4 **fails** while Subagent 3 **succeeds** → capture both results, report Subagent 4 error, proceed with Subagent 3 output
- Both fail → display both errors; all prior outputs (schema report, raw JSON) remain on disk

**Check results and proceed to Step 11.**

---

### STEP 11: Display Final Summary with Metrics

Read `${PLUGIN_ROOT}/skills/migrate-mysql/reference/final-summary.md` and display what it specifies: the combined results of all subagents, then the timing and token usage table. The file also says how the totals are computed. Display both for a partial run as well (see Error Handling).

---

## Error Handling

- If AskUserQuestion fails or user cancels → stop execution and inform the user
- If configuration write/update fails → show error and do not proceed to subagents
- If **Subagent 0 fails** (API connection test error) → show error with resolution hints (check host/port/database, verify credentials, ensure MySQL server is running), **STOP** (do not spawn Subagent 1, 2, 3, or 4)
- If **Subagent 1 fails** (DB connection/extraction error) → show error with resolution hints, **STOP** (do not spawn Subagent 2, 3, or 4)
- If **Subagent 2 fails** (report generation error) → show error, note that `raw_mysql_schema_data.json` is available on disk, **STOP** (do not spawn Subagent 3 or 4 — both need mysql_schema_report.md)
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
| 0 | 7 | Bash | POST to `test-mysql-connection` API to verify DB is reachable | SUCCESS/FAILURE + DB version + DURATION_SECONDS |
| 1 | 8 | Bash | Run `mysql_db_extractor.py` | SUCCESS/FAILURE + file path + DURATION_SECONDS |
| 2 | 9 | General-purpose | Generate `mysql_schema_report.md` from JSON + template | Executive summary + DURATION_SECONDS |
| 3 | 10 ┐ | General-purpose | Generate migration analysis + steps from schema report + reference docs | Complexity score + findings + DURATION_SECONDS |
| 4 | 10 ┘ | General-purpose | Generate Java code from MySQL routines + SP & trigger migration report | Files generated + complexity + DURATION_SECONDS |

**Parallelism:** Subagents 3 and 4 are spawned simultaneously in Step 10 (single message, two Agent calls). Both read from `mysql_schema_report.md` and `raw_mysql_schema_data.json`; neither depends on the other.

**Metrics tracking:** After each Agent call, extract `total_tokens` and `duration_ms` from the `<usage>` block in the result, and `DURATION_SECONDS` from the subagent's self-reported output. Use these to populate the Step 11 summary table.

The skill files are **read directly by subagents** as instruction documents (the Skill tool is not invoked).

---

## Related Files

- **Subagent Prompts**: `${PLUGIN_ROOT}/skills/common/subagents/mysql/` (5 prompt templates)
- **Analysis Skill**: `${PLUGIN_ROOT}/skills/migrate-mysql/analyze-mysql-schema/SKILL.md`
- **Report Template**: `${PLUGIN_ROOT}/skills/migrate-mysql/analyze-mysql-schema/analyze-mysql-dbms_report.md`
- **Extractor Script**: `${PLUGIN_ROOT}/skills/migrate-mysql/analyze-mysql-schema/scripts/mysql_db_extractor.py`
- **Migration Skill**: `${PLUGIN_ROOT}/skills/migrate-mysql/migrate-mysql-to-scalardb/SKILL.md`
- **Migration Templates**: `${PLUGIN_ROOT}/skills/migrate-mysql/migrate-mysql-to-scalardb/templates/`
- **ScalarDB Reference**: `${PLUGIN_ROOT}/skills/migrate-mysql/migrate-mysql-to-scalardb/reference/scalardb_mysql_reference.md`
- **SP & Trigger Migration Skill**: `${PLUGIN_ROOT}/skills/migrate-mysql/migrate-mysql-sp-trigger-to-scalardb/SKILL.md`
- **SP & Trigger Migration Reference**: `${PLUGIN_ROOT}/skills/migrate-mysql/migrate-mysql-sp-trigger-to-scalardb/reference/migration-strategy-guide-sp-triggers-to-scalardb.md`
- **SP & Trigger Migration Template**: `${PLUGIN_ROOT}/skills/migrate-mysql/migrate-mysql-sp-trigger-to-scalardb/templates/scalardb_sp_migration_report.md`
- **Configuration template** (Step 5, first run): `${PLUGIN_ROOT}/skills/migrate-mysql/reference/databases-env-template.md`
- **Final summary format** (Step 11): `${PLUGIN_ROOT}/skills/migrate-mysql/reference/final-summary.md`
- **Config**: `.claude/configuration/databases.env`
