# Database investigation contract

The two entry skills share `inventory.schema.json`, the explicit `adapters/registry.json`,
`scripts/core/` and output generation. Only the selected driver is imported when connecting.
The CLI itself is portable standard-library Python; install a product driver only for live runs.

## Identity and evidence

Objects use a JSON tuple ID `[catalog, schema, kind, name]`, preserving spelling. `null`
catalog means the source did not establish one. Columns keep order, native type and nullable
state (`null` means unknown). Constraints are ordered column lists; FK targets retain schema,
name and ordered columns. An unresolved target is not removed. Engine-specific details live in
`extensions`. Function signatures / table-qualified index names avoid product-specific collisions.

File evidence records SHA-256 and inclusive line ranges; no source bodies are copied. Query
evidence records the registered query ID, scope and UTC collection time. Each collection and
object references existing evidence IDs. Nested members inherit the object's evidence unless
they declare their own. Source path/hash must be checked against the actual supplied file when
an agent adds a finding; syntactic JSON validation cannot prove the truth of a citation.

`statistics` retain value (including 0 or null), unit, metric, granularity, semantics
(`estimate`, `measured`, `cumulative`), collection time, available update/reset times. Do not
convert null to zero. Oracle dictionary dates may lack timezone information: preserve the
native timestamp without assigning a timezone. The query capture time is always UTC.

## Collection status

| Status | Meaning |
|---|---|
| ok | Collected visible rows |
| empty | Query succeeded with no visible rows |
| permission_denied | Access was explicitly denied |
| unsupported | Syntax or capability is outside implemented coverage |
| disabled | Collection feature is disabled |
| timeout | Collection deadline or query timeout |
| error | Unclassified failure; includes ambiguous inaccessible/nonexistent objects |
| not_collected | Deliberately omitted (with reason) |

`row_count` counts returned rows, never business table cardinality. `truncated` marks a
query whose extra sentinel row proves the row limit was reached. `partial` includes any
non-ok/non-empty status, truncation or unresolved findings. Exit 0: complete automated subset;
2: partial; 1: fatal. Completion does not mean all possible DB objects or clauses were analyzed.

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
Markdown report, including the skill's evidence-backed review. Reports use the selected language;
machine field/status names remain stable. Diagram aliases avoid injecting SQL identifiers into
Mermaid syntax; the adjacent table maps aliases back to names. Large schemas use multiple
diagrams, and cross-page edges remain in JSON. Multiplicities are unassessed, deliberately broad.

## Add an adapter

1. Add `adapters/<id>/adapter.json` with `id`, unquoted identifier `fold`, `min_major`, a
   single-SELECT `probe` returning product/version/catalog, and ordered scoped query definitions.
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
triggers and selected statistics. Routine bodies, defaults, check expressions, comments,
partition topology and vendor options may require manual source review. All supported versions
must be distinguished from versions actually tested. No migration adapter has been replaced.
