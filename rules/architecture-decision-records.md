# Architecture Decision Records

Applies to every architect design skill that **decides** something a later phase, a backlog item or
shipped code will depend on: `redesign`, `design-microservices`, `design-scalardb`,
`design-data-layer`, `design-api`. Each of them already makes such decisions — a context boundary,
a relationship pattern, a service split, a cross-service transaction mechanism, CQRS / Event
Sourcing adoption, an API style — and each already records them somewhere: a prose section of its
own report, `work/context.md` § Decisions, `api-style-decisions.json`. What was missing is the one
place a reader (or `review-consistency`) can see **all** of them, with the alternatives that were
rejected and why. That place is `reports/03_design/adr/`.

## 1. What earns an ADR

A decision earns a record when **all three** hold:

1. It chooses between at least two viable alternatives — a fact ("the legacy DB is MySQL 8") is
   not a decision, and a decision with one option is a constraint (record it in `constraints.md`).
2. Reversing it later would rewrite an artifact downstream of the skill that made it.
3. It is not already a machine-readable decision record of its own. `api-style-decisions.json`
   (@rules/api-style-selection.md) is one; its ADR **links** to it and states the rationale at the
   surface level, it does not restate the per-surface table.

Typical records per skill — **illustrative, not exhaustive**: the three-part test above decides,
and a decision that passes it (an outbox pattern, the placement of a migration stage) earns a
record whether or not this table names it. **The skill that decides first writes the record.** A
later skill that finds the decision already taken — in an ADR, or in a downstream document from
an earlier run — cites that record instead of writing a second one; when no record exists yet
because the deciding skill ran before ADRs did, the first skill to touch the decision writes it,
with `skill:` naming itself and the Context section naming where the decision was actually taken.

| Skill | Decisions it records |
|-------|----------------------|
| `redesign` | each bounded-context boundary that differs from the current code; each context relationship pattern (ACL, OHS/PL, Customer/Supplier, Conformist, Shared Kernel) |
| `design-microservices` | the service split and its granularity; the cross-service transaction mechanism (shared cluster / Global Transaction API / application 2PC / Saga); synchronous vs. event-driven integration per edge |
| `design-scalardb` / `design-data-layer` | ScalarDB edition, storage backend, partition-key strategy; CQRS adoption; Event Sourcing adoption |
| `design-api` | the API style per surface (linking `api-style-decisions.json`); the error standard |

## 2. Record shape

One file per decision, `reports/03_design/adr/adr-NNN-<slug>.md` (`NNN` = the `ADR-` number,
zero-padded to three digits; `<slug>` kebab-case), MADR-style. The frontmatter is the
machine-readable part and is what `tools/lib/adr_records.py` validates:

```markdown
---
id: ADR-003
title: "Inventory reservation is a separate aggregate from stock"
status: accepted
skill: redesign
decided_at: "2026-08-28"
upstream: [CTX-002, AGG-002, NFR-004]
supersedes: []
schema_version: 1
---

## Context

What forces are in play — the requirement, the constraint, the evaluation finding.

## Decision

One paragraph, in the active voice: "We will …".

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Reserve by decrementing the stock counter directly | No idempotency key; a retried request over-reserves |

## Consequences

What becomes easier, what becomes harder, what a later phase must now do (name the skill).
```

Field contracts:

| Field | Rule |
|-------|------|
| `id` | `ADR-###`, unique across the directory, and equal to the `NNN` in the file name |
| `title` | Present |
| `status` | `proposed` \| `accepted` \| `superseded` \| `deprecated`. `proposed` is the status of a decision the skill must record but the project has not settled — the ScalarDB edition while its `OQ-` is open — and names the `OQ-` (or the evidence) whose answer promotes it to `accepted` in the Decision section. A skill that needs the decision reads a `proposed` record as the working assumption, not as settled |
| `skill` | The architect skill that wrote it |
| `decided_at` | ISO 8601 date the decision was **taken** — for a record written retroactively (the deciding skill ran before ADRs existed), the date of the document that took it, with the Context section saying the record was written later |
| `upstream` | **Non-empty.** What drove the decision: traceability nodes — a `CTX-`, `FR-`, `NFR-`, `TECH-`, `ARCH-` or another `ADR-` — **that exist in the graph when the record is written** (a `redesign` record cannot cite an `AGG-`, which `design-aggregate` mints later; name the context and the requirement instead). On the legacy path, where `investigate` / `analyze` / `evaluate-*` mint no nodes, cite the report that states the finding as a `reports/...` path (`.md`, or the `.json` of a review finding), optionally with a `#anchor` in any script — Japanese headings included (no whitespace or comma; the anchor is **not** resolved against the document's headings, so name the section in the Context section too). An answered `OQ-` from `work/context.md` is also a valid driver — it is checked against the store, not the graph. Do not pad with a node that did not drive the decision just to have an id. A decision that cites nothing is a preference, not a record |
| `supersedes` | `ADR-` ids this record replaces; every one must exist and carry `status: superseded` |

Body headings are fixed — `Context`, `Decision`, `Alternatives considered`, `Consequences` — so
the index can be regenerated and reviewers know where to look. Write the body in the project's
`output_language`; keep the frontmatter keys and every ID in English.

## 3. The index

`reports/03_design/adr/index.md` is a **view** regenerated from the frontmatter whenever a record
is added or changed — never edited as a source. One row per record, in ID order:

| ID | Title | Status | Skill | Decided | Upstream |
|----|-------|--------|-------|---------|----------|

The validator checks every record appears in the index and the index names no record that does not
exist. The index is a `reports/` Markdown file, so it carries the standard frontmatter
(`title`, `schema_version: 1`, `skill`, `generated_at`) with `skill` naming the skill that
regenerated it last — several skills write records, and the index belongs to none of them.

An ADR record's frontmatter is the shape in §2, **not** the standard output frontmatter of
@rules/output-conventions.md (no `phase` / `generated_at` / `input_files`): a record is a decision
log entry, and `decided_at` + `upstream` are its provenance. The hooks accept both shapes.

## 4. Allocation and traceability — the additive contract

Five skills write into one directory, so the rules are the ones `work/traceability.json` and the
Open Questions store already follow:

- **Allocate `ADR-` as `max + 1` over the graph.** Read every `ADR-` node in
  `work/traceability.json` (and every file in the directory), take the highest number, continue.
  Never number from your own report, and never re-mint a number: a record that was deleted or
  moved leaves its `ADR-` node in the graph, which is what keeps the next allocation above it.
- **Append one node per record** to `work/traceability.json`:
  ```json
  { "id": "ADR-003", "type": "decision", "title": "…", "skill": "redesign",
    "source_file": "reports/03_design/adr/adr-003-reservation-aggregate.md",
    "upstream": ["CTX-002", "AGG-002", "NFR-004"] }
  ```
  `upstream` here carries the traceability ids of the frontmatter `upstream`; the `reports/`
  paths go into a `sources` list on the node. A legacy-path record whose drivers are all reports
  therefore has an **empty `upstream` and a non-empty `sources`** — the same shape as the
  physical-only nodes of @docs/design.md §1.5, and the graph's way of saying "architect-
  originated, grounded in a report". It is not the empty-`upstream` defect: the frontmatter,
  which the validator checks, is still non-empty.
- **Never rewrite another skill's record.** A later skill that disagrees writes a new record with
  `supersedes: [ADR-old]` and sets the old one's `status: superseded` — the only field another
  skill may touch. The same restraint applies to another skill's *design document*: when a record
  contradicts one (the document rests on a fact the record corrects), say so under Consequences
  naming the document and the skill that owns it — that is a `review-consistency` finding and a
  re-run of the owning skill, not an edit from here.
- **The prefix is registered once.** `redesign` declares `id_prefix: [ADR-]` in
  `skills/common/skill-dependencies.yaml` because it is the first skill in the pipeline that
  writes one; the other four append under that registration. This is the same shape as `NFR-`
  across the product/architect boundary (@docs/design.md §1.5), inside one manifest.

## 5. Verification

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/adr_records.py" <project_dir>   # exit 1 on violations
```

`review-consistency` runs it and treats every violation as a finding. `adapt-change` reaches `ADR-`
nodes through the graph like any other architect-owned node and reports them rather than
rewriting them (@docs/design.md §7.5).
