# Final summary and metrics (MySQL migration)

Read by `/architect:migrate-mysql` at Step 11. It says how the totals are computed and gives the two
blocks to display, in order: the combined results of the subagents, then the timing and token table.
A partial run displays them too, with a failed subagent marked `FAILED`.

Display the combined results from all five subagents, then a timing and token usage table.

**Compute totals before rendering:**
- `TOTAL_DURATION = S0_DURATION + S1_DURATION + S2_DURATION + S34_WALL`
  *(Phases 3 & 4 ran in parallel, so only the longer one adds to wall-clock time)*
- `TOTAL_TOKENS = S0_TOKENS + S1_TOKENS + S2_TOKENS + S3_TOKENS + S4_TOKENS`
  *(If any token value is unavailable, mark it as "N/A" and omit it from the total)*

Display to the user:

```
MySQL to ScalarDB Migration — Complete

Phase 0: Connection Test
  - Connection method: Python mysql-connector-python (direct database connection)
  - <Subagent 0 SUMMARY line (database product and version)>

Phase 1: Schema Extraction
  - Connected to MySQL at <host>:<port>/<database>
  - <Subagent 1 SUMMARY line>

Phase 2: Schema Report
  - Generated: mysql_schema_report.md
  - <Subagent 2 SUMMARY lines>

Phase 3 + 4 (Parallel):
  Migration Analysis:
    - Generated: scalardb_mysql_migration_analysis.md
    - Generated: scalardb_mysql_migration_steps.md
    - Migration Complexity: <Subagent 3 COMPLEXITY_SCORE>
    - <Subagent 3 SUMMARY lines>
  SP & Trigger Migration:
    - Generated: scalardb_mysql_sp_migration_report.md
    - Java files: <OUTPUT_DIR>/generated-java/
    - Files generated: <Subagent 4 FILES_GENERATED>
    - <Subagent 4 SUMMARY lines>

Output Directory: <OUTPUT_DIR>

Next Steps:
  1. Review scalardb_mysql_migration_analysis.md for compatibility details
  2. Follow scalardb_mysql_migration_steps.md for implementation guide
  3. Review generated-java/ for migrated stored procedure code
  4. Review scalardb_mysql_sp_migration_report.md for SP & trigger migration details
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
