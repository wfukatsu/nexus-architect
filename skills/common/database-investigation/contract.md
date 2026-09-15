# Database investigation contract

The two entry skills share `inventory.schema.json`, the explicit `adapters/registry.json`,
`scripts/core/` and output generation. Only the selected driver is imported when connecting.
The CLI itself is portable standard-library Python; install a product driver only for live runs.

## Helper invocation

`scripts/investigate.py <mode>` writes one run directory and prints its path.

| Option | Mode | Default | Meaning |
|---|---|---|---|
| `--product` | design | required | Registered adapter ID |
| `--schema` | design | required | Exact schema/owner spelling (after the dialect's identifier folding) |
| `--target-id` | design | required | Safe path component naming the investigated database |
| `--input` | design | required | One or more `.sql` files, each at most 10 MB |
| `--version` | design | unset | Known source version, recorded as-is |
| `--profile` | live | required | JSON profile of environment references (see the live skill) |
| `--output-root` | both | `reports/01_analysis/database-investigation` | Root of `<target-id>/<mode>/<run-id>/` |
| `--run-id` | both | random hex | Safe path component; an existing run directory is never overwritten |
| `--limit` | both | 10000 | Rows per query, 1–100000 (live only has an effect) |
| `--budget` | both | 120 | Collection budget in seconds, 1–3600 (live only has an effect) |
| `--lang` | both | project `output_language`, else `en` | Report language: `ja` or `en` |

## Identity and evidence

Objects use a JSON tuple ID `[catalog, schema, kind, name]`, preserving spelling. `null`
catalog means the source did not establish one. Columns keep order, native type and nullable
state (`null` means unknown — including a column whose attributes the parser stopped reading
before it could see a NOT NULL). Constraints are ordered column lists; FK targets retain schema,
name and ordered columns, plus `on_delete` / `on_update` when declared. An unresolved target is
not removed. Engine-specific details live in `extensions`. Function signatures and, where the
adapter declares `index_scope: table`, table-qualified index names (`<table>.<index>`) avoid
product-specific collisions — the same in design and live mode.

File evidence records SHA-256 and inclusive line ranges; no source bodies are copied. Query
evidence records the registered query ID, scope and UTC collection time. Each collection and
object references existing evidence IDs. Nested members inherit the object's evidence unless
they declare their own. Source path/hash must be checked against the actual supplied file when
an agent adds a finding; syntactic JSON validation cannot prove the truth of a citation.

`statistics` retain value (including 0 or null), unit, metric, granularity, semantics
(`estimate`, `measured`, `cumulative`), collection time, available update/reset times. Do not
convert null to zero. A row may narrow the query's granularity (`partition` among `table`
rows), so partitions are never counted as tables. Oracle dictionary dates may lack timezone
information: preserve the native timestamp without assigning a timezone. The query capture time
is always UTC.

## Collection status

| Status | Meaning |
|---|---|
| ok | Collected visible rows |
| empty | Succeeded with nothing in scope: no visible rows, a statement outside the requested schema, or a session/ownership statement with no structure |
| permission_denied | Access was explicitly denied |
| unsupported | Syntax or capability is outside implemented coverage |
| disabled | Collection feature is disabled |
| timeout | Collection deadline or query timeout |
| error | Unclassified failure; includes ambiguous inaccessible/nonexistent objects and duplicate definitions |
| not_collected | In scope but not collected, with a reason (a name-resolution change, an owner that differs only by letter case, an owner-only view) |

One statement or query has one status, the most severe outcome it met
(`ok` < `empty` < `not_collected` < `unsupported` < `error`), and `reason` belongs to that status.

**Withheld is not a gap.** Default expressions, check expressions, comment text and routine/view
definitions are omitted by policy. They are listed in the record's `withheld` array
(`default_expression`, `check_expression`, `comment_text`, `definition`) and do not change its
status: a table whose only omission is a DEFAULT is `ok`. Dependencies of views and routines are
not analyzed; read their evidence lines when a finding needs them.

