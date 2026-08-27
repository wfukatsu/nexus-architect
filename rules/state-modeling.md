# State Transition Modeling

Applies whenever a skill **models, reviews, or generates code for an object that has a lifecycle**:
`/architect:design-state-machine` above all, plus the data-layer, API, test-spec, code-generation
and review skills that consume its output.

A state transition model is the answer to one question a prose design never answers precisely:
*given what this object is now, which changes are legal, who may make them, and what happens to the
attempts that are not legal?* Everything below exists to keep that answer complete rather than
plausible.

## 1. What earns a state machine

Model an object as a state machine when **all three** hold:

1. It has a named condition that changes over time and is visible to the business (`Draft`,
   `Reserved`, `Shipped`), not merely a derived flag.
2. Some operations are legal in one condition and illegal in another — the object's behaviour,
   not just its data, depends on the condition.
3. Getting an illegal change wrong has a cost: money moved twice, stock reserved for nobody, an
   audit trail that cannot explain itself.

Do **not** mint a machine for: a boolean that is only ever read (`is_active` with no guarded
transitions), a value that changes freely in any direction with no rules, or a workflow that belongs
to a human process outside the system. A machine per aggregate root is the norm; a machine per
attribute is a smell.

**One aggregate, one machine.** The state of an aggregate is the state of its root. If two parts of
one aggregate need independent lifecycles, that is evidence the aggregate boundary is wrong, or that
the second lifecycle belongs to a separate machine with its own aggregate — decide which, and record
the decision. Do not model orthogonal regions inside one machine unless the two regions genuinely
never interact.

## 2. The model

Five element types, and every one of them is named in the ubiquitous language:

| Element | Definition | Must record |
|---------|-----------|-------------|
| **State** | A named condition of the aggregate in which a specific set of operations is legal | The invariant that holds while in it, and what it permits/forbids |
| **Event** | What triggers a change — a command from an actor, an integration event, a timer | Its source: `command` \| `event` \| `timeout` \| `schedule` |
| **Transition** | `(from state, event) [guard] → to state` | Guard, effect, actor/role, consistency class, idempotency |
| **Guard** | A predicate that must hold for the transition to fire | What happens when it is false — never left implicit (§4) |
| **Effect** | The side effect the transition performs besides changing state | Whether it is transactional with the state write, or emitted after commit |

**Terminal states are declared, not inferred.** A state with no outgoing transition is either a
declared terminal state or a defect; the model says which.

## 3. Well-formedness rules

A state machine is not written out until all seven hold. Each is mechanically checkable and each is
asserted by `tools/lib/state_machine_manifest.py` against the manifest the skill emits.

1. **Exactly one initial state**, and it is reachable by creation only.
2. **Every state is reachable** from the initial state by some sequence of transitions.
3. **No undeclared dead end** — every non-terminal state has at least one outgoing transition.
4. **Determinism** — no two transitions share `(from state, event)` unless their guards are stated
   and mutually exclusive. Two unguarded transitions on the same pair are a defect, not a choice.
5. **Every guard has an else branch** — the guarded transition's failure behaviour is a row in the
   matrix (§4), not an unwritten assumption.
6. **Every transition names an actor and a consistency class** (§5). A transition nobody is
   authorized to fire, or whose transactional scope is unknown, is not designed yet.
7. **Every state and event name exists in the ubiquitous language** (`reports/01_analysis/
   ubiquitous-language.md`) — or the model proposes the addition explicitly rather than inventing a
   synonym.

## 4. The state × event matrix

The diagram shows what is legal. The **matrix shows what happens to everything else**, and that is
where the defects live. Build it with one row per state, one column per event, and **no empty
cells** — every cell carries one of four verdicts:

| Verdict | Meaning | Typical response |
|---------|---------|------------------|
| `allow` | A defined transition fires | The target state |
| `reject` | Illegal in this state; the attempt is an error | 409/422 with a registered problem type (@rules/api-error-standard.md) |
| `ignore` | Legal but a no-op — the event has already been applied | Success, unchanged state (this is what makes retries safe) |
| `defer` | Legal but not yet — the event is queued or re-delivered later | Accepted, applied on a later transition |

