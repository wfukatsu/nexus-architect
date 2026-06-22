# Rules: Architecture Synthesis & Technology Fitness (design-architecture)

Reference for `/product:design-architecture`. Synthesize the accumulated design (bounded contexts,
API layers, data model, NFRs) into a coherent **runtime architecture**, then assess the **fitness of
a standing set of platform technologies** and emit an adoption decision with rationale for each.

The architecture is a *synthesis*, not new invention: every node in every diagram must map to an
existing `CTX-`/`API-`/`ENT-`/`NFR-` id. If a diagram needs a component that no artifact justifies,
that is a gap to flag — do not invent capability.

## Part 1 — Architecture diagrams (Mermaid, traceable)

Produce **three complementary views** (use the ones the project's artifacts support; note any skipped):

1. **Runtime / container view** (`flowchart`) — external actors & systems → edge/ingress →
   Experience APIs → Process APIs → System APIs → data stores. Group by bounded context and tag each
   node Core / Supporting / Generic (from `domain-map.md`). Show the principal data flows and any
   inline/critical paths. This is the primary deliverable.
2. **Critical-path view** (`sequence`) — the single most differentiating or highest-risk request
   flow (e.g. an inline enforcement path, a checkout saga). Make latency/failure modes explicit.
3. **Deployment / scaling view** (table or `flowchart`) — how the contexts map to deployable
   services (honor any microservice/monolith constraint), and the scale characteristics that differ
   per service (throughput vs. low-latency vs. durable). Tie each to its governing `NFR-`/`SLO-`.

Diagram discipline:
- Color by subdomain tier; keep labels terse; use `<br/>` for line breaks in node labels.
- Mark differentiators (★) and failure-mode defaults (e.g. fail-open) inline.
- Every component traces to an id; list the trace mapping below the diagrams.
- Record `TBD` where an upstream artifact left a boundary or number undecided (don't paper over it).

## Part 2 — Technology fitness assessment (evidence-driven)

Assess a **standing checklist** of platform technologies against the project's *own* artifacts.
Fitness is read out of signals already in the design — never from vibes. For each technology emit:

- **Fitness**: High / Medium / Low / None
- **Triggering signals** found (cite `NFR-`/`CTX-`/`ENT-`/`API-`/`CON-`/`SCP-` ids)
- **Decision**: Adopt / Conditional / Reject
- **Rationale**: why, and *where it slots into the architecture* (which layer/context) if adopted;
  if rejected, what existing artifact makes it unnecessary
- **Conditions / risks**: what must be true (open questions, `TBD`s) for a Conditional to become Adopt

The standing checklist (assess all four every run):

### Kong (API Gateway)
- **What**: cloud-native API gateway / ingress; plugins for authN/Z (OIDC, JWT, key-auth, ACL),
  rate limiting, mTLS, request transformation, traffic control (canary), and edge observability.
- **Adopt-when signals**: an Experience/Process API layer with **multiple consumers/channels**;
  cross-cutting edge concerns (auth, rate limit, quota, mTLS) that shouldn't live in each service;
  an external IdP to terminate (OIDC); partner/public API surface; a microservice fleet needing one
  ingress. Maps to the **edge in front of Experience APIs**.
- **Reject-when**: a single service / no external consumers; a managed gateway already mandated by a
  constraint; the API surface is internal-only and trivial.

### ScalarDB (universal transaction manager)
- **What**: a universal transaction manager giving **ACID transactions across multiple/heterogeneous
  databases and across microservices** (incl. two-phase commit), abstracting polyglot backends under
  one transactional API. Editions: Core (OSS) / Enterprise (Cluster).
- **Adopt-when signals**: a **microservice constraint** (`CON-` microservices) with invariants that
  span **multiple aggregates/contexts**; **polyglot persistence**; a need for strong consistency that
  would otherwise force fragile **sagas**; cross-service transactional writes visible in `api-design`
  (a Process API mutating several System APIs atomically). Maps to the **System layer / data access**.
- **Reject-when**: a single datastore with no cross-service transaction; a purely append-only /
  event-sourced model where eventual consistency is acceptable everywhere.
- **Note**: if adopted, flag whether `select-scalardb-edition` / `design-scalardb` (architect plugin)
  should follow — this is the bridge to nexus-architect's ScalarDB pipeline.

### ScalarDB Analytics
- **What**: analytical (HTAP) query layer over ScalarDB-managed data — federated analytics/reporting
  across the operational stores without a separate ETL into a warehouse.
- **Adopt-when signals**: analytics/reporting/metering requirements that **span contexts** (e.g.
  usage metering for a North Star/billing metric, compliance reporting across operational data,
  cross-entity dashboards) where standing up a separate warehouse is premature. Presupposes ScalarDB
  fitness ≥ Medium. Maps to a **read/analytics plane** beside the transactional stores.
- **Reject-when**: no analytical workload; a dedicated warehouse/lake already in scope; analytics are
  single-context and trivially served by the operational store.

### ScalarDL (tamper-evident ledger)
- **What**: Byzantine-fault-detection middleware — a **tamper-evident, digitally-signed ledger** with
  execution verifiability/finality; detects unauthorized data changes (non-repudiation).
- **Adopt-when signals**: requirements for **tamper-evidence / integrity / non-repudiation / verifiable
  audit trail** (`NFR-` integrity, an append-only `ENT-` audit ledger, a `SCP-` tamper-proof evidence
  capability, regulated-data retention). Maps to the **audit/ledger context**, replacing or backing a
  hand-rolled hash-chain.
- **Reject-when**: no integrity/audit/non-repudiation requirement; ordinary CRUD durability suffices.

### Extending the checklist
The four above are mandatory. Add project-relevant candidates when the artifacts clearly call for a
category not covered (e.g. a message broker, a vector store) — same evidence-driven format. Never pad
the list with technologies no signal supports.

## Discipline
- **Evidence over enthusiasm.** A High fitness must cite ≥1 concrete artifact id. No citation → Low/None.
- **Decisions are reversible inputs.** Record rationale so `adapt-change` can revisit when NFRs/scope move.
- **Honor constraints.** A technology that violates a `CON-` (e.g. managed-only) is Conditional/Reject
  with the conflict named.
- **Never fabricate adoption.** "Reject" with a reason is a valid, valuable output.

## ID convention & handoff
`ARCH-` for architecture views/components, `TECH-` for technology-fitness decisions; append to
`work/traceability.json` with Upstream `CTX-`/`API-`/`ENT-`/`NFR-`/`CON-`/`SCP-` references. A
ScalarDB/ScalarDL **Adopt** is the bridge to the **architect** plugin
(`/architect:select-scalardb-edition`, `/architect:design-scalardb`, `/architect:design-scalardb-analytics`).

## Sources
- MuleSoft API-Led Connectivity; Kong Gateway documentation (gateway/plugin model)
- Scalar Inc. — ScalarDB (universal transaction manager), ScalarDB Analytics (HTAP), ScalarDL
  (tamper-evident, Byzantine-fault-detection ledger)
- DDD context mapping (architecture-as-synthesis of bounded contexts)
