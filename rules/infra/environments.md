# Rules: The Four Environments (local / test / staging / production)

Infrastructure has four environments. **Every `/infra:*` output fixes which one it is about before
it is written.** An environment-agnostic answer is not a general answer; it is an answer that is
wrong somewhere and does not say where.

Read with @rules/okf-k8s-tf-bundle.md (the bundle and its citation rules) and
@rules/infra/multi-cloud.md (the cloud axis, which multiplies with this one).

## 0. What the bundle covers, per environment

This is the most important table in this file, because the coverage is uneven and the unevenness
must survive into the output.

| Environment | In the bundle | Required posture |
|-------------|---------------|------------------|
| **local** | **Absent** — entirely outside its scope | Say "outside the bundle's scope". Answer from official documentation or general principle; do not assert. §5 below is *this rule's* convention, not a bundle statement |
| **test** | **Observed implementation**: `kubernetes/test` or an app's `k8s/`, applied by a documented procedure or by CI `kubectl apply`, live state [architecture/platform-architecture.md] | Citable as fact |
| **staging** | **Observed implementation**: app-of-apps rooted at `kubernetes/staging`, Argo CD sync, Git commit [architecture/platform-architecture.md, delivery/argocd.md] | Citable as fact |
| **production** | **No observed implementation** — the ownership table has no production row. Every mention is design guidance | Say "the investigated repositories contain no production implementation", present the guidance below with its grounds, and put the apply path in the open questions |

What the bundle *does* say about production is, as far as can be confirmed, exactly four things:

1. Separate test / staging / production by purpose, data, access and change approval
   [architecture/design-build-checklist.md]
2. For staging and production, change the declaration in Git and verify Argo CD's diff and health
   [architecture/design-build-checklist.md]
3. Production adds sync windows, manual approval and protected branches as requirements dictate
   [delivery/argocd.md]
4. Staging and production leave every manifest-repository change as an auditable MR / commit
   [delivery/gitlab-cicd.md] — plus: untrusted fork/MR pipelines and production credentials never
   share a runner [delivery/gitlab-cicd.md], and production Vault is HA, not dev/standalone
   [secrets/vault.md]

**So the production apply path is designed as "staging's GitOps plus approval, protection and sync
windows".** That is consistent with the bundle — but it is a design decision, not an established
fact. Record it in an ADR rather than writing it as if it were already true.

## 1. Environment matrix

| Aspect | local | test | staging | production |
|--------|-------|------|---------|------------|
| Purpose | Fast developer feedback | Automated verification from CI, E2E, DAST | Production-equivalent integration verification | Customer-facing |
| Lifecycle | Disposable (created and destroyed at will) | Permanent but re-creatable | Permanent | Permanent, cannot be stopped |
| Applied by | The developer (local scripts) | A documented procedure **or** CI `kubectl apply` (direct apply) | Argo CD (GitOps) | Argo CD + approval (**to be decided**) |
| Where the declaration lives | Developer's machine + shared base | `kubernetes/test` or the app's `k8s/` | `kubernetes/staging` | **To be decided** (follows staging) |
| State and history | None (disposable) | Git commit + live state | Git commit + Argo CD Application | As staging + approval record |
| Cloud foundation (L1) | Not created | Terraform | Terraform | Terraform |
| Data | Synthetic only | Synthetic | Production-like but masked (**to be decided**) | Real data |
| Production data allowed in | **Forbidden** | **Forbidden** | Per requirements; masking mandatory | — |
| Access | The developer only | The development team | Restricted | Minimal, audited |
| Change approval | None | MR merge | MR merge | MR + explicit approval (**to be decided**) |
| Availability design | None (replica 1) | Minimal | Aims at production equivalence | As required |
| DR / backup | None | Not required | Used as the place to rehearse restore | Mandatory, tested on a schedule |

**To be decided** marks an item the bundle has no implementation fact for. Decide it during
design, record it in an ADR, and list it under open questions.

## 2. What stays identical, and what may differ

Leaving this vague is how environment differences become incidents.

### Identical across environments — never branched

- **The container image digest.** No per-environment rebuild: build → scan → sign → verify →
  deploy all reference the same digest [delivery/docker-cosign.md]
