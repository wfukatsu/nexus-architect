# Operations: running, verifying and maintaining the SQL migration tooling

Procedures the three SQL migration skills refer to. Read a section when a step needs it.

## Environment

| Need | Setup |
|---|---|
| Conversion (no database) | `pip install -r "${CLAUDE_PLUGIN_ROOT}/requirements.txt"` — pins `sqlglot` |
| Plan validation and application-side tests | Java 17 and Gradle; `cd "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/runtime-java" && gradle installDist` builds `build/install/residual-runner/bin/residual-runner` |
| Differential test | Docker, disposable containers for the source database and ScalarDB's backend; ScalarDB Cluster and a license only for the ScalarDB SQL path |

Run the tooling from the project directory; write outputs where the calling skill says.

## Convert a script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/scripts/convert.py" <file.sql> --source oracle \
  --schema <schema.json> --storage jdbc --out-dir <dir> --plan-dir <dir>/plans
```

Exit 0: no ERROR statement; 1: at least one. Outputs `<stem>.scalardb.sql`, `<stem>.report.md`,
`<stem>.report.json`, `<stem>.schema.json` and one `<stem>.<n>.plan.json` per PLANNED statement.

## Validate a plan offline

```bash
residual-runner validate --plan <plan.json>
```

Compiles the residual SQL against empty H2 tables built from the plan's column types. Exit 1 with the
problems when H2 rejects it, or when a fetch has no column types (no schema was known).

## Capture and check golden results (application-side code)

An application-side implementation is compared with results captured once from the source database.
Capturing is the only step that needs the source database, and it runs only against a database the user
authorized, through an environment-reference profile (the same shape as `/architect:investigate-db-live`).

```bash
# once, with the source database
python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/scripts/verify/golden.py" capture \
  --profile <private/profile.json> --setup <setup.sql> --query <query.sql> --tables <t1>,<t2> --out <golden-dir>
# afterwards, no database
python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/scripts/verify/golden.py" check \
  --golden <golden-dir> --impl <fully.qualified.AppSideQueryClass> --cp <generated module classes>
```

See references/app-side-notes.md for the comparison rules.

## Run the vendored runtime's tests

```bash
cd "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/runtime-java" && gradle test
```

Needs network for dependency resolution, so it is not part of `tools/run-tests.sh`; run it after changing
the runtime or its dependency versions.

## Re-import from upstream

The procedure and the list of local changes are in `PROVENANCE.md`. Never copy upstream files over the
vendored ones wholesale: the translations and the removed components would be lost.
