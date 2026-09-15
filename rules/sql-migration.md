# SQL migration to ScalarDB

Applies to `/architect:design-sql-migration`, `implement-sql-migration` and `verify-sql-migration`, and to
anyone reading their manifest. The mechanism (converter, execution plans, runtime) is described in
`skills/common/sql-migration/references/architecture.md`; this rule is the contract the manifest
validator (`tools/lib/sql_migration_manifest.py`) enforces.

## 1. One statement, one decision

Every statement in `reports/03_design/sql-migration/sql-inventory.json` gets exactly one entry in
`sql-migration-manifest.json`, under the same `SQM-###` ID. A statement nobody decided is a gap in the
migration, not a statement that does not matter; one decided twice is a contradiction. Statements the
inventory could not extract (`unextracted` calls, `unavailable` definitions of a live run) have no ID
and are reported as open work, never silently dropped.

## 2. Routes

| Route | Meaning | Converter status it may follow | What the entry must carry |
|---|---|---|---|
| `schema` | DDL that becomes the ScalarDB schema (Schema Loader JSON) | OK / WARN, DDL only | `rationale` |
| `scalardb_sql` | runs as the converted ScalarDB SQL | OK / WARN | `rationale`; the edition has ScalarDB SQL |
| `core_api` | same access, written against the Core API (Get / Scan / Put / Delete) | OK / WARN | `rationale` |
| `plan` | fetch through ScalarDB, run the original SQL in in-memory H2 | PLANNED | `rationale`, `plan.row_limit` |
| `app_side` | reimplemented in the application | PLANNED / ERROR (OK / WARN too, when the user prefers it) | `rationale`, `app_side.pattern`, and `app_side.semantics` when the converter reported `APP_SEMANTICS` |
| `redesign` | the schema or the use case changes (keys, summary table, precomputed hierarchy, ScalarDB Analytics) | any | `rationale`, `redesign.proposal`; an ADR when it changes keys or the backend |
| `retire` | the statement is not migrated (dead code, a one-off script) | any | `rationale`, `retire.evidence` |

- `ERROR` never takes `scalardb_sql`, `core_api` or `plan`; `PLANNED` never takes `scalardb_sql` or
  `core_api`. The converter's verdict is recorded in `converter.status` / `codes` / `pattern` as produced.
- `schema` is for DDL only, and DDL takes no query route.
- JPQL (`language: jpql`) is not SQL the converter reads: it takes `app_side`, `redesign` or `retire`.
- `app_side.pattern` is one of `read` (a query rewritten with the helpers), `rmw` (read → compute →
  write in one transaction, P9), `conditional_write` (existence check and write, P10), `id_generation`
  (P11), `app_clock` (P12). Each `app_side.semantics` entry names the note it answers and how the code
  keeps it (`Windows.lag`, `OracleNumbers.round`, an injected clock).

## 3. Edition and storage

- `target.edition` is `community`, `enterprise_standard` or `enterprise_premium`
  (@rules/scalardb-edition-profiles.md). ScalarDB SQL is Enterprise Premium: under any other edition no
  statement takes `scalardb_sql` — it takes `core_api` or `app_side`.
- `target.storage` is `jdbc` or `cassandra`, and must be the storage the converter ran with. Cassandra has
  no cross-partition scan; the converter reflects that in its verdicts.
- Plans fetch through `CoreFetcher` (no license) unless the edition has ScalarDB SQL.

## 4. Dynamic SQL

A `dynamic` statement (string concatenation with a variable, MyBatis dynamic elements, `${...}`) is a
family of statements; the converter saw one rendering of it. It takes an automatic route (`schema`,
`scalardb_sql`, `core_api`, `plan`) only with `confirmation: {"by": "user", "note": ...}` recording which
variants were expanded and converted. Otherwise it takes `app_side`, `redesign` or `retire`.

## 5. Keys

`keys[]` records the partition key, clustering key and secondary indexes per table, where the choice came
from (`design-scalardb`; `investigation` for an investigate-db-design run; `source_ddl` for DDL read from
a SQL file or the application; `user`) and why. Every table and column named there exists in
`schema.json`. Key design decides post-migration cost more than any rewrite: a query the partition key
cannot narrow becomes a cross-partition scan.

## 6. Evidence and traceability

- Each statement's `origin` lines must still exist in the source file; the full text is re-extracted from
  there when code is generated (`inventory.py`), and a changed source is refused, not guessed.
- `upstream` IDs, when given, resolve in `work/traceability.json`. The skill appends one `SQM-` node per
  statement with those upstreams (allocation `max + 1`, @docs/design.md §1.5).

## 7. Verification

`verification.status` is `pending`, `verified`, `failed` or `skipped`.

| Status | Requires |
|---|---|
| `verified` / `failed` | `method` (`golden`, `difftest`, `plan_validate`, `unit`) and `evidence` (a report path) |
| `skipped` | `reason` (no authorized source database, no license for ScalarDB SQL, ...) |

A statement is migrated when it is `verified`. `pending` and `skipped` are reported as unproven, never as
done.

## 8. Never

- Connect to ScalarDB's backend database directly — fetch and load go through ScalarDB.
- Connect to a production source database: capture golden results and run differential tests only against
  a database the user authorized, through an environment-reference profile.
- Store string literals from application code or DDL in reports; the inventory masks them.
- Present a converter `OK` as proof of equivalence: it means the grammar accepted the output.
