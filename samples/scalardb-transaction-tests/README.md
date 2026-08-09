# ScalarDB Transaction Tests

Executable evidence for the ScalarDB transaction rules this repository ships. Every claim in
`rules/scalardb-*.md` about how a transaction behaves is asserted here against a **real ScalarDB
engine** — not described, not reviewed, executed.

```bash
./gradlew integrationTest      # 25 tests, ~10s, no container and no external service
```

SQLite storage runs in-process, so there is nothing to start and nothing to clean up.

## Why this exists

`rules/ai-code-quality-gate.md` defines an eight-stage gate. Stages 1–3 and 8 — build, unit,
contract, conformance review — all passed on an implementation whose `cancel` operation could not
commit at all. Four rules in this repository were wrong or missing until these tests ran:

| Test | What it establishes | Rule it backs |
|------|--------------------|---------------|
| `BlindWriteProbeIT` | A `Put` with no preceding `Get` is an INSERT; on an existing record it fails at `commit()`, not at `put()`, with a *conflict* error that no retry can clear | `scalardb-crud-patterns.md` § A `Put` with no preceding `Get` |
| `TwoPhaseCommitIT` | `join(txId)` resolves within the manager it is called on, so two participants need two managers; and protocol misuse throws an **unchecked** `IllegalStateException` a `TransactionException` handler never sees | `scalardb-2pc-patterns.md` §§ One Manager Per Participant, Protocol Misuse Is Unchecked |
| `SagaCompensationIT` | A composite clustering key is one `Key` — `clusteringKey(...)` replaces rather than appends | `scalardb-crud-patterns.md` § Composite Clustering Keys Are ONE Key |
| `OrderTransactionIT` | The idempotency replay path is an authorization path: without an ownership check in that branch, a same-tenant caller holding another customer's key reads back that order's outcome | `api-error-standard.md` § The replay path is an authorization path |

Re-run this suite after a ScalarDB upgrade. If a rule's premise stops holding, a test fails and the
rule gets fixed instead of quietly going stale.

## What the two implementations are for

`ConformingOrderService` implements TX-001..TX-004 as the reference design specifies: one
transaction per operation, the ownership predicate evaluated inside the transaction that read the
order, the idempotency record written with the business write, conflicts retried before they reach
the caller, and `UnknownTransactionStatusException` neither rolled back nor retried.

`NonConformingOrderService` is the same operations with the violations a review is supposed to
catch — split transactions, a missing ownership check, an idempotency record in its own commit, a
rollback on unknown status, and blind writes. It exists so the tests can assert that the defects are
detectable, and it is **not a template**. An independent reviewer reading it reported the
authorization and transaction defects correctly and never noticed that its writes cannot commit;
that gap is the reason this suite exists.

## Scenario coverage

**OCC conflict** (`OccConflictIT`) — a stale writer loses and the winner's write survives; two
concurrent confirms serialize so exactly one succeeds and the loser fails cleanly instead of
silently double-applying; the service's own retry absorbs a conflict that clears, so no conflict
reaches the caller.

**2PC failure** (`TwoPhaseCommitIT`) — the happy path prepares every participant before any commits;
a participant whose `prepare()` conflicts forces all participants to roll back, leaving no order
committed against unreserved stock; commit-before-prepare is rejected; a partial prepare leaves
nothing behind.

**Saga compensation** (`SagaCompensationIT`) — a later step's failure compensates the earlier ones in
reverse; a compensation replayed under redelivery does not inflate stock; a step with no
compensation leaks its effect, which is what a design review must catch.

These exercise the saga **pattern** over ScalarDB local transactions. They are not ScalarDB Saga the
product (3.19.0-alpha.1), which is not a dependency here.

**Order operations** (`OrderTransactionIT`) — TX-001..TX-004 end to end, including tenant isolation,
the 404-not-403 rule for a non-owned order, and the confidential field that must not reach the
domain view.

## Not in scope

No HTTP layer, no Spring, no OpenAPI. Those belong to the contract-test tier
(`/architect:generate-contract-tests`), which asserts the shape of a response and by construction
cannot reach any of the behaviour above. This suite is stage 4 of the gate, and the point of it is
that stages 3 and 8 do not substitute for it.

## Layout

```
src/main/java/com/example/orders/
  OrderApplicationService.java   the operations under test
  ConformingOrderService.java    implements the design
  NonConformingOrderService.java implements it wrongly, on purpose
  Caller.java, OrderView.java, DraftOrderCommand.java, *Exception.java
src/test/java/com/example/orders/
  ScalarDbTestBackend.java       real ScalarDB over SQLite; two managers, for 2PC
  *IT.java                       the scenarios
```

`ScalarDbTestBackend` is the reusable piece: it boots a real engine, creates the namespace, the
coordinator tables and the order/inventory/idempotency/saga-log tables, and hands back both a
`DistributedTransactionManager` and two `TwoPhaseCommitTransactionManager`s. Point it at a different
schema to test another transaction design.