`row_count` counts returned rows (design: objects read from the statement), never business table
cardinality. `truncated` marks a query whose extra sentinel row proves the row limit was reached.
A run is `partial` when any status is other than `ok`/`empty`, any query is truncated, or any
finding exists (`unresolved_reference`, `duplicate_definition`, `schema_case_mismatch`). Exit 0:
complete automated subset; 2: partial; 1: fatal. Completion does not mean all possible DB objects
or clauses were analyzed.

Connection timeout is 10 seconds; each query has a 15-second configured deadline and the
collection loop a default 120-second budget. Network/driver cleanup can extend wall-clock
time (MySQL finite socket timeouts also apply). This is not a hard process-level SLA. Drivers
implement server statement deadlines or Oracle call timeout. Do not claim the budget is a
hard upper bound or that all disconnects prove the server stopped instantly.

## Validation and reports

The CLI runs `core.output.validate` for semantic checks before writing. For the full published
schema, use `jsonschema` in the validation environment:

```python
import json
from pathlib import Path
from jsonschema import validate
validate(json.loads(Path("<run>/inventory.json").read_text()),
         json.loads(Path("<plugin>/skills/common/database-investigation/inventory.schema.json").read_text()))
```

Do not claim JSON Schema validation when only the standard-library semantic checks ran.
Run `hooks/validate-frontmatter.sh <report>` and `hooks/validate-mermaid.sh <report>` for each
Markdown report, including the skill's evidence-backed review. Generated reports carry the
output-convention frontmatter (`title`, `schema_version`, `phase`, `skill`, `generated_at`,
`input_files`); a live run lists no input file, since its profile is private. Reports use the
selected language; machine field/status names remain stable. Diagram aliases avoid injecting SQL
identifiers into Mermaid syntax; the adjacent table maps aliases back to names. Large schemas use
multiple diagrams, and cross-page edges remain in JSON. Multiplicities are unassessed,
deliberately broad.

## Add an adapter

1. Add `adapters/<id>/adapter.json` with `id`, unquoted identifier `fold`, `min_major`, a
   single-SELECT `probe` returning product/version/catalog (and optionally
   `compatible_product`, non-null on a compatible fork), and ordered scoped query definitions.
   Optional capabilities: `compatible_markers` (substrings of the probe's product/version that
   identify a compatible product to reject), `index_scope: table` (index names are table-local),
   `inline_indexes: true` (the dialect declares indexes inside CREATE TABLE).
2. Add `scripts/adapters/<id>.py` exposing `connect(config) -> Port`. The port returns bounded
   dictionaries from `query(spec, schema, limit, timeout)` and implements `close()`.
   Product-specific setup/SQL/binding stays here, not in the shared collector.
3. Declare optional dependencies and official evidence/privileges/limitations in `reference.md`.
   SQL aliases match existing normalized fields. Extend `core.live.normalize` only for a new
   shared concept, not for a product name. Design parsing shares a bounded grammar; a new dialect
   can provide `parse_design(paths, spec, schema)` in its registered module when needed.
4. Register the ID to its same-package module folder in `registry.json`; never accept module
   paths from a connection profile. Add DDL fixtures and query-row examples plus real-engine tests.
5. Run `tools/run-tests.sh database-investigation`. `contract.test.py` loads a fourth temporary
   adapter without editing the core. Real DB tests are explicit `tests/integration.py` runs,
   not part of the offline runner. They initialize ONLY the disposable integration containers.

The initial coverage is tables, columns, PK/FK/UNIQUE/CHECK, indexes, named views/routines/
triggers and selected statistics. Offline, the reader also accepts the shapes the standard dump
tools emit: pg_dump's `ALTER TABLE ONLY ... ADD CONSTRAINT`, `CREATE INDEX ... USING <method>`,
session `SET` / `set_config` and `OWNER TO` statements; mysqldump's inline `KEY` / `UNIQUE KEY`;
DBMS_METADATA's `EDITIONABLE` blocks. Routine bodies, defaults, check expressions, comments,
partition topology and vendor options may require manual source review. All supported versions
must be distinguished from versions actually tested. No migration adapter has been replaced.
