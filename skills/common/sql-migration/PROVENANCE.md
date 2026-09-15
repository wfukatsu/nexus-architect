# Provenance: vendored sql-migration

The converter, runtime and verification tooling under this directory are copied from
[wfukatsu/sql-migration](https://github.com/wfukatsu/sql-migration) and translated to English.
They are vendored, not a submodule: the user chose a translated copy on 2026-09-15, so nothing here
tracks the upstream automatically.

| | |
|---|---|
| Upstream | https://github.com/wfukatsu/sql-migration |
| Commit | `c32996d` (2026-09-15; first imported at `1d2e4db`, then re-imported for upstream issues #1–#4) |
| License | MIT, Copyright (c) 2026 Wataru Fukatsu — kept verbatim in `LICENSE` |

## What was copied, and how it changed

| Here | Upstream | Changes |
|---|---|---|
| `scripts/scalardb_migrate/` (8 modules) | `scalardb_migrate/` | Code unchanged. Comments, docstrings, one help string and one cost message that cited upstream `docs/*.md` or the `sql-transpile` skill now cite `references/*.md` |
| `scripts/convert.py` | — | New: runs `scalardb_migrate.cli` by path |
| `runtime-java/` | `runtime-java/` | Local extension, not upstream: `AppSideQuery.run(tables, params)` (a default method delegating to `run(tables)`), and `GoldenCheck` decoding golden.json's `params` and passing them, so a parameterised or dynamic statement can be golden-checked (with its test in `GoldenCheckTest`). Keep both on re-import. `Bench` removed together with the `bench` sub-command in `Runner`; the `examples` package (`AreaSalesReport` and its test) removed; Javadoc in `GoldenCheck`, `Plan`, `Residual` and `OracleFunctions` that cited upstream `docs/` points at `scripts/verify/golden.py` or `references/architecture.md`; `build.gradle` re-resolved (below) without the benchmark-only Oracle, MySQL and PostgreSQL drivers |
| `references/scalardb-grammar.md` | `skills/sql-transpile/references/scalardb-grammar.md` | Translated; commands point at `scripts/convert.py` |
| `references/app-side-notes.md` | `skills/sql-transpile/references/app-side-notes.md` | Translated; golden commands moved to `references/operations.md` |
| `references/architecture.md` | `docs/architecture.md`, `docs/app-side-processing-plan.md` | Translated and condensed to what the skills need |
| `references/operations.md` | `skills/sql-transpile/references/operations.md` | Rewritten for this repository (no vendor-sync step; re-import procedure below) |
| `tests/{converter,decomposer,appside,dml_examples}.test.py` | `tests/test_{converter,decomposer,appside,dml_examples}.py` | pytest → unittest (parametrized cases become subtests), one comment translated. `test_skill_plan_dir_report_sections_and_plan_comment` exercised the `sql-transpile` entry point, which is not vendored; it is replaced by the same assertions against `scalardb_migrate.cli --plan-dir` |
| `tests/fixtures/dml/{oracle,postgres,mysql}.sql` | `skills/sql-transpile/examples/dml/` | Header and `@note` comments translated; every other line byte-identical (checked when copied) |

Deliberately not copied: the generic dialect-to-dialect transpiler (`skills/sql-transpile/scripts/generic.py`,
function catalogs, `vendor_sync.py`), `difftest/` benchmarks and experiments, `spikes/`, slides, drawio
diagrams and the investigation reports under `docs/`. None of them is on the ScalarDB migration path.
Upstream's connection profiles for `difftest/` (`difftest/sources.py`, `difftest/conf/sources/`, issue #2) are not
copied either: `scripts/verify/common.py` already takes environment-reference profiles and refuses production.

## Re-imports

| Upstream | Issue | Taken here |
|---|---|---|
| `19875ea` | #1 aggregate over an expression reported as an unsupported function | `converter.py`, `appside.py` patched verbatim; test ported to `tests/appside.test.py`; the `AGG` and `PROJECTION` rows of `references/scalardb-grammar.md` translated |
| `14991ee` | #2 hard-coded connection details in `difftest/` | nothing (see above) |
| `7970e63` | #3 H2 2.5.250, Gson 2.14.0 | already pinned here |
| `55b4ae6` | #4 no SLF4J provider | `slf4j-simple` in `build.gradle`, `src/main/resources/simplelogger.properties` (verbatim, already English), the logging note in `Runner`'s Javadoc |

The kanji in `OracleOrderingTest` is test data (the ordering of surrogate-pair characters), not prose.

## Dependency versions

Resolved 2026-09-15 per @rules/dependency-versions.md and confirmed by the user. The vendored runtime's
39 tests passed with both the upstream pins and this set.

| Dependency | Chosen | Latest stable | Upstream pin | Source | Why |
|---|---|---|---|---|---|
| `sqlglot` (Python) | 30.18.0 | 30.18.0 | 30.18.0 | https://pypi.org/pypi/sqlglot/json | the release the converter rules are asserted against; exact pin because a parser change can reclassify statements |
| `com.scalar-labs:scalardb`, `scalardb-sql-jdbc`, `scalardb-cluster-java-client-sdk` | 3.19.1 | 3.19.1 | 3.19.1 | repo1.maven.org maven-metadata.xml; `gh release list -R scalar-labs/scalardb` | newest supported line |
| `com.h2database:h2` | 2.5.250 | 2.5.250 | 2.5.250 (2.2.224 at `1d2e4db`) | repo1.maven.org maven-metadata.xml | newest stable; residual and compatibility-mode tests pass |
| `com.google.code.gson:gson` | 2.14.0 | 2.14.0 | 2.14.0 | repo1.maven.org maven-metadata.xml | newest stable |
| `org.slf4j:slf4j-simple` | 2.0.18 | 2.0.19 | 2.0.18 | repo1.maven.org maven-metadata.xml; `build/install/residual-runner/lib` | matches the `slf4j-api` 2.0.18 the runtime classpath resolves (ScalarDB's pom declares 1.7.36, overridden by a transitive 2.0.x); 2.0.19 would move the API too, for no change the runner needs |
| `org.junit:junit-bom` | 5.14.4 | 6.1.3 | 5.14.4 | repo1.maven.org maven-metadata.xml | newest 5.x; JUnit 6 is a new major not required here |
| Java toolchain | 17 | — | 17 | endoflife.date | LTS, supported; the runtime is verified on it |

## Verified equivalence

- Python: the four ported suites (78 test functions, parametrized cases as subtests) pass on sqlglot
  30.18.0, as upstream's pytest cases do on the same commit.
- Java: `gradle test` in `runtime-java/` — 37 tests after removing `AreaSalesReportTest` (2 of upstream's 39), all
  passing on the dependency set below.

## Re-importing from upstream

1. `git clone https://github.com/wfukatsu/sql-migration` and `git diff 1d2e4db..<new> -- scalardb_migrate runtime-java/src tests skills/sql-transpile/references skills/sql-transpile/examples/dml`.
2. Apply the code changes to `scripts/scalardb_migrate/` and `runtime-java/src/` keeping the edits in the table above.
3. Translate any new Japanese prose; port new tests to the unittest suites.
4. Re-resolve dependency versions per @rules/dependency-versions.md.
5. Run `bash tools/run-tests.sh sql-migration` (with `requirements.txt` installed) and `gradle test` in `runtime-java/`.
6. Update the commit, the tables and the counts in this file.
