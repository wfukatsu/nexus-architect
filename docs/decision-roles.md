# Decision Roles

Who decides what, and who approves which gate. A pipeline run asks many questions and records
many decisions; this document names the roles those questions and decisions belong to, so that
`work/context.md` § Open Questions can say *whose* answer a `TBD` waits on, an ADR can say who
took and who approved a decision, and the audit log can say who acted (`skills/common/progress-registry.md`
§ Audit Log). The names are roles, not job titles: one person may hold several on a small
project, and a role may be a committee on a large one. The project maps roles to people in
`work/context.md` § Decisions (a short table, written once by `/architect:start` or
`/product:start` when first asked).

## The roles

| Role | Decides | Typical holder |
|------|---------|----------------|
| `product owner` | Scope in and out, priority, target numbers, which of two product designs to take, the success metrics | The business owner of the product |
| `business sponsor` | Budget, deadline, go / no-go on the riskiest assumptions, revenue model | Whoever funds it |
| `domain expert` | Business rules, terminology, the examples that define a rule, what the current process really is | A practitioner of the domain |
| `architect` | Bounded contexts, aggregates, transaction boundaries, API style, the data layer, the ADRs that depend on these | The system's architect |
| `security` | Authorization model, tenant isolation, secrets, the security findings' acceptance | Security owner |
| `operations` | SLOs, RTO/RPO, environments, the deployment and recovery procedures | Operations / SRE owner |
| `legal` | Trademark, licensing, data-protection — the `external` questions nobody in the room can answer | Legal / compliance |
| `engineering lead` | Implementation style, test strategy, merge approval of delivered code | The team lead |

## Which gate each role approves

| Gate | Where | Approver | Recorded as |
|------|-------|----------|-------------|
| Requirements baseline | `/architect:define-requirements` (its answered questions) | `product owner`, `domain expert` | `QUESTION_ANSWERED` per question; the phase `completed` |
| Riskiest-assumption verdict | `/product:validate-assumptions` | `business sponsor` (go / no-go) | `VERDICT_RECORDED` (`go` / `no-go`) |
| Design decision | an ADR (`rules/architecture-decision-records.md`) | the `deciders` take it; `approved_by` accepts it — `architect` for structure, plus the role the decision's `upstream` points at | the record itself, `ADR_RECORDED` |
| Design review verdict | `/architect:review-synthesizer` | the verdict is computed; `architect` decides whether a `CONDITIONAL_PASS` proceeds | `VERDICT_RECORDED` |
| Pull request approval | `/architect:deliver-backlog` stage (c), `/architect:merge-issue` Step 2 | `engineering lead` (and the tracker's required reviewers) | `GATE_APPROVED` / `GATE_REJECTED` / `GATE_SKIPPED` |
| Follow-up Issues | `/architect:capture-followup` Step 3 | `product owner` or `engineering lead` | `GATE_APPROVED` / `GATE_REJECTED` |

## How the roles appear in the artifacts

- **Open Questions** (`rules/open-questions.md` §6): the `Role` column names the role whose answer
  the question needs; `Owner` names the person. A skill that derives a question sets the role
  from the table above — a question about scope is the product owner's whatever the phase asking
  it. `python3 tools/lib/open_questions.py <project> by=role` lists what waits on whom.
- **ADRs** (`rules/architecture-decision-records.md` §2): `deciders` are the roles (or names) that
  took the decision; `approved_by` the names (or roles) that accepted it — required for
  `status: accepted` at `schema_version: 2`. A `proposed` record is promoted to `accepted` by
  whoever answered the `OQ-` it waits on, and the promotion writes `approved_by`.
- **Audit log**: `actor` is the git user name of the session, or the signer of a workshop sheet
  (`rules/open-questions.md` §9). The role is in the event's `detail` when it matters.
- **Workshop mode** (`rules/open-questions.md` §9): the sheet shows each question's role, so a
  room of stakeholders can see which questions are theirs.
