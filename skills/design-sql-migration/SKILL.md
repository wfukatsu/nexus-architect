---
description: |
  Design the migration of an existing system's SQL to ScalarDB, statement by statement, from the analysis
  results: inventory every statement in application code, SQL files and investigated database objects, run
  the vendored SQLGlot converter with the schema, keys, storage and row estimates the analysis established,
  and decide one route per statement (ScalarDB SQL, Core API, fetch-and-H2 plan, application code, redesign,
  retire) in a validated manifest.
  /architect:design-sql-migration [target_path] [--source=oracle|postgres|mysql] [--app-root=<path>] [--sql-file=<path>] [--db-run=<path>] [--live-run=<path>] [--edition=community|enterprise_standard|enterprise_premium] [--storage=jdbc|cassandra] [--auto] [--lang=en|ja] to invoke.
  Extension tier; recommended after investigate-db-design / investigate-db-live and design-scalardb.
  Feeds implement-sql-migration and verify-sql-migration.
model: opus
user_invocable: true
---

# SQL Migration Design

## Desired Outcome

For every SQL statement the existing system runs, a decision that answers precisely: **how does this
statement run on ScalarDB, what does acting on that decision take, and what is still unproven?**

1. **SQL inventory** — `sql-inventory.json`: every statement from application code (MyBatis, JDBC, Spring
   JDBC, JPA native queries), SQL files and investigated DDL, views and routines, each with its source
   evidence, category and dynamic-SQL flags, and no stored literal. What static reading could not extract is
   counted, not dropped.
2. **Schema** — `schema.json`: the ScalarDB schema (Schema Loader JSON) the converter judged access paths
   against, with the key split recorded and justified per table.
3. **Converter verdicts** — `conversion.json`: OK / WARN / PLANNED / ERROR per statement with the findings,
   access paths and cost estimates, literals masked.
4. **Migration manifest** — `sql-migration-manifest.json`: **the canonical decision record**, one route per
   statement with its rationale and what the route requires (@rules/sql-migration.md). The validator accepts it.
5. **Design view** — `sql-migration-design.md`: the routes, the application-side work, the redesign
   proposals, the open questions and an effort picture a reader can act on.

Read @rules/sql-migration.md before Stage 1. The mechanism behind the converter is
`skills/common/sql-migration/references/architecture.md`; the grammar and finding codes are
`references/scalardb-grammar.md`; application-side semantics are `references/app-side-notes.md`.

## Invocation

```
/architect:design-sql-migration [target_path] [--source=oracle|postgres|mysql] [--app-root=<path>] [--sql-file=<path>] [--db-run=<path>] [--live-run=<path>] [--edition=community|enterprise_standard|enterprise_premium] [--storage=jdbc|cassandra] [--auto] [--lang=en|ja]
```

- `target_path` — Project directory; defaults to the current directory.
- `--source` — Source dialect. Taken from the investigation run's product when omitted.
- `--app-root` — Application source root to inventory (repeatable).
- `--sql-file` — SQL script to inventory: batch jobs, report queries, migration scripts (repeatable).
- `--db-run` — An `investigate-db-design` run whose DDL, views and routines are inventoried (repeatable).
- `--live-run` — An `investigate-db-live` run whose row estimates feed the cost estimates (repeatable).
- `--edition` — ScalarDB edition; decides whether ScalarDB SQL is available. Taken from
  `scalardb-edition-selection.md` when omitted.
- `--storage` — Storage behind ScalarDB; `cassandra` has no cross-partition scan. Taken from the
  `design-scalardb` ADR when omitted.
- `--auto` — No questions; everything the user owns becomes an `unasked` Open Question.
- `--lang` — Output language of the design view. Defaults to `options.output_language`.

## Decision Criteria

- **The analysis decides the inputs, not the converter.** Keys, storage, edition and row estimates come
  from `design-scalardb`, `select-scalardb-edition` and the investigation runs; the converter judges
  statements against them. A key split the converter defaulted from a source primary key is a proposal to
  confirm, not a design.
- **One statement, one route, with a reason.** Every inventoried statement is decided; a route without the
  payload the rule requires is not a decision.
- **`OK` means the grammar accepted it.** It is not equivalence: NULL handling, rounding, collation and
  types still differ. Say so in the rationale of every `scalardb_sql` / `core_api` route whose converter
  findings include a WARN, and leave `verification.status: pending` for `verify-sql-migration`.
- **The edition gates ScalarDB SQL.** It is Enterprise Premium (@rules/scalardb-edition-profiles.md). Under
  any other edition a convertible statement takes `core_api`; never propose a license to make a route work.
- **Dynamic SQL is a family of statements.** The converter saw one rendering. Ask which renderings exist and
  convert each before any automatic route; otherwise take `app_side`, `redesign` or `retire`.
- **Cost comes from measured estimates.** Row counts are the live run's estimates (`semantics: estimate`),
  quoted as such; a statement over its row limit or deadline is a redesign candidate, not a plan to accept.
