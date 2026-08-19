---
description: |
  Design a multi-cloud, four-environment infrastructure configuration from requirements and emit
  the design document, environment matrix and ADRs. Grounded in the OKF k8s/tf bundle; writes no
  implementation code.
  /infra:design [target] [--env=<env>] [--cloud=<cloud>] [--auto] to invoke.
  Use for "design the infrastructure", "decide the configuration", "select the technology",
  "compare the approaches". Implementation follows separately via /infra:implement, after the
  design is agreed.
model: opus
user_invocable: true
---

# Infrastructure Design

## Desired Outcome

A configuration a team can build from, in which:

- Requirements are **numbers**, not adjectives
- The multi-cloud premise and the four environments are settled, with the cloud × environment
  grid filled in
- Every resource has **exactly one owner**
- Each of L1–L4 states what stays identical across environments and what may differ
- The promotion path is designed **per digest**
- Every decision that had two or more options is recorded as an ADR
- The open questions are listed rather than silently resolved

**No implementation code is written here.**

## Decision Criteria

| Situation | Do this |
|-----------|---------|
| A requirement is qualitative ("highly available", "fast") | It is not a requirement yet. Ask for a number, or record a provisional value with the reason it is provisional |
| The bundle covers the topic | Cite it `[document.md]` and state it at the right tier (fact / guidance / open question) |
| The bundle does not cover it (all of `local`; anything production-specific) | Say "outside the bundle's scope", ground it in official documentation or in @rules/infra/environments.md §5, and never speak with the bundle's authority |
| Three or more differences cannot be expressed in common across clouds | Choose separation, not abstraction (@rules/infra/multi-cloud.md §1) |
| More than three differences between two environments | It is becoming a different system. Question the differences before adding another overlay |

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| `knowledge/okf-k8s-tf/` | **Required** | Vendored bundle (@rules/okf-k8s-tf-bundle.md) |
| reports/03_design/target-architecture.md | Recommended | /architect:design-microservices |
| reports/08_infrastructure/infrastructure-design.md | Recommended | /architect:design-infrastructure — the logical design this makes concrete |
| reports/08_infrastructure/{security,observability,disaster-recovery}-design.md | Recommended | The corresponding `/architect:design-*` skills — policy this design implements |
| The target repository | Recommended | Read it when it exists; the code is the fact and the bundle is the standard |

When invoked from `/infra:start`, environment, cloud, target path and `$OKF` arrive already
settled. **Do not re-ask them** — confirm only what is missing. When invoked directly, run
@rules/okf-k8s-tf-bundle.md §1–2 first (resolve, freshness, environment, cloud).

## Step 1 — Turn requirements into numbers

Use the "requirements and boundaries" section of `architecture/design-build-checklist.md` as the
question list. Do not leave a blank and continue: record a provisional value with its grounds.

- Availability target, RTO / RPO
- Performance (throughput, latency)
- Data retention
- Budget
- Regulatory constraints and data residency
- For each environment in scope: purpose, data, access, change approval

A requirement without a number cannot ground a design decision.

## Step 2 — Settle the multi-cloud and environment premises

Fill in the four items of @rules/infra/multi-cloud.md §0. A design that proceeds with these vague
will break later — that is the single most reliable failure in this area.

Then fill the environment matrix (@rules/infra/environments.md §1). At minimum:

- **Which of the four environments this design covers**
- The cloud × environment grid (§7). A blank cell means "not deployed here", never left implicit
- Separation of purpose, data, access and change approval per environment
  [architecture/design-build-checklist.md]
- **The production apply path.** The bundle has no implementation fact here, so decide it now and
  record it as an ADR (staging's GitOps plus approval, protection and sync windows is the
  bundle-consistent shape)
- **The declaration of what local does not reproduce.** This is the central deliverable of
  local-environment design, not a footnote

## Step 3 — Decide the ownership split

Start from the bundle's ownership table and produce this system's version
[architecture/platform-architecture.md].

| Resource | Where the declaration lives | Applied by | State / history |
|----------|-----------------------------|------------|-----------------|

**Verify one-resource-one-owner immediately after writing the table** — that Terraform, Argo CD,
CI and manual operation do not overlap. For reference, the observed implementation splits as:

- Cloud foundation → `terraform/environments/*/infra`, the Terraform job in GitLab CI
- Shared Kubernetes platform → `terraform/environments/*/kubernetes` + `terraform/modules/kubernetes`
- Upstream Helm values → `terraform/charts`, Terraform `helm_release`
- Staging applications → `kubernetes/staging`, Argo CD app-of-apps
- Test manifests → `kubernetes/test` or the app's `k8s/`, applied by procedure or CI `kubectl apply`

## Step 4 — Design layer by layer

Work L1 → L4 (@rules/infra/multi-cloud.md §1), reading the bundle document for each. **State for
every layer what stays identical across environments and what may differ**
(@rules/infra/environments.md §2).

| Layer | What to decide | Bundle |
|-------|----------------|--------|
| L1 cloud foundation | Network, cluster, database, IAM, storage, state boundaries | `foundation/terraform.md` |
| L2 Kubernetes | Namespace design, RBAC, NetworkPolicy, Pod Security, workload availability | `foundation/kubernetes.md` |
| L3 shared components | Which charts, common vs. differing values, CRD lifecycle | `foundation/helm.md`, `architecture/supporting-stack.md` |
| L4 delivery | The GitOps boundary, CI stages, environment protection, image identity | `delivery/*.md` |
| Cross-cutting | Secrets, observability, policy | `secrets/*.md`, `operations/*.md`, `security/*.md` |