- **The Kubernetes manifest base.** The base is never branched on environment
  [foundation/kustomize.md]
- **The Helm chart and its version.** Differences are confined to values [foundation/helm.md]
- **Metric/log label names and resource attribute names** — only the *value* of `environment`
  changes [operations/observability.md]
- **The rule that secrets never sit in Git or in plaintext values.** No local exception (§5)
- **ServiceAccount names and the shape of RBAC** (the IAM identity they bind to is per-environment)

### May differ — confined to overlays and values

Replica count, resource requests/limits, hostnames/DNS, storage class and size, log and metric
retention, alert routing and severity thresholds, sampling rate, node pools and scaling settings,
the environment label.

Every difference is expressed as a **value difference in an overlay or in values**. Never write
`if env == "production"` into a base [foundation/kustomize.md].

### When the differences exceed three

It is becoming a different system rather than a different environment. Before adding another
overlay, question whether the difference is necessary at all. A staging/production difference is
the most expensive kind: it directly reduces what staging verifies.

## 3. Promotion path

The flow confirmed in the observed implementation
[delivery/gitlab-cicd.md, architecture/platform-architecture.md]:

```
local ──(outside the bundle)──▶ test ──E2E──▶ staging ──(to be decided)──▶ production
                                 ↑              ↑
                          kubectl apply   update the manifest's image
                          (direct apply)  in Git → Argo CD syncs
```

1. Secret Detection / SAST / Dependency Scanning
2. Unit tests, Docker build/push
3. Container Scanning, Cosign sign/verify
4. `kubectl apply` from main into **test**
5. After E2E, update the manifest and let Argo CD sync **staging**
6. Smoke tests, failure notification
7. Scheduled DAST / API / Coverage Fuzzing

**What gets promoted is a digest — not code and not a tag.** Each promotion commit must let a
reader trace back to the source image digest, the build pipeline and the signature
[foundation/kustomize.md].

The bundle has no implementation fact for promotion into production, so design decides:

- The unit of promotion (digest / release tag) and the evidence that staging verified it
- Who approves, and how the approval is recorded [delivery/gitlab-cicd.md]
- Where sync windows, manual approval and protected branches apply [delivery/argocd.md]
- The rollback method (Git revert / forward-fix — an ad-hoc Argo CD rollback is undone by
  auto-sync [delivery/argocd.md])

## 4. Where the emphasis falls, per environment

### local (outside the bundle's scope)

- Do not build L1. For anything that depends on cloud infrastructure, **explicitly choose** one of
  mock / emulator / shared test environment — and write the choice and its limits into the open
  questions
- The Kubernetes runtime (kind / minikube / k3d …) is outside the bundle. When adopting one, check
  whether its Kubernetes version can be kept in step with test and above (version skew,
  [foundation/kubernetes.md])
- Decide whether to run Vault / Kyverno / the observability stack. **If they are omitted, state
  that "it worked locally" is not evidence of passing signature verification or admission policy**
- Keep startup to one command. The longer the procedure, the less the local environment is used,
  and the wider the environment gap grows
- **Declare what is not reproduced.** What cannot be reproduced locally — HA, real NetworkPolicy
  behaviour, workload identity, the performance characteristics of the real database — is the
  central deliverable of local-environment design, not a footnote

### test

- **Direct apply drifts.** Assume the Git declaration and the live state diverge, and provide a
  re-creation procedure [architecture/platform-architecture.md]
- The only environment where direct apply is legitimate (applied by a documented procedure **or**
  CI [architecture/platform-architecture.md]). CI authenticates with short-lived OIDC credentials,
  and the deploy role is separate from plan/apply/sign [delivery/gitlab-cicd.md]
- The target of scheduled DAST / API / Coverage Fuzzing runs [delivery/gitlab-cicd.md]
- Run Kyverno in Audit here, and use it to inventory violations before raising staging/production
  to Enforce [security/kyverno.md]

### staging

- GitOps. Never edit the live cluster. CI updates the manifest's image reference, not the cluster
  [delivery/argocd.md]
- Define `prune` / `selfHeal` behaviour, a break-glass procedure and drift auditing
  [delivery/argocd.md]