- **Resolve, then ask, then record** (@rules/open-questions.md). Never ask what the reports already state;
  batch 1–4 questions per call with derived candidates; what stays open becomes an `OQ-` entry.
- **Read only.** The inventory reads files and investigation runs; nothing here connects to a database.

## Prerequisites

| Input | Required/Recommended | Source |
|------|---------------------|--------|
| `sqlglot` from `requirements.txt` | Required | `pip install -r "${CLAUDE_PLUGIN_ROOT}/requirements.txt"` |
| At least one of: application source root, SQL file, `investigate-db-design` run | Required | the project / /architect:investigate-db-design |
| `reports/01_analysis/database-investigation/<target>/design/<run>/` | Recommended | /architect:investigate-db-design — DDL, view and routine evidence |
| `reports/01_analysis/database-investigation/<target>/live/<run>/` | Recommended | /architect:investigate-db-live — row estimates for cost |
| `reports/03_design/scalardb-schema.md` and its ADRs | Recommended | /architect:design-scalardb — key design and storage backend |
| `reports/03_design/scalardb-edition-selection.md` | Recommended | /architect:select-scalardb-edition — whether ScalarDB SQL is available |
| `reports/01_analysis/data-model-analysis.md` | Optional | /architect:analyze-data-model — relationships behind join-heavy statements |
| `reports/03_design/aggregates/aggregate-manifest.json` | Optional | /architect:design-aggregate — transaction boundaries for rewritten writes; `AGG-` upstreams |
| `work/traceability.json` | Optional | earlier phases — `FR-` / `AGG-` nodes a statement serves |

Select investigation runs explicitly: list the runs that exist and let the user choose. Never pick the latest
run silently, and never combine a design run and a live run as if they were one baseline.

## Execution Modes

### Interactive Mode (default)

Six stages, at most two question rounds each. Record `in_progress` in `work/pipeline-progress.json`
(`plugin: architect`) before Stage 1 and `completed` with the outputs at the end (@skills/common/progress-registry.md).

**Stage 1 — Scope and target**
Resolve from the reports what they already state: source dialect and version (the investigation run's
`product` / `version`), edition, storage backend, namespace. Ask for what is missing in one batch — the
edition question states that ScalarDB SQL needs Enterprise Premium and what the Core API route costs
instead. Confirm the application roots, SQL files and investigation runs in scope.

**Stage 2 — Inventory**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/scripts/inventory.py" --source <dialect> \
  --out reports/03_design/sql-migration/sql-inventory.json \
  --app-root <root> --sql-file <file> --db-run <design-run> \
  --previous reports/03_design/sql-migration/sql-inventory.json
```

Pass `--previous` only when an inventory already exists, so statement IDs survive the re-run. Exit 2 means
problems: a stale evidence line means the DDL changed after the investigation — re-run the investigation or
pass the file with `--sql-file`; do not continue on stale input. Present the counts by origin and category,
the dynamic statements, the JPQL statements, the `unextracted` calls and the `unavailable` definitions.
Every `unextracted` call and `unavailable` object is open work in the design view.

**Stage 3 — Keys and schema**
Take the key design from `scalardb-schema.md` when it exists and write it as Schema Loader JSON for
`--schema`; otherwise the converter splits each source primary key (first column partitions, the rest
cluster). For each table, compare that split with how the inventoried statements read it: equality columns
in `WHERE`, join columns, ordering. Where the reads contradict the split, propose the alternative with its
consequence and ask. Record every override as a key hint for the next step; a change to keys or backend is an
ADR (@rules/architecture-decision-records.md).

**Stage 4 — Convert and draft**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/sql-migration/scripts/convert_inventory.py" \
  --inventory reports/03_design/sql-migration/sql-inventory.json \
  --edition <edition> --storage <jdbc|cassandra> --namespace <namespace> \
  --out-dir reports/03_design/sql-migration \
  --schema <existing-schema.json> --keys <table>=<partition,...>/<clustering,...> --live-run <live-run>
```

It writes `schema.json`, `conversion.json` and `sql-migration-manifest.draft.json`. Exit 2 lists statements
skipped because their source changed — re-run Stage 2. The draft proposes the route the rule assigns and
lists the questions a tool may not answer in `open`.

**Stage 5 — Decide**
Walk the draft with the user, grouped so each question decides many statements:

- **Dynamic statements** — show the static text with its dynamic markers; ask which renderings occur. Convert
  each rendering by writing it to a scratch SQL file under `work/sql-migration/` and running `convert.py` on
  it; record `confirmation` only when every rendering converts.
- **JPQL** — rewrite as SQL and convert, reimplement in the application, or redesign.
- **ERROR reads** — `app_side` with the helpers of `references/app-side-notes.md`, a rewrite H2 can run
  (then convert again and expect PLANNED), or `redesign` (summary table, precomputed hierarchy, ScalarDB
  Analytics).
