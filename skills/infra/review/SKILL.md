---
description: |
  Review existing infrastructure code or a design document against the OKF k8s/tf bundle and
  return severity-ranked findings. Checks ownership overlap, image digest continuity and secret
  exposure first, and always includes a multi-cloud and an environment-parity section.
  /infra:review [target] [--env=<env>] [--cloud=<cloud>] [--round=<n>] to invoke.
  Use for "review this infrastructure", "IaC review", "look at this Terraform". For reviewing a
  GitLab MR as a review write-up, use gitlab-review.
model: opus
user_invocable: true
---

# Infrastructure Review

## Desired Outcome

A review a team can act on: an ownership map, findings ranked by severity, each written as
**path:line → what → impact → fix → source**, plus a mandatory multi-cloud section and a mandatory
environment-parity section — and the things that genuinely cannot be judged from outside listed as
open questions rather than guessed at.

## Decision Criteria

| Situation | Do this |
|-----------|---------|
| The environment is unknown | Ask before writing findings. The same code gets a different verdict per environment (§ Per-Environment Standards) |
| The finding concerns `local` or `production` | Both are outside the observed implementation. Ground the finding in this skill's conventions or in official documentation — **never in the bundle's authority** |
| The repository and the bundle differ | The repository is what exists. The bundle is a snapshot of specific commits; do not assert "it should look like this" without reading the code |
| The topic is outside the bundle | Say so, then WebFetch official documentation or record it as an open question |
| A finding has no proposed fix | It is not finished. Do not emit findings without fixes |

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| `knowledge/okf-k8s-tf/` | **Required** | Vendored bundle (@rules/okf-k8s-tf-bundle.md) |
| The review target (repository / MR diff / design document, with revision) | **Required** | The user |
| Previous round's review report | Recommended | `$OUT/reviews/review-<target>-r<n-1>.md` |

When invoked from `/infra:start`, environment, cloud, target path and `$OKF` arrive already
settled. **Do not re-ask them.**

## Steps

1. **Fix the target and its scope** — whole repository / a specific MR diff / a design document.
2. **Confirm the target environment.** Always devote one section to environment parity; the
   standards differ per environment.
3. **Confirm the target clouds.** Always devote one section to multi-cloud.
4. **Build the ownership map first.** Without knowing who applies what, the remaining findings
   cannot be prioritized [architecture/platform-architecture.md].
5. **Work through the checks below**, opening the relevant bundle document before each.
6. **Assign severity**, remembering it moves with the environment.
7. **Emit with `templates/infra/review-report.md`.**
8. Round 2 and later: open with a reconciliation against the previous round — resolved / still
   open / new. Determine the round number from the existing files unless `--round=<n>` says
   otherwise.

## The Three Checks That Come First

Check these in order; anything found here is written before every other finding.

1. **Ownership overlap** — is any resource managed by two or more of Terraform / Argo CD / CI /
   manual operation? [architecture/platform-architecture.md]
2. **Broken artifact identity** — do build / scan / sign / verify / deploy all reference the same
   image digest, with no re-resolution from a tag in between? [delivery/docker-cosign.md]
3. **Secret exposure** — any plaintext secret in Git / values / tfvars / plan artifacts / CI logs /
   Docker layers? [foundation/terraform.md, delivery/docker-cosign.md]

## Checks by Area

Walk every item of `architecture/design-build-checklist.md`. Below is that list plus the points
worth digging into.

### Requirements and boundaries
- [ ] Are availability / RTO / RPO / performance / retention / budget / regulatory and residency
      constraints expressed as numbers?
- [ ] Are test / staging / production separated by purpose, data, access and change approval?
- [ ] Are failure boundaries defined (namespace, cloud account/subscription/project, state)?

### IaC [foundation/terraform.md]
- [ ] Terraform / provider / module / chart versions pinned, lock file committed
- [ ] Remote state encrypted, access-controlled, locked, versioned/backed up
- [ ] CI runs `fmt` / `validate` / plan / static analysis; apply restricted to protected refs
- [ ] Plan and apply use different roles; OIDC rather than long-lived access keys
- [ ] Procedures exist for destroy / import / state move / provider upgrade
- [ ] Sharing between states limited to a minimal set of outputs
- [ ] `-target` not baked into normal operation
- [ ] Modules have not become giant lowest-common-denominator conditionals (over-abstraction)

### Kubernetes [foundation/kubernetes.md]
- [ ] Requests / limits, probes, PDBs, multiple replicas, topology spread
- [ ] RBAC and workload identity least-privileged per namespace / ServiceAccount
- [ ] Use of `cluster-admin`, wildcard verbs/resources, default ServiceAccount tokens
- [ ] Pod Security, NetworkPolicy (starting from default deny), staged admission policy
- [ ] No secrets in Git or plaintext values; a decided reload path after rotation
- [ ] Upgrade / rollback including CRDs, and version-skew verification

