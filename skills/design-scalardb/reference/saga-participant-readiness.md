# Saga Participant Readiness — section template

The section `/architect:design-scalardb` writes into `reports/03_design/scalardb-transaction.md` for every
saga, **before** the five-point saga checklist. The rule behind it is
`rules/scalardb-saga-patterns.md` § External Participants; this file fixes the shape so a reviewer can
read any project's table the same way.

## Why it comes first

ScalarDB Saga requires idempotent steps, a compensation per step and compensations that eventually
succeed. For a participant the project writes, those are design obligations the toolkit already
enforces. For an **external API** they are facts about somebody else's system, and the pivot, the
retry policy and the saga's maximum duration all follow from them. Collect the facts, then design.

## The table

One row per (step, participant). Every cell is filled; `unknown` is a value, not a blank.

```markdown
### Saga Participant Readiness — <saga name>

Saga horizon (longest duration before a terminal state, incl. retries and escalation grace): <e.g. 4 h>

| Step | Participant | Idempotency mechanism | Duplicate response | Compensation (deadline) | Outcome query | TCC decomposition | Rate limit / latency | Evidence | Disposition |
|------|-------------|-----------------------|--------------------|-------------------------|---------------|-------------------|----------------------|----------|-------------|
| charge | external: PayCo API v3 | key_header:Idempotency-Key (24 h) | same_result | exists:refund (30 days); void before capture | get:/charges/{id} | not_possible | 50 rps; p99 800 ms | https://docs.payco.example/idempotency | — (no gap) |
| ship | external: CarrierHub v2 | none | new_effect (second label) | exists:cancel-shipment (until pickup) | get:/shipments?ref= | not_possible | 10 rps | https://carrierhub.example/api | idempotency_layer |
| reserve | own: inventory-service | key_header:Idempotency-Key (design-api) | same_result | exists:release (none) | get | reserve/confirm/cancel:… | — | reports/03_design/api-specifications/inventory.yaml | — |
| notify | external: MailRelay | unknown | unknown | none | none | not_possible | unknown | OQ-017 (integration owner) | pivot_or_exclude |
```

### Column vocabulary

| Column | Values |
|--------|--------|
| Participant | `own: <service>` or `external: <provider> <API version>` |
| Idempotency mechanism | `key_header:<name> (<key lifetime>)` · `request_id_in_body` · `natural_key` (the resource ID is chosen by the caller, so a replay is a no-op) · `none` · `unknown` |
| Duplicate response | what a replayed request does: `same_result` · `conflict_409` · `new_effect` (a second charge, a second label) · `unknown` |
| Compensation (deadline) | `exists:<operation> (<deadline>)` — the window in which it is accepted · `none` · `manual` (a human process, not an API) |
| Outcome query | how the result of a call that timed out is learned: `get:<operation>` · `webhook` · `none` |
| TCC decomposition | `reserve/confirm/cancel:<ops>` when the provider has a hold-then-capture shape · `not_possible` (SAGA mode only for this step) |
| Rate limit / latency | the documented limits and latency the step's `retryPolicy` and `timeoutMillis` must respect |
| Evidence | the provider document URL at the version assessed; for `own`, the project's API contract path. A cell without evidence is `unknown` |
| Disposition | `—` when there is no gap; otherwise one of the four below |

### A gap is any of

- idempotency mechanism `none` or `unknown`, or duplicate response `new_effect` or `unknown`
- compensation `none`, `manual`, or a deadline **shorter than the saga horizon**
- outcome query `none` on a step whose forward call can time out (every HTTP call can)
- evidence missing

### Dispositions

| Disposition | Meaning | What the design must then contain |
|-------------|---------|-----------------------------------|
| `idempotency_layer` | the project makes the step idempotent itself | a request-ledger table (ScalarDB, keyed by `X-Saga-Id` + `X-Saga-Step`) written **in the same transaction** as the step's business write; the step reads the ledger first and returns the stored result on a replay; the ledger row carries the provider's response ID so the outcome query (when one exists) can reconcile. The table appears in `scalardb-schema.md` |
| `query_before_retry` | a timed-out call is resolved before it is re-sent | the outcome query named in the row; the retry policy's first action is the query; `new_effect` is tolerable only with this plus `idempotency_layer` |
| `pivot_or_exclude` | the step cannot be undone within the horizon | either the step is the saga's **pivot** (every earlier step reversible, every later step roll-forward only, stated in the checklist's item 4) or it leaves the saga for a manual exception process with an operator queue and an `ESCALATED` runbook entry |
| `accept_risk` | the business accepts the exposure | an ADR (`rules/architecture-decision-records.md`) naming the business owner, the exposure (what happens on a duplicate or an uncompensated step), its expected frequency and the manual remedy |

`unknown` at the end of the design is an `OQ-` with the integration owner as owner
(`rules/open-questions.md`), and `verify-implementation` treats the step as unproven until it is
answered. `--auto` records it `unasked`.

## Where the facts come from

1. The provider's API reference and integration guide, at the version the project will call —
   cite the URL. Search terms that find the right page: *idempotency*, *idempotent requests*,
   *duplicate*, *retry*, *refund / void / cancel*, *webhook*, *rate limit*.
2. The project's existing integration code, when it already calls the API — what it does on
   timeout today is evidence of what the provider tolerates.
3. The provider's support, when the documentation is silent — recorded as an `OQ-`, never guessed.