- **Semantics to keep** — every `APP_SEMANTICS` note gets its `handling`.
- **Cost** — `ROW_LIMIT` / `COST_DEADLINE` findings: raise the limit with a reason, narrow the read, or redesign.
- **Writes** — confirm the application-side pattern and name the aggregate whose transaction owns each
  rewritten write when `aggregate-manifest.json` exists.
- **Retirement** — only with evidence (no caller in the code, a one-off script).

Replace every `proposed:` rationale with the decision and its reason, add `upstream` `FR-` / `AGG-` IDs,
remove the draft-only `status` and `open` fields, and write `sql-migration-manifest.json`.

**Stage 6 — Validate and write the view**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/sql_migration_manifest.py" <project_dir>
```

Exit 0, or every violation is resolved with the user — a violation is a defect in the decision, not in the
checker. Then write `sql-migration-design.md` (structure below), append the traceability nodes, and run both
report hooks on the view.

### Auto Mode (`--auto`)

Run Stages 2, 4 and 6 without questions, taking the edition and storage from the reports (stop with an error
when neither the flags nor the reports state them — a guessed edition changes every route). Accept the
draft's routes except: a dynamic statement proposed for an automatic route takes `app_side` instead; each
`APP_SEMANTICS` note's `handling` is `TBD (OQ-###)`; JPQL keeps the proposed `app_side`. Every such item is an
`unasked` Open Question carrying the options that would have been offered (@rules/open-questions.md §5).
Auto mode never retires a statement.

## Output

| File | Content |
|------|---------|
| `reports/03_design/sql-migration/sql-inventory.json` | The statements, their evidence and flags; `unextracted` calls, `unavailable` definitions, problems |
| `reports/03_design/sql-migration/schema.json` | Schema Loader JSON, namespace-qualified — the schema `implement-sql-migration` loads |
| `reports/03_design/sql-migration/conversion.json` | Converter verdicts, findings, access paths and cost, literals masked |
| `reports/03_design/sql-migration/sql-migration-manifest.json` | **Canonical decisions.** `implement-sql-migration` and `verify-sql-migration` read only this and the inventory |
| `reports/03_design/sql-migration/sql-migration-design.md` | The design view |

The draft (`sql-migration-manifest.draft.json`) is an intermediate file; keep it for the next run's review, but
nothing downstream reads it.

### Design view structure

```markdown
---
title: "SQL Migration Design"
schema_version: 1
phase: "Phase 3: Design"
skill: design-sql-migration
generated_at: "<ISO8601>"
input_files:
  - reports/03_design/sql-migration/sql-migration-manifest.json
---

## Summary
[statements by route and by converter status; target edition, storage, namespace; what is unproven]

## Keys and Schema
[one row per table: partition key, clustering key, indexes, source, rationale; ADR links]

## Routes
[one table per route: SQM ID, origin (path:lines, locator), category, converter status and codes, rationale]

## Application-side Work
[per statement: pattern, semantics notes and their handling, owning aggregate]

## Redesign Proposals
[per statement or group: the proposal, its consequence, the ADR when one exists]

## Coverage Gaps
[dynamic statements and their confirmations, JPQL, unextracted calls, unavailable definitions, skipped statements]

## Open Questions
[OQ- IDs from work/context.md with owner and impact]
```

Show SQL only as the inventory's masked text. Diagrams, when useful (routes by module), use Mermaid.

## Traceability

Append one node per statement to `work/traceability.json` (create it as `{ "schema_version": 1, "nodes": [] }`
when absent; never start a second graph, @docs/design.md §1.5):

```json
{ "id": "SQM-004", "type": "sql_statement", "title": "OrderMapper#findByCustomer",
  "skill": "design-sql-migration",
  "source_file": "reports/03_design/sql-migration/sql-migration-manifest.json",
  "upstream": ["FR-012", "AGG-002"] }
```

`SQM-` IDs are minted only by the inventory, which keeps them across runs; on a re-run, a node that already
exists is updated in place, and a node whose statement left the inventory is removed together with its
manifest entry.

## Completion Criteria

1. `sql-inventory.json`, `schema.json`, `conversion.json` and `sql-migration-manifest.json` written under
   `reports/03_design/sql-migration/`, and the inventory reports no problems
2. `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/sql_migration_manifest.py" <project_dir>` exits 0
3. Every `unextracted` call, `unavailable` definition and unconfirmed dynamic statement appears under Coverage
   Gaps, with an owner for each
4. `sql-migration-design.md` passes both report hooks and shows no unmasked literal
5. `SQM-` nodes appended to (or updated in) `work/traceability.json`; key or backend changes recorded as ADRs

## Related Skills

- `/architect:investigate-db-design`, `/architect:investigate-db-live` — the database evidence this skill reads
- `/architect:design-scalardb`, `/architect:select-scalardb-edition` — keys, storage and edition
- `/architect:implement-sql-migration` — generates code from the manifest
- `/architect:verify-sql-migration` — proves the routes on data and records the verification states
- `/architect:migrate-database` — schema-level migration reports for Oracle / MySQL / PostgreSQL
