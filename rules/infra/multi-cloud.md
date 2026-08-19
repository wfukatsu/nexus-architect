# Rules: Multi-Cloud as the Default Premise

`/infra:*` skills assume AWS / Azure / GCP may be **in scope simultaneously**. Never produce an
answer that silently assumes one cloud. The bundle's own observed implementation separates clouds
too — `terraform/environments/<cloud>/<env>/{infra,kubernetes}` and
`terraform/modules/{aws,azure,gcp,kubernetes}`
[architecture/platform-architecture.md, foundation/terraform.md].

Read with @rules/okf-k8s-tf-bundle.md and @rules/infra/environments.md (the environment axis,
which multiplies with this one).

## 0. Four things to fix before starting

In design, implementation and review alike, settle these before doing anything else. Ask the user
when unknown.

1. **Which clouds**, in which environments (`local` / `test` / `staging` / `production`). Fill the
   cloud × environment grid first (@rules/infra/environments.md §7). Keep local
   cloud-independent — tying it to one cloud's emulator makes that cloud the de facto reference.
2. **Why multi-cloud**: portability, a customer requirement, DR, avoiding vendor lock-in, or
   simply several unrelated engagements. The purpose decides how much duplication is acceptable.
3. **Whether it runs concurrently**: is the *same* workload live in several clouds at once, or is
   one cloud chosen per engagement? Only the first forces data-consistency, DNS and cost-allocation
   design.
4. **How far commonality is meant to go**: aligning interfaces only, or sharing implementations
   too.

## 1. The portability boundary

The bundle's Terraform module guidance is to align the interface for concepts the clouds share,
while not forcing provider-specific attributes and vocabulary into hiding
[foundation/terraform.md]. Expressed as layers:

| Layer | Examples | Commonality policy |
|-------|----------|--------------------|
| **L1 cloud-specific** | VPC/VNet, IAM/Managed Identity, EKS/AKS/GKE node configuration, KMS | **Do not unify.** Confine to `modules/{aws,azure,gcp}`; align only variable names and output names |
| **L2 Kubernetes abstraction** | Deployment, Service, NetworkPolicy, ServiceAccount, CRDs | **Fully common.** No cloud branching reaches this layer |
| **L3 platform components** | Argo CD, Vault, ESO, Kyverno, kube-prometheus-stack, Kong | **Common chart and values**; cloud differences confined to the smallest possible value diff [foundation/helm.md] |
| **L4 applications** | ScalarDB, business applications | **Fully common.** Only the endpoints (database, object storage) are injected |

**The design question is where to draw the L1/L2 line.** Draw it too high — cloud branching leaks
into L2/L3 — and manifests fork once per cloud until the shared platform means nothing. Draw it
too low — L1 forced into an abstraction — and the Terraform modules become the giant
lowest-common-denominator conditional the bundle warns against as over-abstraction
[foundation/terraform.md].

### Concrete rules that hold the boundary

- **Align L1 module output names across the three clouds** (`cluster_endpoint`, `cluster_ca`,
  `oidc_issuer_url`, `db_endpoint`, `object_store_uri`). What is behind them stays cloud-specific.
- Never write the equivalent of `if cloud == "aws"` into L2/L3. Express the difference as a value
  difference in a Kustomize overlay or Helm values
  [foundation/kustomize.md, foundation/helm.md].
- Concentrate cloud-specific annotations (workload-identity binding and the like) in one outermost
  place in the overlay/values. Never in the base.
- When three or more differences cannot be expressed in common, choose **separation, not
  abstraction**.

## 2. Cloud service mapping

The services `architecture/supporting-stack.md` names, arranged by role. **This table is a
starting point, not a guarantee of equivalence.** Before adopting any row, check that service's
availability SLA, regions, encryption and network requirements individually — i.e. put it in the
open questions.

| Role | AWS | Azure | GCP |
|------|-----|-------|-----|
| Managed Kubernetes | EKS | AKS | GKE |
| Networking | VPC | VNet | VPC |
| RDBMS | RDS | PostgreSQL Flexible Server | Cloud SQL |
| NoSQL | DynamoDB | (not in the bundle) | (not in the bundle) |
| Object storage | S3 | Storage | Cloud Storage |
| Key management | KMS (via IAM/OIDC) | Key Vault | KMS |
| Workload identity | IAM Roles for Service Accounts (OIDC) | Managed Identity | Workload Identity |
| Analytics | EMR Serverless | Synapse | Dataproc |
| Audit logging | CloudTrail | (not in the bundle) | (not in the bundle) |
| Threat detection | GuardDuty | (not in the bundle) | (not in the bundle) |
| Fault injection | FIS | (not in the bundle; Chaos Mesh instead) | (not in the bundle; Chaos Mesh instead) |
| Node autoprovisioning | Karpenter | (AWS-only; cluster autoscaler instead) | (AWS-only) |

