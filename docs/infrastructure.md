# Multi-Cloud Infrastructure Guide

The `/infra:*` plugin designs, builds and reviews the platform an application runs on — across
**three clouds (AWS / Azure / GCP)** and **four environments (local / test / staging /
production)** — grounding every claim in the vendored OKF `okf-k8s-tf` knowledge bundle instead of
model memory.

It is a separate plugin, not a phase of the architect pipeline. Nothing runs it automatically.

| Command | Model | What it does |
|---------|-------|--------------|
| `/infra:start` | sonnet | Triage: resolve the bundle, check freshness, fix environment and cloud, route to a mode |
| `/infra:design` | opus | Decide the configuration; emit the design document, environment matrix and ADRs |
| `/infra:implement` | sonnet | Write Terraform / manifests / Helm values / Kustomize overlays / CI into a real repository |
| `/infra:review` | opus | Assess existing code or a design document; emit severity-ranked findings |

## Setup

The bundle ships with the repository — there is nothing to fetch. Confirm it resolves:

```bash
tools/update-okf-bundle.sh status --bundle=k8s-tf
```

```
bundle:        k8s-tf (vendored — no remote)
resolved:      .../knowledge/okf-k8s-tf
okf_version:   0.2
documents:     23
stale_after:   earliest 2026-10-19 (a document past its date is re-verified, not quoted as current)
sections:
  architecture  delivery  foundation  operations  secrets  security
```

**There is no remote.** The bundle's origin repository was deleted, which is why it is vendored
rather than a submodule; `--latest` reports that rather than fetching. See
[`knowledge/OKF-K8S-TF-PROVENANCE.md`](../knowledge/OKF-K8S-TF-PROVENANCE.md).

To point the skills at a different copy, set `NEXUS_OKF_K8S_TF` to its root.

## The four premises

These are enforced by the skills, not offered as advice. Knowing them explains most of what the
output looks like.

### 1. Multi-cloud is the default

No answer assumes a single cloud. The design question is where the **portability boundary** falls:

| Layer | Policy |
|-------|--------|
| L1 cloud-specific (VPC/VNet, IAM, EKS/AKS/GKE, KMS) | Not unified. Confined to `modules/{aws,azure,gcp}`, with **aligned output names** |
| L2 Kubernetes (Deployment, Service, NetworkPolicy, RBAC) | Fully common. No cloud branch reaches this layer |
| L3 platform (Argo CD, Vault, ESO, Kyverno, kube-prometheus-stack) | Common chart and values; cloud differences confined to the smallest value diff |
| L4 applications | Fully common. Only endpoints are injected |

Draw the line too high and manifests fork once per cloud; too low and the Terraform modules become
a lowest-common-denominator conditional. When three or more differences cannot be expressed in
common, the answer is separation, not abstraction. See
[`rules/infra/multi-cloud.md`](../rules/infra/multi-cloud.md).

### 2. Four environments, with unequal evidence

| Environment | What the bundle has | What the output says |
|-------------|--------------------|----------------------|
| `local` | Nothing at all | "Outside the bundle's scope" — grounded in official docs or the skills' own stated conventions |
| `test` | Observed implementation (direct apply) | Citable as fact |
| `staging` | Observed implementation (Argo CD GitOps) | Citable as fact |
| `production` | **No implementation, guidance only** | "The investigated repositories contain no production implementation", then staging + approval / protection / sync windows, recorded as an ADR |

This unevenness is the most useful thing the plugin knows. A tool that presented all four
environments with equal confidence would be inventing the two it has no evidence for. See
[`rules/infra/environments.md`](../rules/infra/environments.md).

Across environments, **base, chart and image digest stay identical**; differences are value
differences in an overlay or in values. `if env == "production"` never enters a base.

### 3. One resource, one owner

A resource managed by two or more of Terraform / Argo CD / CI / manual operation is the
highest-priority finding the review has. `/infra:design` builds the ownership table and verifies
it immediately; `/infra:review` builds the ownership map before anything else, because without it
the other findings cannot be ranked.

### 4. The bundle is the source

