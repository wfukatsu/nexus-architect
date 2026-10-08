# Final summary and metrics (Oracle migration)

Read by `/architect:migrate-oracle` at Step 11. It says how the totals are computed and gives the two
blocks to display, in order: the combined results of the subagents, then the timing and token table.
A partial run displays them too, with a failed subagent marked `FAILED`.

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
