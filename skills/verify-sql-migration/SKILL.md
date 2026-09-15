---
description: |
  Prove the SQL migration on data and record what was proven: golden checks that compare application-side
  implementations with results captured once from an authorized source database, and differential tests that run
  plan and ScalarDB SQL routes against the source database and ScalarDB side by side — then write each statement's
  verification state (verified / failed / skipped with its reason) back into the migration manifest.
  /architect:verify-sql-migration [target_path] [--mode=golden|difftest|all] [--id=<SQM-###>] [--source-profile=<path>] [--scalardb-properties=<path>] [--fetcher=core|jdbc] [--out=<path>] [--auto] [--lang=en|ja] to invoke.
  Extension tier; requires implement-sql-migration. Never connects to a production database.
model: sonnet
user_invocable: true
disable-model-invocation: true
---

# SQL Migration Verification

## Desired Outcome

For every statement of `reports/03_design/sql-migration/sql-migration-manifest.json`, an honest answer to **has this
route been shown to return what the source database returns?**

- **Golden checks** — for application-side reads, the source database's input tables and result captured once into
  `golden.json`, and the generated implementation (`appside/Sqm###Query`) compared with it without a database.
- **Differential tests** — for `plan` and `scalardb_sql` reads, the full original statement on the source database
  and the migrated route on ScalarDB, with the same data, compared as result sets.
- **Recorded states** — `verification` in the manifest: `verified` / `failed` with method and evidence, `skipped` with
  the reason; the manifest validator accepts the result.
- **Report** — `reports/09_verification/sql-migration/verification-report.md` plus one JSON evidence file per run.

This skill opens database connections, so it runs only when explicitly invoked.

## Invocation

```
/architect:verify-sql-migration [target_path] [--mode=golden|difftest|all] [--id=<SQM-###>] [--source-profile=<path>] [--scalardb-properties=<path>] [--fetcher=core|jdbc] [--out=<path>] [--auto] [--lang=en|ja]
```

- `target_path` — Project directory; defaults to the current directory.
- `--mode` — `golden`, `difftest` or `all` (default).
- `--id` — Verify only this statement (repeatable).
- `--source-profile` — Connection profile of the source database: environment references only, the same shape as
  `/architect:investigate-db-live` plus a required `environment` of `local`, `test` or `staging`.
- `--scalardb-properties` — ScalarDB client properties for the differential test.
- `--fetcher` — `core` (ScalarDB Core API, no license) or `jdbc` (ScalarDB SQL through ScalarDB Cluster, licensed).
  ScalarDB SQL statements are only compared with `jdbc`.
- `--out` — Generated module; defaults to the one `migration-summary.json` names under `generated/sql-migration/`.
- `--auto` — No questions: golden checks for statements whose `golden.json` already exists, no capture, no
  differential test without a profile.
- `--lang` — Output language of the report.

## Decision Criteria

- **Authorization is explicit, and production is out of reach.** Capture and differential tests run only against a
  database the user authorized for verification: a disposable container, a test or a staging copy. The profile
  states `environment`; `production` is refused by the tooling, and a profile without it is refused too. Never ask
  for a password in chat; credentials stay in environment variables or Wallets.
- **Same data on both sides.** A differential test compares routes, not datasets: ScalarDB holds exactly the rows the
  source holds for the tables involved (load them through `residual-runner load`), or the comparison proves nothing.
- **Never overstate.** `verified` needs a passing comparison and its evidence file. A skip keeps an earlier proof but
  never creates one; a harness error (no JVM, a connection failure) is not a verdict and leaves the state unchanged.
- **Data stays out of reports.** Evidence files and the report state row counts and the first differing row index,
  never row values. Golden files hold captured rows and live only in the generated module's test resources.
- **A failure is a finding, not a fix.** A failed statement goes back to `implement-sql-migration` (an implementation
  defect) or `design-sql-migration` (a wrong route); this skill does not edit code or decisions.

## Prerequisites

| Input | Required/Recommended | Source |
|------|---------------------|--------|
| `reports/03_design/sql-migration/sql-migration-manifest.json`, `sql-inventory.json` | Required | /architect:design-sql-migration |
| `generated/sql-migration/<namespace>/` built with `gradle build` | Required | /architect:implement-sql-migration |
| The vendored runtime installed | Required | `cd "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/runtime-java" && gradle installDist` |
| An authorized source database profile | Required for capture and difftest | the user |
| ScalarDB with the migrated schema and the same data | Required for difftest | Schema Loader with `schema.json`, then `residual-runner load` |
| The source database driver (`oracledb`, `psycopg`, `PyMySQL`) | Required for capture and difftest | the pins in `skills/common/database-investigation/adapters/<product>/requirements.txt` |

## Steps

1. **Record progress** — `in_progress` in `work/pipeline-progress.json` (`plugin: architect`).
2. **Confirm scope and authorization.** List the statements by route and current verification state. Ask which
   database the user authorizes, confirm its `environment`, and whether ScalarDB SQL (licensed) is in scope.
3. **Golden checks** (`--mode=golden|all`), per application-side read:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/scripts/verify/golden.py" capture \
     --project-dir <project_dir> --profile <private/profile.json> --out <generated module> --id <SQM-###>
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/scripts/verify/golden.py" check \
     --project-dir <project_dir> --out <generated module> --package <java.package> --id <SQM-###> --record
   ```

   Capture only when the user authorized it; it refuses a table over its row bound (a golden set is a fixture, not a
   copy of production). A statement whose skeleton still throws fails — that is the expected state before it is
   implemented.
4. **Differential tests** (`--mode=difftest|all`):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/scripts/verify/difftest.py" \
     --project-dir <project_dir> --profile <private/profile.json> --scalardb-properties <scalardb.properties> \
     --fetcher core --out <generated module> --record
   ```

   Plans run through `residual-runner run`; ScalarDB SQL statements run through `residual-runner sql` only with
   `--fetcher jdbc`. Writes, schema statements and statements whose source changed are skipped with their reason.
5. **Validate** — `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/sql_migration_manifest.py" <project_dir>` exits 0.
6. **Report** `reports/09_verification/sql-migration/verification-report.md` (below), run both report hooks, mark the
   phase `completed`.

## Output

| File | Content |
|------|---------|
| `reports/03_design/sql-migration/sql-migration-manifest.json` | `verification` updated per statement |
| `reports/09_verification/sql-migration/<mode>-<timestamp>.json` | Evidence of one run: per statement the method, outcome and reason |
| `reports/09_verification/sql-migration/verification-report.md` | The report |
| `<generated module>/src/test/resources/golden/SQM-###/golden.json` | Captured golden data (test resources of the git-ignored module) |

Report structure (frontmatter `title`, `schema_version: 1`, `phase: "Phase 9: Verification"`,
`skill: verify-sql-migration`, `generated_at`, `input_files`): **Summary** (states by route), **Environment** (source
environment and product, ScalarDB fetcher, what was out of scope and why), **Results** (one row per statement: SQM ID,
route, method, outcome, reason, evidence file), **Failures** (where each goes next), **Unproven** (pending and skipped
statements with what would prove them).

## Completion Criteria

1. Every statement in scope has a recorded state, and the manifest validator exits 0
2. Every `verified` state names its method and an evidence file that exists
3. No production database was connected to; the report names the environment used
4. The report passes both hooks and contains no row values

## Related Skills

- `/architect:implement-sql-migration` — the module under test; where implementation failures go
- `/architect:design-sql-migration` — where a wrong route goes
- `/architect:investigate-db-live` — the profile shape reused here