"Not in the bundle" **does not mean it does not exist** — it means the bundle did not investigate
it. Check the official documentation when it becomes relevant, and flag it as an open question.

### Asymmetries to watch

- **Karpenter is AWS-only** [architecture/supporting-stack.md]. Node scaling strategy, and the PDB
  and topology-spread design that depends on it, will not be identical between AWS and the others
  [foundation/kubernetes.md].
- **Vault's auto-unseal KMS** differs across the three clouds in permission model, key rotation and
  deletion protection [secrets/vault.md]. Write the unseal-failure runbook per cloud.
- **Workload identity binding** differs in annotation format and trust-policy claims. Aligning
  ServiceAccount names does not make the IAM side common
  [foundation/kubernetes.md, foundation/terraform.md].
- **Kubernetes version availability and EOL** differ per managed service. Verify version skew for
  each cloud [foundation/kubernetes.md].
- **NetworkPolicy is implemented by the CNI**, which differs, so identical manifests can behave
  differently. Verify default-deny per cloud.

## 3. State and account boundaries

- Split state by cloud × environment (test / staging / production) × layer (infra / kubernetes).
  Local builds no L1 and therefore holds no state. Apply the bundle's split criteria — change
  frequency, owning team, permissions, blast radius — to the cloud axis as well
  [foundation/terraform.md].
- **Never consolidate several clouds' credentials into one state.** Read access to a whole state is
  effectively access to every secret in it [foundation/terraform.md].
- Decide which cloud hosts the backend, and record as a design decision that an outage in the
  backend cloud stalls apply in the others — that is a single point of failure.
- The units in which failure boundaries are defined are namespace, cloud
  account/subscription/project, and state [architecture/design-build-checklist.md].

## 4. Delivery across clouds

- **Build the image once and ship the same digest to every cloud** [delivery/docker-cosign.md].
  No per-cloud rebuild — it forks the signing identity and the scan result.
- Cosign identity/issuer verification and Kyverno's allowed repositories are managed **from one
  source** across clouds [security/kyverno.md, delivery/docker-cosign.md].
- When mirroring registries per cloud, make digest equality and the freshness of Kyverno's allowed
  repository list explicit verification items.
- Decide whether one Argo CD serves clusters in several clouds or each cloud runs its own. The
  former means accepting AppProject destination restrictions and an Argo CD outage whose blast
  radius spans every cloud [delivery/argocd.md].

## 5. Observability across clouds

- Use **identical label / resource attribute names in every cloud** for `cluster`, `cloud`,
  `region`, `environment`, `namespace`, `service` [operations/observability.md]. Without this there
  is no cross-cloud dashboard and no cross-cloud SLO.
- Keep labels to bounded values, and include in the estimate that cardinality grows with the number
  of clouds [operations/observability.md].
- Decide whether Prometheus / Loki / Tempo run per cloud or centrally. Centrally means designing
  cross-cloud egress cost, the network path, and backpressure when collection stalls.
- Agree with the service owner whether SLOs are measured as separate SLIs per cloud or combined.

## 6. Multi-cloud anti-patterns

| Anti-pattern | Why it fails |
|--------------|--------------|
| A home-grown lowest-common-denominator module | Each cloud's needed features become unreachable and the conditionals grow without bound [foundation/terraform.md] |
| Cloud branching leaking into L2/L3 | Manifests fork once per cloud and the shared platform stops meaning anything |
| Rebuilding the image per cloud | Breaks digest identity across scan / sign / deploy [delivery/docker-cosign.md] |
| Consolidating into one state | Spreads blast radius and permissions across every cloud [foundation/terraform.md] |
| Label names that differ between clouds | Cross-cloud visualization and SLOs cannot exist [operations/observability.md] |
| Asymmetry left alone because "it works" | An implicit dependency on AWS-only pieces like Karpenter or FIS surfaces at the moment of expansion |
| A separate Kyverno policy per cloud | A gap in signature verification survives as a per-cloud difference [security/kyverno.md] |
