---
description: |
  Generate the code the SQL migration manifest decided: ScalarDB SQL statements, the ScalarDB schema, fetch-and-H2
  execution plans with their executor, a Core API interface and application-side skeletons that carry the semantics
  they must keep — into a self-contained Gradle module under generated/, behind an offline gate that refuses when
  the manifest no longer matches the source or the converter.
  /architect:implement-sql-migration [target_path] [--out=<path>] [--package=<java.package>] [--confirm-versions|--no-confirm-versions] [--refresh-versions] [--dry-run] [--auto] [--lang=en|ja] to invoke.
  Extension tier; requires design-sql-migration. Followed by verify-sql-migration.
model: sonnet
user_invocable: true
---

# SQL Migration Implementation

## Desired Outcome

A Gradle module at `generated/sql-migration/<target>/` that turns every decision of
`reports/03_design/sql-migration/sql-migration-manifest.json` into code — never a decision of its own:

| Route | Generated |
|---|---|
| `schema` | `src/main/resources/schema.json` (Schema Loader JSON) |
| `scalardb_sql` | `src/main/resources/sql/SQM-###.sql` and a constant in `ScalarDbSqlStatements` — the converted statement, full text |
| `plan` | `src/main/resources/plans/SQM-###.plan.json` and `MigrationPlans`, which fetches in one read-only transaction and runs the original SQL in H2 |
| `core_api` | a method on `CoreApiStatements` to implement, documented with the access the converted SQL states |
| `app_side` | `appside/Sqm###Query` (read, with a disabled golden test), `Sqm###Write` (read-modify-write, conditional write, application clock) or `Sqm###IdGenerator`, each documenting the semantics it must keep |
| `redesign`, `retire` | nothing — listed in the summary |

plus the vendored runtime (`com.scalar.migrate.runtime` / `appside`), `build.gradle` with resolved versions,
`migration-summary.json`, and `reports/06_implementation/sql-migration-implementation.md`.

Implementing the `core_api` methods and the application-side skeletons is the next step, test-first
(@rules/tdd-workflow.md); the golden checks of `verify-sql-migration` are their outer loop.

## Invocation

```
/architect:implement-sql-migration [target_path] [--out=<path>] [--package=<java.package>] [--confirm-versions|--no-confirm-versions] [--refresh-versions] [--dry-run] [--auto] [--lang=en|ja]
```

