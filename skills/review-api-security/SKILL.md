---
description: |
  Review the API surface against OWASP API Security Top 10 — object- and function-level authorization,
  data exposure, injection, resource controls, tenant isolation, and transaction-boundary security.
  Runs as one perspective within the parallel design review, and with --mode=code against the
  implemented source as the security stage of the quality gate.
  /architect:review-api-security [--mode=design|code] [--source-root=<path>] [--scope=changed|service|repo].
model: opus
user_invocable: true
---

# API Security Review

## Expected Outcome

Evaluate the API surface against @rules/api-security-checks.md and output findings in JSON format.
For every GraphQL surface, also apply @rules/graphql-security-checks.md. Treat SDL field coordinates
as the operation inventory and derive annotated/runtime-wired resolvers from source rather than
trusting the contract map.

Two modes, same dimensions, different subject:

| Mode | Subject | Runs as |
|------|---------|---------|
| `design` (default) | The API specifications, gateway design, and security design | One perspective of the parallel design review, alongside consistency / operations / risk / business / scalardb |
| `code` | The implemented source tree | Stage 7 of the quality gate (@rules/ai-code-quality-gate.md), delegated from `/architect:verify-implementation` |

**The two modes are not redundant, and passing one does not imply the other.** A project can hold a
correct Zero-Trust design and ship a controller that trusts a path parameter. Design mode asks
whether the control was decided; code mode asks whether it was implemented.

## Review Dimensions

GraphQL reviews additionally cover root and nested-field authorization, authenticated tenant
predicates, DataLoader cache partitioning, depth/complexity/alias/batch/page/document limits,
production GraphiQL/introspection/schema-printer policy, safe observations, and WebSocket origin,
authentication expiry, connection limits and cleanup. Cross-tenant resolver or DataLoader access is
critical; missing executable query-cost limits on an exposed surface are major.

For every ScalarDB-backed surface, read `api-style-decisions.json` and validate the structured
`graphql_provider`, `native_exposure`, `approval`, `pinned_product`, `pinned_release`,
`contracted_edition`, `control_evidence`, and `rationale` fields against
@rules/api-style-selection.md and the pinned OKF bundle. `scalardb-native` exposure without an
`approved:<decision-id>` and evidence for authentication, authorization, audit, query limits, and
network isolation is a **critical** finding. A prose statement does not satisfy this check.

### 1. Authorization and Tenant Isolation (weight: 0.40)
- Object-level authorization: an ownership predicate per resource, evaluated against a **verified
  token claim**, before read-back and before mutation (API1/BOLA)
- Function-level authorization: the role-to-operation matrix, with administrative operations
  enumerated and enforced (API5/BFLA)
- Existence disclosure: 404 vs 403 where existence is confidential
- Authentication: independent verification in the service, not assumed from the Gateway (API2)
- Tenant isolation: origin of `tenant_id`, its path to the data layer, partition-key placement,
  and the forgotten paths — administrative endpoints, batch jobs, saga compensations, 2PC participants
- Transaction-boundary security: authorization decided inside the transaction that acts on it;
  compensations carrying the same scoping as their forward step

### 2. Data Exposure and Input Handling (weight: 0.35)
- Mass assignment: request DTO distinct from domain object and entity, mapper limited to declared
  fields (API3, write side)
- Excessive data exposure: response DTO carrying exactly the declared schema; confidential fields
  absent from responses, logs, and Problem Details `detail` (API3, read side)
- Injection: parameter binding in ScalarDB SQL/JDBC; caller input never selecting a namespace, table,
  or index; path traversal; log injection
- SSRF: allowlists on every outbound URL derived from caller input (API7)
- Third-party responses validated before they are trusted or persisted, and failures closing rather
  than opening the operation (API10)

### 3. Resource, Flow, and Configuration Controls (weight: 0.25)
- Page-size, payload-size, and cost caps; timeouts on every outbound call; bounded retries with
  backoff (API4)
- Abuse protection on sensitive business flows, and absence of enumeration oracles (API6)
- TLS/mTLS, CORS, error verbosity, management endpoint exposure, default credentials, security
  headers (API8)
- API inventory: every reachable endpoint present in the specification; deprecated versions sunset;
  non-production endpoints unreachable from production configuration (API9)

## Scoring

Each dimension scored 1-5 (5: Exemplary, 4: Good, 3: Acceptable, 2: Concerning, 1: Critical).

A dimension carrying an unmitigated **critical** finding scores at most 2 — a control that is
absent is not "acceptable with a note".

## Execution

### Step 1: Resolve mode and collect input paths