- Use it as the place to rehearse restore, upgrades and chaos experiments (**this rule's
  recommendation**: the bundle requires periodic restore testing
  [architecture/design-build-checklist.md] and names fault-injection tooling
  [architecture/supporting-stack.md], but does not say where it runs)
- Keep the difference from production small. The larger it is, the less staging proves

### production

- No implementation fact in the bundle. **Take staging's configuration as the base and add
  approval, protection and sync windows**
- Vault is HA (three or more nodes, spread across zones, PDB, anti-affinity); design the
  auto-unseal KMS key's permissions, availability, deletion protection and rotation
  [secrets/vault.md]
- Test **restore**, not backup, on a schedule, and measure RTO/RPO against the real system
  [architecture/design-build-checklist.md]
- Kyverno runs in Enforce — but a policy error can halt deployment cluster-wide, so provide a
  canary namespace and a rollback path [security/kyverno.md]
- Symptom-based alerts, plus dead-man / availability alerting on the monitoring stack itself
  [operations/observability.md]
- Untrusted fork/MR pipelines never share a runner with production credentials
  [delivery/gitlab-cicd.md]
- Control who applies and in what order with protected branches/tags, protected environments,
  approvals and `resource_group` [delivery/gitlab-cicd.md]

## 5. What may be relaxed locally — and what may not

The bundle says nothing about local environments, so this table is **this rule's convention**.
Never present it with the bundle's authority.

| Item | Verdict | Reason |
|------|---------|--------|
| Replica count, resources, HA | **May relax** | Developer machines are resource-constrained. Declare "HA is unverified" |
| Omitting the observability stack | **May relax** | But state that alerts and SLOs cannot be verified locally |
| Omitting Kyverno / signature verification | **May relax** | But state that "it passed locally" does not mean "it is safe" |
| Self-signed TLS | **May relax** | Real certificate handling is verified from test upwards |
| **Bringing in production data** | **Forbidden** | A developer machine guarantees neither encryption, nor access control, nor audit |
| **Committing plaintext secrets to Git** | **Forbidden** | A local exception becomes a habit that leaks. Use a generator script or a Git-ignored file |
| **Branching the base** | **Forbidden** | Local differences also stay in an overlay [foundation/kustomize.md] |
| **Swapping in a locally rebuilt image** | **Forbidden in principle** | Experimenting locally is fine; carrying that image into test or above is not |

## 6. Environment-parity review checklist

A review always devotes one section to this.

- [ ] Are base, chart and image digest identical across environments?
- [ ] Is every environment difference a **value difference** in an overlay or in values, with no
      branch leaking into the base?
- [ ] Are the staging/production differences enumerated, each with a reason?
- [ ] Is there a re-creation procedure covering test's drift from direct apply?
- [ ] Is promotion done per digest, with traceable evidence (build pipeline, signature)?
- [ ] Are production's apply path, approval and rollback decided? (the area with no
      implementation fact)
- [ ] Is there any path by which production data reaches test / staging / local?
- [ ] Is each environment's Kyverno failure action (Audit / Enforce) what was intended?
- [ ] Is the `environment` label value consistent across environments, so cross-environment
      dashboards work?
- [ ] Is what cannot be reproduced locally documented and communicated to developers?
- [ ] Are namespace / cloud account / state failure boundaries separated per environment?
      [architecture/design-build-checklist.md]

## 7. Environment × cloud

The cloud axis (@rules/infra/multi-cloud.md) multiplies with this one. Do not try to fill every
cell.

- **State which environments exist in which cloud, in a table.** Asymmetry — "all four in AWS,
  only staging and production in Azure" — is normal and fine. What is not fine is leaving it
  implicit
- Split state by cloud × environment × layer (infra / kubernetes) [foundation/terraform.md]
- Keep local cloud-independent. Once local depends on one cloud's emulator, that cloud has
  silently become the reference cloud
- Managed Kubernetes versions become available and reach EOL on different schedules per cloud, so
  do not verify version skew across *cloud count × environment count*: anchor on each cloud's
  production version and align the lower environments to it

| | local | test | staging | production |
|---|---|---|---|---|
| AWS | | | | |
| Azure | | | | |
| GCP | | | | |

(The design document fills this in. A blank cell means "not deployed here" — it is never left
implicit.)