- `target_path` — Project directory; defaults to the current directory.
- `--out` — Output directory; defaults to `generated/sql-migration/<namespace>/`.
- `--package` — Java package of the generated classes; asked when omitted (candidates from the application's packages).
- `--confirm-versions` / `--no-confirm-versions` — Whether the resolved dependency versions are confirmed before
  pinning (@rules/dependency-versions.md §4).
- `--refresh-versions` — Re-resolve versions even when `work/version-decisions.json` is recent.
- `--dry-run` — Run the gate and report what would be generated; write nothing.
- `--auto` — No questions; versions adopted per the rule, the package defaults to `<namespace>.migration`.
- `--lang` — Output language of the implementation report.

## Decision Criteria

- **The manifest is the only source of decisions.** A route the manifest does not state is not generated; a
  statement that looks wrong is sent back to `design-sql-migration`, never re-decided here.
- **The gate refuses rather than repairs.** Converter drift, a changed source, an invalid manifest or an unresolved
  version stops generation with every violation listed. Report them and stop.
- **Generated is not implemented.** Skeletons throw `UnsupportedOperationException`; the report counts them as work
  remaining, never as migrated statements.
- **Transactions follow the ScalarDB rules.** A write skeleton commits once and rolls back on failure, except on
  `UnknownTransactionStatusException`, whose outcome is unknown (@rules/scalardb-exception-handling.md).
- **`generated/` only.** The generator writes nowhere else and replaces only a directory it wrote before.

## Prerequisites

| Input | Required/Recommended | Source |
|------|---------------------|--------|
| `reports/03_design/sql-migration/sql-migration-manifest.json` | Required | /architect:design-sql-migration — must pass its validator |
| `reports/03_design/sql-migration/sql-inventory.json`, `schema.json`, `conversion.json` | Required | /architect:design-sql-migration |
| The source files the inventory cites | Required | the project — re-read to recover each statement's full text |
| `sqlglot` from `requirements.txt` | Required | `pip install -r "${CLAUDE_PLUGIN_ROOT}/requirements.txt"` |
| Java 17 and Gradle | Required for the build check | the environment |
| `reports/03_design/aggregates/aggregate-manifest.json` | Optional | /architect:design-aggregate — which aggregate's transaction a rewritten write belongs to |

## Steps

1. **Record progress.** Mark the phase `in_progress` in `work/pipeline-progress.json` (`plugin: architect`).
2. **Resolve versions.** The module pins `com.scalar-labs:scalardb` (and, under Enterprise Premium,
   `scalardb-sql-jdbc` / `scalardb-cluster-java-client-sdk` at the same version), `com.h2database:h2`,
   `com.google.code.gson:gson` and `org.junit:junit-bom`. Reuse `work/version-decisions.json` when under seven days
   old; otherwise look each up from its registry, choose stable and mutually compatible releases, confirm per the
   flags, and write the entries (@rules/dependency-versions.md). The ScalarDB version matches the manifest's
   `target.scalardb_version` line when it names one.
3. **Choose the package** from `--package`, or ask with candidates taken from the application's source roots.
4. **Generate behind the gate.**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/scripts/generate_migration.py" \
     --project-dir <project_dir> --out generated/sql-migration/<namespace> --package <java.package>
   ```

   Exit 1 prints every gate violation: converter drift or a changed source means the design is stale — re-run
   `/architect:design-sql-migration`; an invalid manifest is fixed there too; a missing version means step 2 did
   not finish. With `--dry-run`, stop after reporting the gate result. The generator creates no output when it
   refuses.
5. **Check the module offline.**

   ```bash
   cd generated/sql-migration/<namespace> && gradle build
   ```

   Then validate each plan against H2 without a database, with the vendored runtime built into the project —
   never into `${CLAUDE_PLUGIN_ROOT}`, which an installed plugin may keep read-only or shared:

   ```bash
   mkdir -p work/sql-migration && rm -rf work/sql-migration/runtime-java
   cp -R "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/runtime-java" work/sql-migration/runtime-java
   cd work/sql-migration/runtime-java && gradle installDist && cd -
   work/sql-migration/runtime-java/build/install/residual-runner/bin/residual-runner validate --plan <out>/src/main/resources/plans/<SQM-###>.plan.json
   ```

   `verify-sql-migration` uses the same build.

   A plan H2 rejects goes back to design as a finding against that statement; the build failing is a generator
   defect to report, not to patch by hand.
6. **Write the report** `reports/06_implementation/sql-migration-implementation.md` (below), run both report hooks,
   and mark the phase `completed` with its outputs.

## Output

| File | Content |
|------|---------|
| `generated/sql-migration/<namespace>/` | The Gradle module |
| `generated/sql-migration/*/build.gradle` | The module's build, pinning the versions from `work/version-decisions.json` |
| `generated/sql-migration/*/migration-summary.json` | What was generated per statement, what still needs implementing, and the manifest hash it came from |
| `reports/06_implementation/sql-migration-implementation.md` | The implementation report |

Report structure (frontmatter `title`, `schema_version: 1`, `phase: "Phase 6: Implementation"`,
`skill: implement-sql-migration`, `generated_at`, `input_files`):

- **Summary** — statements by route; generated, to implement, not generated
- **Version Decisions** — the table of @rules/dependency-versions.md §3
- **Gate** — the manifest hash the module was generated from, the build result, each plan's `validate` result
- **Work Remaining** — one row per `core_api` method and application-side skeleton: SQM ID, class, pattern,
  semantics to keep, owning aggregate
- **Not Generated** — redesign and retire statements with their proposal or evidence

Show SQL only as the inventory's masked text; the generated module carries the full statements.

## Completion Criteria

1. `generate_migration.py` exited 0 and `migration-summary.json` names every manifest statement
2. `gradle build` passes in the generated module, and every plan passes `residual-runner validate` or is reported
   against its statement
3. The implementation report passes both hooks and lists every skeleton as remaining work
4. `work/version-decisions.json` holds the versions the module pins

## Related Skills

- `/architect:design-sql-migration` — the manifest this skill implements; the place to fix a refused gate
- `/architect:verify-sql-migration` — golden checks and differential tests that prove the generated routes
- `/architect:generate-scalardb-code` — the domain and infrastructure layers when the migrated service is rebuilt