Claims carry a citation (`[foundation/terraform.md]`). What the bundle does not cover is *said* to
be uncovered rather than filled in from memory. The bundle's own three tiers survive into the
output: **observed implementation** is fact, **design guidance** is a recommendation with a source,
**open question** stays open in the deliverable's closing section.

The observed tier is scoped to two specific commits. Where a real repository is available, the
repository is the fact and the bundle is the standard — the difference gets reported.

## A worked flow

```bash
# 1. Triage — routes to a mode, settling bundle / freshness / environment / cloud
/infra:start ./platform

# or go straight to a mode when those are already known
/infra:design ./platform --env=staging --env=production --cloud=aws --cloud=azure
/infra:implement ./platform --env=staging --cloud=aws
/infra:review ./platform --env=production --cloud=aws
```

Design → **user confirmation** → implement. A compound request ("design it and build it") is split
deliberately; implementation never proceeds on an unagreed design.

Deliverables land in `reports/08_infrastructure/` when `work/pipeline-progress.json` exists, and in
the target repository's `docs/infra/` otherwise:

```
reports/08_infrastructure/
├── infra-design-<system>.md        # /infra:design
├── env-matrix-<system>.md          # /infra:design
├── adr/adr-<NNN>-<slug>.md         # /infra:design
└── reviews/review-<target>-r<n>.md # /infra:review — round 2+ opens with a reconciliation
```

## Where it meets the architect pipeline

| Architect | Infra | Boundary |
|-----------|-------|----------|
| `/architect:design-infrastructure` | `/infra:design` | Logical vs. concrete. Architect decides the infrastructure as one phase of the design pipeline; infra turns it into a multi-cloud, four-environment configuration |
| `/architect:generate-infra-code` → `generated/` | `/infra:implement` | Output location. Codegen emits scaffolding plus the quality-gate CI workflow into `generated/`; `/infra:implement` writes merge-bound code into the real infrastructure repository |
| `/architect:design-security` · `design-observability` · `design-disaster-recovery` | sections of `/infra:design` | Policy vs. means. Architect sets the authorization model, SLI/SLO and RTO/RPO; infra decides Vault / ESO / Prometheus / Kyverno and how they are deployed |
| `/architect:review-operations` | `/infra:review` | Artefact. Architect reviews operational readiness in design documents; infra reviews Terraform, manifests and CI — and adds ownership overlap, digest continuity and secret exposure, which architect has no checks for |

Running the architect pipeline first is not required, but its
`reports/03_design/target-architecture.md` and `reports/08_infrastructure/*.md` are read as inputs
when they exist.

## Things worth knowing before the first run

- **Kyverno `ClusterPolicy` is on a clock.** `kyverno.io/v1 ClusterPolicy` is deprecated and v1.20
  (planned October 2026) removes it. This is why `security/kyverno.md` carries an earlier
  `stale_after` than the rest of the bundle, and why the review lists it as the first known issue.
- **The test/staging asymmetry is deliberate.** Direct apply in test, GitOps in staging, is a
  design decision in the observed implementation — not a defect to report. What is worth reporting
  is that the asymmetry is undocumented, or that test has no drift re-creation procedure.
- **Promotion moves a digest**, not code and not a tag. Every promotion commit must trace back to
  the source digest, the build pipeline and the signature.
- **Versions are looked up, never recalled** — the same rule the rest of the repository follows
  ([`rules/dependency-versions.md`](../rules/dependency-versions.md)).
- **Implementation runs on sonnet.** When it hits genuinely hard ground — a complex migration,
  state surgery, a CRD upgrade — it will say so and suggest `/model opus` rather than pushing
  through.

## Rules the skills read

| Rule | Covers |
|------|--------|
| [`rules/okf-k8s-tf-bundle.md`](../rules/okf-k8s-tf-bundle.md) | Resolving the bundle, the topic map, the three tiers, freshness, citation form, source precedence |
| [`rules/infra/environments.md`](../rules/infra/environments.md) | The four environments, coverage, parity, promotion, the local-relaxation table, the review checklist |
| [`rules/infra/multi-cloud.md`](../rules/infra/multi-cloud.md) | The portability boundary, the cloud service mapping, state boundaries, delivery and observability across clouds, anti-patterns |
