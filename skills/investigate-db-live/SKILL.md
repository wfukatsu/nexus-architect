---
name: investigate-db-live
description: |
  Investigate an existing database by connecting to its catalogs and existing statistics.
  Oracle, PostgreSQL and MySQL adapters return scoped, source-linked structure and metrics,
  distinguishing unavailable data from empty results. Use
  /architect:investigate-db-live [--profile=path] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# Investigate a Live Database

## Outcome and prerequisites

Inventory visible schema objects, declared relationships and existing statistics, with
query evidence and collection limits. No ScalarDB target or source-code analysis is required.
Read @rules/database-investigation.md and
@skills/common/database-investigation/contract.md, then only the selected adapter's
`reference.md`, `adapter.json` and driver requirements in that common directory.

Use an authorized connection, an explicit target environment and schema, a target ID, and
the expected database version. Reuse already supplied authorization; do not infer permission
to connect from merely finding credentials on disk. Ask for missing scope/profile details.
Never request a password in chat. Keep connection settings outside Git and use environment
references or the supported Wallet setup. Unknown versions require a separately authorized
identification probe before creating the expected-version profile; do not guess.

## Connection profile

The JSON profile contains references, never secret values:

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

Use the exact catalog/schema/owner spelling. MySQL's schema is its database; Oracle uses
`service_env` (and optionally `database_env` for the expected PDB name), with optional
`wallet_location_env` and `wallet_password_env`. Oracle uses verified TCPS by default;
PostgreSQL verifies hostname/certificate; MySQL requires a CA. Only explicitly isolated
loopback tests may set `allow_local_plaintext: true`. No arbitrary driver options/modules.

## Procedure

1. Confirm the supplied environment, expected product/version, exact schema, visible scope
   and bounded collection. Review the adapter's query list and capability notes. Use a
   read-only account with only the metadata visibility needed; do not elevate privileges or
   enable extensions/monitoring to make a report complete.
2. In an isolated Python environment install only the selected adapter's requirements if
   missing. Before introducing/updating a version pin, follow @rules/dependency-versions.md:
   verify registry/compatibility, preserve existing decisions and follow confirmation options.
   Read the adapter reference for the tested combination; do not promise all historical versions.
3. Run from the output project directory:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/database-investigation/scripts/investigate.py" live \
     --profile /path/to/private/profile.json --lang ja
   ```

   The python3 helper accepts row limits, time budgets, output roots and run IDs (see contract).
   Defaults are 10000 rows per query and 120 seconds for collection. Limits must fit the target
   workload. Connection and individual query timeouts are independently bounded. See the
   contract for cancellation limits. The version/product/catalog probe must match before
   collection; a mismatch is fatal, never a fallback to another adapter.
4. Read `collection-summary.json` before interpreting the inventory. Keep permission denied,
   disabled, unsupported, timeout, error, empty and truncated distinct. An ALL_/catalog view
   describes visibility, not a proof that hidden objects do not exist. Oracle segment bytes
   are owner-only in the initial adapter. Explain partial coverage in the report.
5. Assess schema integrity and statistics with evidence. Metrics retain their units,
   estimate/measured/cumulative semantics and timestamps. Do not infer a rate, trend or an
   index deletion recommendation from one snapshot or counters with unknown resets.
   Append `live-review.md` using @templates/database-investigation/review.md for reasoned findings, each with query evidence IDs, limitations
   and follow-up questions. No row sampling, arbitrary SQL text, histogram boundary values,
   AWR/ASH, DDL/DML, ANALYZE, EXPLAIN ANALYZE or statistics resets are part of this skill.
6. Validate JSON and every report's frontmatter/Mermaid. Record unresolved user decisions in
   the shared `work/context.md` under existing/next OQ IDs; don't replace pipeline state.

## Outputs and completion

`reports/01_analysis/database-investigation/<target-id>/live/<run-id>/` contains
`inventory.json`, `collection-summary.json`, `investigation-report.md`, `er-diagram.md`.
The skill adds `live-review.md` with required report frontmatter. Raw driver errors and
credentials are not printed; diagnose failures locally without copying secret-bearing logs.

Report successful coverage and partial/fatal limits truthfully (helper exit 0/2/1).
Offer the selected run as optional input to `/architect:analyze-data-model`. Never merge a
design-input snapshot and live run silently or automatically rerun existing migration skills.
