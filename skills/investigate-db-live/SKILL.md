---
name: investigate-db-live
description: |
  Investigate an existing database by connecting to its catalogs and existing statistics.
  Oracle, PostgreSQL and MySQL adapters return scoped, source-linked structure and metrics,
  distinguishing unavailable data from empty results. Use
  /architect:investigate-db-live [--profile=path] [--lang=ja|en].
model: sonnet
user_invocable: true
disable-model-invocation: true
---

# Investigate a Live Database

## Desired Outcome

An inventory of the visible schema objects, declared relationships and existing statistics of
one authorized database, with query evidence and collection limits, in one new run directory:
`inventory.json`, `collection-summary.json`, `investigation-report.md`, `er-diagram.md`, and the
skill's `live-review.md`. No ScalarDB target or source-code analysis is required.

This skill opens a connection to a real database, so it runs only when explicitly invoked.

## Decision Criteria

- **Authorization is explicit.** Reuse already supplied authorization; do not infer permission to
  connect from merely finding credentials on disk. Never request a password in chat.
- **Read-only and bounded.** Fixed, schema-bound SELECTs only. No row sampling, arbitrary SQL
  text, histogram boundary values, AWR/ASH, DDL/DML, ANALYZE, EXPLAIN ANALYZE or statistics
  resets. Do not elevate privileges or enable extensions/monitoring to make a report complete.
- **Identity before collection.** The version/product/catalog probe must match the profile; a
  mismatch — including a compatible product such as Aurora, YugabyteDB, MariaDB or TiDB — is
  fatal, never a fallback to another adapter.
- **Visibility is not existence.** An ALL_/catalog view describes what the connected user can see.
  Keep permission denied, disabled, unsupported, timeout, error, empty and truncated distinct.
- **One snapshot proves little.** Metrics retain their units, estimate/measured/cumulative
  semantics, granularity and timestamps. Do not infer a rate, trend or an index deletion
  recommendation from one snapshot or counters with unknown resets.

Read @rules/database-investigation.md and @skills/common/database-investigation/contract.md,
then only the selected adapter's `reference.md`, `adapter.json` and driver requirements in that
common directory.

## Prerequisites

| Input | Required | Notes |
|---|---|---|
| Authorized connection | Required | A read-only account with only the metadata visibility needed |
| Target environment and exact schema | Required | Exact catalog/schema/owner spelling; MySQL's schema is its database |
| Expected database version | Required | Unknown versions need a separately authorized identification probe before the profile is written; do not guess |
| Connection profile | Required | JSON of environment references, kept outside Git (below) |
| Output language | Optional | Argument, then `options.output_language` in `work/pipeline-progress.json` |

The profile contains references, never secret values:

```json
{
  "product": "postgresql",
  "expected_version": "<approved-server-version>",
  "schema": "app",
  "target_id": "existing-db",
  "host_env": "INV_DB_HOST",
  "port_env": "INV_DB_PORT",
  "database_env": "INV_DB_DATABASE",
  "user_env": "INV_DB_USER",
  "password_env": "INV_DB_PASSWORD",
  "tls_ca_env": "INV_DB_CA"
}
```

Oracle uses `service_env` (and optionally `database_env` for the expected PDB name), with optional
`wallet_location_env` and `wallet_password_env`. Oracle uses verified TCPS by default;
PostgreSQL verifies hostname/certificate; MySQL requires a CA. Only explicitly isolated loopback
tests may set `allow_local_plaintext: true`. No arbitrary driver options/modules.

## Steps

1. **Confirm scope.** The supplied environment, expected product/version, exact schema, visible
   scope and bounded collection. Review the adapter's query list and capability notes.
2. **Prepare the driver.** In an isolated Python environment install only the selected adapter's
   requirements if missing. Before introducing/updating a version pin, follow
   @rules/dependency-versions.md: verify registry/compatibility, preserve existing decisions and
   follow confirmation options. Read the adapter reference for the tested combination; do not
   promise all historical versions.
3. **Collect** from the output project directory:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/database-investigation/scripts/investigate.py" live \
     --profile /path/to/private/profile.json --lang ja
   ```

   Row limits, time budget, output root and run ID are helper options listed in the contract.
   Defaults are 10000 rows per query and 120 seconds for collection; limits must fit the target
   workload. Connection and individual query timeouts are independently bounded. See the
   contract for cancellation limits.
4. **Read coverage first.** Read `collection-summary.json` before interpreting the inventory, and
   explain partial coverage in the report. Oracle segment bytes are owner-only in the initial
   adapter; PostgreSQL partitions appear as partition-granularity statistics, not as tables.
5. **Assess.** Schema integrity and statistics, with evidence. Write `live-review.md` using
   @templates/database-investigation/review.md for reasoned findings, each with query evidence
   IDs, limitations and follow-up questions.
6. **Validate.** Validate JSON and every report's frontmatter/Mermaid. Record unresolved user
   decisions in the shared `work/context.md` under existing/next OQ IDs; don't replace pipeline
   state.

## Outputs and Completion

`reports/01_analysis/database-investigation/<target-id>/live/<run-id>/` contains the four helper
outputs plus `live-review.md` with the output-convention frontmatter. Raw driver errors and
credentials are not printed; diagnose failures locally without copying secret-bearing logs.

Report successful coverage and partial/fatal limits truthfully (helper exit 0/2/1). Offer the
selected run as optional input to `/architect:analyze-data-model`. Never merge a design-input
snapshot and live run silently or automatically rerun existing migration skills.