**Design mode** — glob:
- `reports/03_design/api-specifications/**` (specifications, `problem-types.md`, `operation-contracts.md`)
- `reports/03_design/api-style-decisions.json` (provider, exposure, approval, release/edition and control evidence)
- `reports/03_design/api-gateway-design.md`
- `reports/08_infrastructure/security-design.md`
- `reports/03_design/target-architecture.md`
- `reports/03_design/scalardb-schema.md` (partition-key placement of the tenant identifier)

**Code mode** — resolve the source root from `--source-root`, then `api-contract-map.json`'s
`source_root`, then the project's Output Location. Collect the controllers, DTOs, mappers,
application services, security configuration, and the same design files above as the baseline to
check against. Honour `--scope` (`changed` diffs against the base branch; default when a working
branch exists).

Record the full list of found file paths — these will be passed to sub-agents. When a design file is
missing, record it: a security review run without the security design is a weaker review and must say so.

Run `python3 tools/validate-api-style-decisions.py
reports/03_design/api-style-decisions.json` when the decision artifact exists. Any validation error
on a native GraphQL exposure becomes a critical finding; do not downgrade it to a missing-document
note or accept equivalent prose elsewhere.

### Step 2: Spawn three parallel dimension reviewers

In a **single message**, issue all three Task() calls simultaneously so they run in parallel.

