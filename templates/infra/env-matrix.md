# Environment Matrix — Template

Used by `/infra:design`. Write the content in the project's `options.output_language`.

```yaml
---
title: "<system> Environment Matrix"
schema_version: 1
phase: "Infrastructure"
skill: infra-design
generated_at: "<ISO8601>"
input_files: []
---
```

---

# Environment Matrix — <system>

## 1. Cloud × environment grid

A blank cell means "not deployed here". It is never left implicit.

| | local | test | staging | production |
|---|---|---|---|---|
| AWS | | | | |
| Azure | | | | |
| GCP | | | | |
| Cloud-independent | ✓ (kind / minikube / …) | — | — | — |

## 2. Environment definitions

| Aspect | local | test | staging | production |
|--------|-------|------|---------|------------|
| Purpose | | | | |
| Lifecycle | | | | |
| Applied by | | | | |
| Where the declaration lives | | | | |
| State / history | | | | |
| Cloud foundation (L1) | not created | | | |
| Data | synthetic only | synthetic only | | real |
| Access | | | | |
| Change approval | none | | | |
| Availability design | none | | | |
| DR / backup | none | | | |
| Bundle coverage | **out of scope** | observed implementation | observed implementation | **no observed implementation** |

## 3. Identical across environments

| Item | How identity is guaranteed |
|------|----------------------------|
| Image digest | |
| Kubernetes base | |
| Helm chart / version | |
| Label / resource attribute names | |
| ServiceAccount names and RBAC shape | |
| Secrets never committed to Git | |

## 4. Environment differences (confined to overlays / values)

| Axis | local | test | staging | production | Reason for the difference |
|------|-------|------|---------|------------|---------------------------|
| Replicas | | | | | |
| Requests / limits | | | | | |
| Storage class / size | | | | | |
| Hostname / DNS | | | | | |
| Metric retention | | | | | |
| Log retention | | | | | |
| Trace sampling rate | | | | | |
| Alert routing | | | | | |
| Alert severity thresholds | | | | | |
| Node pool / scaling | | | | | |
| Kyverno failure action | not installed / Audit | Audit | | Enforce | |

> Pull the staging↔production differences out of the table above and list them separately,
> **each with a reason**. A difference with no reason lowers what staging proves — consider
> removing it.

### Staging ↔ production difference inventory

| # | Difference | Reason | Planned resolution |
|---|------------|--------|--------------------|

## 5. Promotion path

```
local ──▶ test ──E2E──▶ staging ──▶ production
```

| Segment | Unit of promotion | Trigger | Approval | Evidence |
|---------|-------------------|---------|----------|----------|
| local → test | | | | |
| test → staging | | | | |
| staging → production | | | | |

- What is promoted is a **digest** — not code, not a tag
- Rollback method: (Git revert / forward-fix)

## 6. Not reproduced locally (declaration)

The central deliverable of local-environment design. Keep it in a form developers actually read.

| Not reproduced | Substitute | Where it is verified instead |
|----------------|-----------|------------------------------|
| HA / failover | replica 1 | staging |
| Workload identity | | |
| Real NetworkPolicy behaviour | | |
| Signature verification / admission policy | | |
| Real database performance | | |
| Real certificate handling | self-signed | |

> "It worked locally" is not evidence of having passed any item in this table.

## 7. Open questions

| # | Item | Environment | Who decides |
|---|------|-------------|-------------|