Any version named here is **looked up, not recalled**, and must be stable and non-EOL
(@rules/dependency-versions.md). State the version *and* its support horizon so
`/infra:implement` pins the same set.

## Step 5 — Write the apply flow

Numbered: who applies what, on what trigger, in what order — **within a single environment**
[architecture/platform-architecture.md]. Make explicit:

- Inter-state dependencies in Terraform and the resulting apply order
- The boundary between what GitOps syncs and what CI touches directly [delivery/argocd.md]

Flow *between* environments (digest promotion, approval, rollback) belongs in Step 8.

## Step 6 — Write the change-impact matrix

Make the bundle's change-impact table concrete for this system
[architecture/platform-architecture.md]. These six rows are the minimum:

| Change | What must be checked at the same time |
|--------|---------------------------------------|
| Kubernetes version | kubectl, provider, Helm chart/CRD, managed-service add-ons |
| Provider version | `.terraform.lock.hcl`, plan diff, deprecated attributes, state migration |
| Helm chart version | CRDs, values schema, hooks, rollback method, orphaned resources |
| ServiceAccount / namespace | IAM workload identity, Vault role/policy, RBAC, NetworkPolicy |
| Image repository / tag | CI matrix, scanner, Cosign identity, Kyverno rule, Kustomize image |
| Secret path | Vault policy, SecretStore, ExternalSecret, application references, rotation |

## Step 7 — Put the environment differences on one page

Fill `templates/infra/env-matrix.md`. It becomes the most-referenced table in the design.

- Replicas / resources / storage / retention / alert routing / scaling, per environment
- **Enumerate the staging↔production differences separately, each with a reason.** A difference
  with no reason lowers what staging proves — remove it
- Wherever there are more than three differences, check whether it is still an environment
  difference or has become a different system

## Step 8 — Design the promotion path

The flow *between* environments (@rules/infra/environments.md §3).

- The unit of promotion is a **digest** — not code, not a tag. Write the path by which the digest
  CI built reaches deploy intact [delivery/docker-cosign.md]
- Each promotion commit must trace back to the source image digest, the build pipeline and the
  signature [foundation/kustomize.md]
- A re-creation procedure for test's drift under direct apply
  [architecture/platform-architecture.md]
- Approval, sync windows and rollback method (Git revert / forward-fix) for production
  [delivery/argocd.md, delivery/gitlab-cicd.md]

## Step 9 — Record the decisions

Every judgement that had two or more options goes into `templates/infra/adr.md`. In multi-cloud
work the "unify or not" calls are the ones argued about later — record those without exception.

## Step 10 — Emit the design and leave the open questions standing

Use `templates/infra/design-doc.md`. **The closing open-questions section is never empty**: walk
every item of `architecture/design-build-checklist.md` and drop what is unmet into it. Follow
@rules/open-questions.md — ask the user what the user owns, and record as `TBD` only what is
deferred, unanswerable in session, or never asked (`--auto`).

## Options

| Flag | Effect |
|------|--------|
| `--env=<env>` | Target environment: `local` / `test` / `staging` / `production`. Repeatable |
| `--cloud=<cloud>` | Target cloud: `aws` / `azure` / `gcp`. Repeatable |
| `--auto` | Do not ask. Every unresolved item becomes an open question with status `unasked`, carrying the question and the options that would have been offered |

## Output

Written in the project's `options.output_language`. Location per `/infra:start` § Output Location.

| File | Content |
|------|---------|
| `$OUT/infra-design-<system>.md` | The design document (`templates/infra/design-doc.md`) |
| `$OUT/env-matrix-<system>.md` | The environment matrix (`templates/infra/env-matrix.md`) |
| `$OUT/adr/adr-<NNN>-<slug>.md` | One per decision (`templates/infra/adr.md`) |

## Easily Missed Points

Reminders drawn from the bundle. Each of these has been got wrong before.

- **The test/staging asymmetry is deliberate** in the observed implementation — staging is GitOps,
  test is direct apply [architecture/platform-architecture.md]. Decide **explicitly** whether a new
  design follows it or makes the two symmetric. Do not copy it unthinkingly.
- **Production does not exist in the observed implementation.** The ownership table has no
  production row and every mention is guidance. "Build production the way the bundle does" is not
  a sentence that can be said (@rules/infra/environments.md §0).
- **Local is absent from the bundle entirely.** Ground local statements in
  @rules/infra/environments.md §5 or in official documentation, never in the bundle's authority.
- **Vault HA is for availability, not performance scaling** [secrets/vault.md]. Do not try to meet
  a throughput requirement with node count.
- **Kubernetes Secrets still appear in etcd and on the Pod/node.** Using Vault does not remove
  that exposure [secrets/external-secrets.md].
- **When Argo CD is down, existing workloads keep running but new syncs and drift correction
  stop** [delivery/argocd.md]. Fold that into the availability design.
- **A Kyverno policy error can halt deployment cluster-wide** [security/kyverno.md]. Design the
  canary namespace and the rollback path with it.
- **Having a backup is not the same as being able to restore.** Put periodic restore testing into
  the operations design [architecture/design-build-checklist.md, secrets/vault.md].

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /infra:start | Router — settles environment, cloud and bundle before this runs |
| /infra:implement | Next step, after the design is agreed |
| /infra:review | Reviews what this produced |
| /architect:design-infrastructure | Upstream — the logical design this makes concrete |
| /architect:estimate-cost | Consumer — costs the configuration decided here |
