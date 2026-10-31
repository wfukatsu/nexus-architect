# samples

Four self-contained projects the toolkit is exercised against. Each has its own README; this page
says what each one is for and which rules apply before touching it.

| Sample | What it is | Exercised by | Run / check |
|--------|------------|--------------|-------------|
| [`ec-monolith/`](ec-monolith/README.md) | Spring Boot + JPA EC monolith with planted technical debt and OWASP issues (README in Japanese; the reports it yields are Japanese too) | `/architect:pipeline` and `/architect:start` on the legacy path (`docs/getting-started.md`); the committed DDD reference set in `expected-reports/` backs `docs/ddd-coverage.md` | `./gradlew bootRun` after `docker-compose up -d` (MySQL); `python3 samples/ec-monolith/reference-set.test.py` |
| [`legacy-ui-shop/`](legacy-ui-shop/README.md) | Runnable JSP + jQuery shop with planted UI/UX defects; `planted-defects.json` is the answer key | `/architect:analyze-ui`, `/architect:evaluate-ux`; the committed UI reference set in `expected-reports/` | `./gradlew run`; `python3 samples/legacy-ui-shop/reference-set.test.py` |
| [`scalardb-transaction-tests/`](scalardb-transaction-tests/README.md) | Executable evidence for the `rules/scalardb-*.md` transaction rules on a real ScalarDB engine over in-process SQLite | Cited by `rules/scalardb-2pc-patterns.md`, `rules/scalardb-crud-patterns.md`, `generate-scalardb-code`, `scalardb:scaffold` | `./gradlew integrationTest` (34 tests; needs network for dependencies, so not in `tools/run-tests.sh`) |
| [`sql-migration-shop/`](sql-migration-shop/README.md) | Static PostgreSQL schema plus MyBatis / JDBC / JPA / batch SQL, each statement planted to exercise one migration decision; the README holds the answer key | `/architect:design-sql-migration`, `implement-sql-migration`, `verify-sql-migration` smoke runs | Nothing to build |

## Ground rules

- **Two of these are fixtures with deliberate defects** — `ec-monolith` and `legacy-ui-shop`. Do not
  fix, reformat or "clean up" their source: the debt is the test input, and `legacy-ui-shop` pins
  file and line numbers in `planted-defects.json` (its `reference-set.test.py` checks every line
  still points at its construct).
- **`expected-reports/` is committed skill output**, not hand-written documentation. Regenerate it
  per the sample's README when a skill or a ScalarDB bump changes an artifact's shape; the two
  `reference-set.test.py` suites (discovered by `tools/run-tests.sh`, see `docs/test-suites.md`)
  reject a stale or stray file.
- **`scalardb-transaction-tests` is real code** and may be refactored freely — as long as
  `./gradlew integrationTest` stays green, because every rule it backs was written or corrected
  when one of its tests failed.
- **One build setup.** The three Gradle projects share the same Gradle 8.6 wrapper and target
  Java 17; `build/` and `.gradle/` are ignored in each. Dependency versions are resolved per
  `rules/dependency-versions.md` and recorded in the sample's `build.gradle` or README.