### Delivery [delivery/*.md]
- [ ] CI templates and job images pinned by commit / tag / digest (not `main` / `latest`)
- [ ] Runners separated by trust boundary; nothing unrelated on a privileged DinD runner
- [ ] Staging / production changed through Git declarations; CI not hitting the cluster directly
- [ ] Failure conditions decided for GitOps prune / selfHeal / auto-sync / sync waves
- [ ] Security jobs allowed to fail are not acting as the real gate
- [ ] Cosign verify **explicitly specifies** issuer and certificate identity, rather than merely
      confirming a signature exists [delivery/docker-cosign.md]

### Secrets [secrets/*.md]
- [ ] Vault in HA (three or more nodes, zone-spread, PDB, anti-affinity), not dev/standalone
- [ ] Auto-unseal KMS permissions, availability, deletion protection, rotation
- [ ] Vault policies deny-by-default, avoiding wildcards
- [ ] Root token revoked after initial setup
- [ ] Several audit devices, with defined behaviour when logging stops
- [ ] ESO's Vault policy limited to read/list on the paths it needs
- [ ] `ClusterSecretStore` not shared without restriction
- [ ] `dataFrom` / templates not copying broad value sets into Kubernetes Secrets
- [ ] Restore, not just snapshotting, actually tested

### Observability [operations/observability.md]
- [ ] SLI / SLO / recording rules / alerts / dashboards / runbooks tied together per service
- [ ] Symptom-based alerts, plus dead-man / availability alerting on the monitoring stack itself
- [ ] No unbounded label values (user ID, request ID, full URL)
- [ ] Loki labels limited to bounded / static values
- [ ] Alerts carry severity / owner / runbook URL / dashboard URL
- [ ] Generated and hand-written rules not duplicating each other
- [ ] Cardinality and retention cost estimated

### Policy [security/kyverno.md]
- [ ] **Is `kyverno.io/v1 ClusterPolicy` still in use?** (see Known Patterns — the most important
      known issue)
- [ ] A staged Audit → Enforce rollout design
- [ ] Image verification targeting digests, not tags
- [ ] CI verify and admission verify policies managed from one source
- [ ] Fail-open / fail-closed decided for registry or Sigstore outages
- [ ] Kyverno's own replicas / PDB / webhook timeout / failurePolicy, canary namespace and
      rollback path

## Multi-Cloud (mandatory section)

Against @rules/infra/multi-cloud.md.

- [ ] No cloud branching leaking into L2/L3 (manifests, shared charts)
- [ ] L1 module output names aligned across the three clouds
- [ ] No implicit dependency on AWS-only pieces (Karpenter, FIS) that breaks the premise of
      expanding to another cloud
- [ ] No single state holding several clouds' credentials
- [ ] No per-cloud image rebuild (digest identity)
- [ ] Label / resource attribute names aligned across clouds
- [ ] The backend's cloud is not a single point of failure for the others' apply
- [ ] Kyverno policies not forked per cloud, leaving a gap in signature verification
- [ ] Version skew / EOL verified for all three clouds

## Environment Parity (mandatory section)

Against @rules/infra/environments.md §6. The eleven checks there are used verbatim.

## Per-Environment Standards

**The same code gets a different verdict in a different environment. Never write a finding without
confirming the environment.**

This table is **this skill's convention** — the bundle has no per-environment verdict table. Rows
that do have bundle grounds carry their own source (direct apply being deliberate in test
[architecture/platform-architecture.md], the staged Kyverno Audit → Enforce rollout
[security/kyverno.md], Vault HA as a production requirement [secrets/vault.md]). When using this
table in a finding, speak with the bundle's authority only for those rows.

| Aspect | local | test | staging | production |
|--------|-------|------|---------|------------|
| Replica 1 / no HA | acceptable | acceptable | check | **NG** |
| No signature verification / Kyverno | acceptable (state the limits) | Audit is fine | fine if mid-migration to Enforce | **NG** |
| Observability stack omitted | acceptable | partially | production-equivalent preferred | **NG** |
| Self-signed TLS | acceptable | check | NG | **NG** |
| Direct apply to the cluster | acceptable | **deliberate design** | NG (GitOps) | **NG** |
| Drift present | acceptable | expected (needs a re-creation procedure) | should be resolved by selfHeal | **NG** |
| Deploy without approval | acceptable | acceptable | MR merge is fine | **NG** |
| Production data present | **NG** | **NG** | masking mandatory | — |
| Plaintext secrets in Git | **NG** | **NG** | **NG** | **NG** |
| Environment branching in the base | **NG** | **NG** | **NG** | **NG** |
| Per-environment image rebuild | **NG** | **NG** | **NG** | **NG** |

The bottom four rows admit **no exception in any environment**. "It's only local" is not a reason
(@rules/infra/environments.md §5).

## Severity