The `ignore` cells are the idempotency design. Deciding them by default — "a duplicate event is an
error" — is what turns an at-least-once delivery into a support ticket.

## 5. Concurrency and consistency

A transition is a **transaction**, and treating it as anything less is the failure mode this section
exists to prevent.

- **Read-check-write is one transaction.** The guard is evaluated on the state read *inside* the
  transaction that writes the new state. A guard checked before the transaction begins is not a
  guard; it is a race with a comment.
- **Concurrent transitions conflict, by design.** Under ScalarDB's optimistic concurrency control,
  two actors firing transitions from one state means one commits and one fails — that is correct.
  What must be designed is what the loser does: retry (re-reading the state and re-evaluating the
  guard, which may now `reject`), or surface a conflict. Never retry a transition without
  re-evaluating its guard. Design keys so the contended transitions do not share a partition beyond
  what the business requires (@rules/scalardb-schema-design.md).
- **Classify every transition.** `local` (one service, one datastore), `distributed` (one ACID
  transaction across services — shared cluster / Global Transaction API / 2PC), or `saga` (steps
  with compensation). The classification comes from `scalardb-transaction.md` when it exists, and
  feeds it when it does not (@rules/scalardb-2pc-patterns.md, @rules/scalardb-saga-patterns.md).
- **A compensation is a transition.** A saga that rolls back moves the aggregate to a real state —
  `PaymentFailed`, `ReservationReleased` — that appears in the model with its own row. A
  compensation that "returns to the previous state" is almost always wrong: the aggregate has been
  observed in the intermediate state, and the history matters.
- **Timeouts are transitions with a sweeper.** A state that expires names: the deadline, the state
  it expires into, who fires it (a scheduled sweeper, not the request path), and how the sweeper's
  write races with a concurrent legitimate transition — both cannot win.
- **`UnknownTransactionStatusException` is not a rejected transition.** The transition may have
  committed. The model records how the caller re-establishes the state before retrying
  (@rules/scalardb-exception-handling.md).

## 6. Persistence and history

Two decisions the model must make, because the data design cannot make them alone:

- **The current state** is one column on the aggregate root, storing the state name verbatim — not
  an ordinal, whose meaning shifts the day a state is inserted. Constrain the permitted values in
  the application, and treat the column as part of the aggregate's OCC scope.
- **The transition history** is a separate append-only record (`from`, `to`, `event`, actor,
  timestamp, correlation id) whenever any of these apply: the business asks "why is it in this
  state?", the transition moves money or goods, or an auditor will. Decide it explicitly; a history
  nobody designed is a history nobody has.

## 7. Diagrams

Use `stateDiagram-v2`, per @rules/mermaid-best-practices.md:

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Submitted: submit
    Submitted --> Approved: approve [budget_available]
    Submitted --> Rejected: approve [!budget_available]
    Approved --> Shipped: ship
    Rejected --> [*]
    Shipped --> [*]
```

- State identifiers stay ASCII/English; display labels follow `options.output_language` and are
  quoted when non-ASCII.
- Label every arrow `event [guard]` — an unlabelled arrow is an undesigned transition.
- One diagram per machine. When a machine exceeds roughly 12 states, that is evidence of state
  explosion: extract a sub-lifecycle into its own machine (§1) rather than shrinking the font.

## 8. What downstream consumes

| Consumer | What it takes |
|----------|---------------|
| `design-scalardb` / `design-data-layer` | The state column, its OCC scope, the history table, and the per-transition consistency class |
| `design-api` | Transitions become operations; `reject` cells become registered problem types; `ignore` cells become the idempotency contract |
| `generate-test-specs` / `generate-contract-tests` | Transition coverage (every `allow` fires), rejection coverage (every `reject` returns the contracted error), idempotency (every `ignore` replays cleanly) |
| `generate-scalardb-code` / `generate-api-code` | Guards enforced server-side in exactly one place — the aggregate — never in a controller and never only in the UI |
| `review-consistency` / `review-risk` | The seven rules of §3, and whether the design documents still agree with the model |

**Enforcement lives in the domain.** A state machine documented in a report and enforced in a
controller is enforced nowhere: the second caller — a batch job, another service, a support script —
bypasses it. The aggregate rejects its own illegal transitions.