**Task A — Authorization and Tenant Isolation (ASEC-1xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "API authorization and tenant isolation dimension review",
  prompt: """
You are an application security reviewer evaluating API AUTHORIZATION AND TENANT ISOLATION.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Mode: <design|code>. In design mode, judge whether the control is DECIDED and located. In code mode,
judge whether it is IMPLEMENTED at the point the design named — read the handler bodies; do not infer
a check from a method name or an annotation you have not seen on that method.

Evaluate ONLY this dimension, per rules/api-security-checks.md:
- Object-level authorization (API1/BOLA): per operation taking a resource identifier, is an ownership
  predicate evaluated against a verified token claim, before read-back and before mutation? A check
  against a client-supplied value is not a check.
- Function-level authorization (API5/BFLA): role-to-operation matrix, administrative operations
  enumerated and enforced; no operation relying on a URL-prefix convention it sits outside of.
- Existence disclosure: 403 returned where the design classified existence as confidential (should be 404).
- Authentication (API2): signature, issuer, audience and expiry verified in the service; no permissive
  fallback catching what the explicit rules missed.
- Tenant isolation: tenant identifier originating from a verified token claim, reaching the data layer
  on EVERY path including administrative endpoints, batch jobs, saga compensations and 2PC participant
  operations; part of the partition key where the schema says so; cache/idempotency/rate-limit keys
  including the tenant.
- Transaction-boundary security: authorization decided outside the transaction that acts on the data;
  compensations dropping the scoping their forward step applied; 2PC participant operations reachable
  without the coordinator's authorization context.

Severity per rules/api-security-checks.md. Cross-tenant access and a missing object-level check on a
state-changing operation are critical. Every finding must state the concrete failure scenario: the
request a caller would send and what they would get back. A finding that cannot state one is info.

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical.
A dimension with an unmitigated critical finding scores at most 2.

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Authorization and Tenant Isolation",
  "weight": 0.40,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "ASEC-1<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:line or file:section>",
      "operation_id": "<operationId, or null>",
      "owasp": "API1|API2|API5|tenant-isolation|transaction-boundary",
      "title": "<finding title>",
      "description": "<issue and its impact>",
      "failure_scenario": "<the request a caller sends and what they get back>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task B — Data Exposure and Input Handling (ASEC-2xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "API data exposure and input handling dimension review",
  prompt: """
You are an application security reviewer evaluating API DATA EXPOSURE AND INPUT HANDLING.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Mode: <design|code>. In code mode, read the DTOs and mappers themselves — a field list in a design
document is not evidence about the code.

Evaluate ONLY this dimension, per rules/api-security-checks.md:
- Mass assignment (API3 write side): request DTO that IS the domain object or the persistence entity;
  a mapper copying fields wholesale or reflectively; any mapper-writable field the request schema does
  not declare. Critical when a privileged field (role, status, price, tenantId) is reachable.
- Excessive data exposure (API3 read side): response DTO that IS the entity; a handler returning the
  domain object; any response property the schema does not declare; any field the data classification
  marks confidential appearing in a response, a log line, or a Problem Details `detail`.
- Injection: string-concatenated ScalarDB SQL/JDBC; caller input selecting a namespace, table or index
  (input as a partition/clustering key VALUE is normal and safe — do not report it); path traversal on
  file paths, object keys or resource names; unescaped caller input in logs.
- SSRF (API7): any outbound request whose URL derives from caller input without an allowlist; webhook
  or callback URLs accepted unvalidated; redirect targets from parameters. Critical where a cloud
  metadata endpoint is reachable.
- Third-party consumption (API10): upstream responses deserialized into trusted types unvalidated;
  upstream failures that fail open; upstream data persisted or returned unvalidated.

Every finding must state the concrete failure scenario. A finding that cannot state one is info.

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical.
A dimension with an unmitigated critical finding scores at most 2.

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Data Exposure and Input Handling",
  "weight": 0.35,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "ASEC-2<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:line or file:section>",
      "operation_id": "<operationId, or null>",
      "owasp": "API3|API7|API10|injection|traversal",
      "title": "<finding title>",
      "description": "<issue and its impact>",
      "failure_scenario": "<the request a caller sends and what they get back>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task C — Resource, Flow, and Configuration Controls (ASEC-3xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "API resource, flow and configuration controls dimension review",
  prompt: """
You are an application security reviewer evaluating API RESOURCE, FLOW AND CONFIGURATION CONTROLS.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Mode: <design|code>. In code mode, a limit declared in a design document but absent from configuration
is a finding, not a pass.

Evaluate ONLY this dimension, per rules/api-security-checks.md:
- Resource consumption (API4): page-size maximum present and not caller-overridable — an unbounded
  limit reaching a ScalarDB Scan is major; request payload size limits; rate limits actually configured
  and keyed to the right subject (per-account where the threat is per-account); a timeout on EVERY
  outbound call; retries bounded and backed off; cost bounds on analytics, export and report operations.
- Sensitive business flows (API6): flows the design flagged as abuse-sensitive with no corresponding
  control; enumeration oracles in signup, login or password-reset paths (differing responses or timings
  for existing vs non-existing accounts).
- Misconfiguration (API8): TLS not enforced; mTLS declared between services but absent from config;
  CORS with `*` alongside credentials or reflecting Origin; stack traces or framework error pages
  reachable; debug, actuator and management endpoints exposed without authentication; default
  credentials; missing security headers the gateway design requires.
- Inventory (API9): a reachable endpoint absent from the OpenAPI document (this is a security finding
  as well as a contract one — an undocumented endpoint is an unreviewed one); deprecated versions still
  routable with no sunset date; non-production endpoints reachable from production configuration.

Every finding must state the concrete failure scenario. A finding that cannot state one is info.

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical.
A dimension with an unmitigated critical finding scores at most 2.

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Resource, Flow and Configuration Controls",
  "weight": 0.25,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "ASEC-3<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:line or file:section>",
      "operation_id": "<operationId, or null>",
      "owasp": "API4|API6|API8|API9",
      "title": "<finding title>",
      "description": "<issue and its impact>",
      "failure_scenario": "<the request a caller sends and what they get back>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

### Step 3: Merge and write output

After all three Tasks complete, compute the weighted score:

```
weighted_score = round(0.40 × scoreA + 0.35 × scoreB + 0.25 × scoreC, 2)
```

Design mode writes `reports/review/individual/review-api-security.json`; code mode writes
`reports/09_verification/api-security-code-review.json` so the two never overwrite each other and
the synthesizer only ever consumes the design-mode result.

```json
{
  "perspective": "api-security",
  "reviewer": "review-api-security",
  "mode": "design|code",
  "scope": "<what was examined — source root and --scope, or the design file set>",
  "timestamp": "<ISO-8601 now>",
  "dimensions": [<Task A result>, <Task B result>, <Task C result>],
  "weighted_score": <computed>,
  "missing_inputs": ["<design file that was expected and absent>"],
  "summary": "<2-3 sentences: the exploitable findings first, then overall posture>"
}
```

`missing_inputs` is never omitted. A review that ran without the security design or without the API
specifications reached a weaker conclusion, and the synthesizer and the quality gate both need to
know that rather than reading the score at face value.

## Output Format

Finding ID prefix: **ASEC-**
- ASEC-1xx: Authorization and Tenant Isolation
- ASEC-2xx: Data Exposure and Input Handling
- ASEC-3xx: Resource, Flow and Configuration Controls

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-security | Input source — the control baseline |
| /architect:design-api | Input source — per-operation authorization declarations |
| /architect:review-synthesizer | Consumes the design-mode result |
| /architect:verify-implementation | Delegates the security axis to this skill in code mode |
| /architect:review-issue | Consumes code-mode critical findings as `[B]` blockers |