Severity moves with the environment: as a rule drop one step going
**production > staging > test > local** — except for the four rows above that are NG everywhere,
whose severity never drops.

| Severity | Definition | Examples |
|----------|------------|----------|
| **Critical** | Directly implies secret disclosure, data loss or a full outage | Plaintext secret in Git, unprotected shared state, a backup whose restore was never verified, production data reaching a lower environment |
| **High** | A realistic path to a production incident or a security breach | Ownership overlap, broken digest continuity, Cosign verify without an identity, surviving `ClusterPolicy` |
| **Medium** | Breeding ground for operational load and change accidents | Unpinned versions, a security gate allowed to fail, unmanaged label cardinality |
| **Low** | Readability, consistency, future improvement | Module naming, missing descriptions, duplicated overlays |
| **Info** | Not enough information; needs confirmation | Environment-dependent items that cannot be judged from outside |

Every finding is written as **path:line → what → impact → fix → source bundle document**. Never
write a finding that only says something is bad.

## Known Patterns Worth Checking

| Pattern | What |
|---------|------|
| **Kyverno ClusterPolicy** | `kyverno.io/v1 ClusterPolicy` is deprecated (critical fixes only). v1.18 stabilized ValidatingPolicy / MutatingPolicy / GeneratingPolicy / ImageValidatingPolicy under `policies.kyverno.io/v1`; v1.20 (planned for October 2026) removes the old one [security/kyverno.md]. The observed implementation still used `ClusterPolicy`; the migration procedure is in the same document |
| **Pinning a major image tag** | A tag like `docker:27` is not pinned to a patch or digest. The bundle itself lists this as an improvement candidate [delivery/docker-cosign.md] |
| **Re-resolving the digest after build** | Re-resolving from a tag can shift what is scanned, signed and deployed. Capture the digest as an artifact right after build [delivery/docker-cosign.md] |
| **No SBOM / provenance** | Associating an SBOM and build provenance with the same digest is an open improvement [delivery/docker-cosign.md] |
| **Moving CI template references** | `main` / `latest` change behaviour without notice [delivery/gitlab-cicd.md] |
| **Misreading PolicyReport** | A PolicyReport is the current evaluation result, not a history of rejections. Investigating a blocked admission needs Events, metrics or audit logs [security/kyverno.md] |
| **Misreading the `Orphan` deletion policy** | It leaves the Secret behind on deletion; it does not prevent overwrite on re-creation [secrets/external-secrets.md] |
| **Misreading Vault HA** | HA is for availability, not horizontal performance [secrets/vault.md] |
| **Ad-hoc Argo CD rollback** | Auto-sync re-applies the new revision. Rollback means Git revert or forward-fix [delivery/argocd.md] |
| **Sync succeeded ≠ ready** | Without a health assessment for a custom resource, do not conflate sync success with service readiness [delivery/argocd.md] |
| **Production is not in the bundle** | The ownership table has no production row and every mention is guidance. There is no such thing as "a production configuration as the bundle prescribes". Report production's apply path, approval and rollback as decisions still to be made (@rules/infra/environments.md §0) |
| **Local is not in the bundle** | Not covered at all. Ground findings about local configuration in this skill's conventions or official documentation, never in the bundle's authority |
| **The test/staging asymmetry** | Direct apply vs. GitOps is a deliberate design [architecture/platform-architecture.md]. Do not report the asymmetry itself. What is worth reporting is that the asymmetry is undocumented, and that test lacks a drift re-creation procedure |
| **Staging drifting from production** | The more they differ, the less staging proves. A difference with no stated reason is a finding |

## Things a Review Must Not Do

- **Write a finding without confirming the environment** (the verdict changes with it)
- **Speak with the bundle's authority about local or production configuration** (neither is in the
  observed implementation)
- Report from general principle without reading the bundle
- Present a recommendation the bundle does not make as though it did — say "outside its scope"
- Assert "it must look like this" from the bundle alone without reading the implementation (the
  bundle is a snapshot of specific commits)
- List findings without severities
- Emit a finding without a proposed fix

## Options

| Flag | Effect |
|------|--------|
| `--env=<env>` | Target environment: `local` / `test` / `staging` / `production`. Repeatable |
| `--cloud=<cloud>` | Target cloud: `aws` / `azure` / `gcp`. Repeatable |
| `--round=<n>` | Force the review round number instead of deriving it from existing reports |

## Output

| File | Content |
|------|---------|
| `$OUT/reviews/review-<target>-r<round>.md` | The review report (`templates/infra/review-report.md`) |

Written in the project's `options.output_language`. Location per `/infra:start`
§ Output Location.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /infra:design, /infra:implement | Produce what this reviews |
| /architect:review-operations | Sibling — reviews operational readiness in design documents; this one reviews infrastructure code |
| gitlab-review | For turning an MR review into a write-up in the GitLab review convention |
