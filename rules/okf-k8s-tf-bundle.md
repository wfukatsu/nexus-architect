# OKF Knowledge Bundle (Kubernetes / Terraform / GitOps)

Version-pinned platform-engineering documentation, vendored at `knowledge/okf-k8s-tf/` as an
**OKF v0.2** bundle (23 documents). It is the **primary source** for every `/infra:*` skill:
Terraform, Kubernetes, Helm, Kustomize, Argo CD, GitLab CI/CD, Docker + Cosign, Vault, External
Secrets, Prometheus/Grafana and Kyverno.

Applies whenever a skill **designs, implements or reviews infrastructure** — IaC, cluster
configuration, delivery pipelines, secrets, observability or admission policy.

The relationship to `@rules/okf-knowledge-bundle.md` is parallel, not nested: that bundle is
authoritative for ScalarDB/ScalarDL behaviour, this one for the platform underneath. A ScalarDB
Cluster running on Kubernetes is in scope for both — pin each bundle separately and cite each for
what it actually covers.

## 1. Resolve the bundle

One command performs the resolution:

```bash
${CLAUDE_PLUGIN_ROOT}/tools/update-okf-bundle.sh status --bundle=k8s-tf
```

Also exposed as `/architect:update-knowledge --status --bundle=k8s-tf`. Manually, resolve in this
order and use the first hit:

| Order | Path | Purpose |
|-------|------|---------|
| 1 | `$NEXUS_OKF_K8S_TF` (or `$INFRA_DESIGN_OKF`) | Explicit override by the user |
| 2 | `${CLAUDE_PLUGIN_ROOT}/knowledge/okf-k8s-tf` | The vendored bundle that ships with this repository |
| 3 | `~/.cache/nexus-architect/okf-k8s-tf` | A local copy, if one was placed there |

Call the resolved root `$OKF` and read `$OKF/index.md` first.

**There is no remote.** The origin repository was deleted on 2026-08-19, which is why the bundle
is vendored rather than a submodule (`knowledge/OKF-K8S-TF-PROVENANCE.md`). `--latest` reports
that fact; it does not fetch. If the bundle cannot be resolved at all, **do not answer from
memory** — say the primary source is unavailable and stop, exactly as the ScalarDB rule requires.

**Never edit `$OKF`.** A correction belongs in the citing skill or in a report's "OKF addendum
candidates" section, stated as a correction. Editing a vendored source with no upstream turns a
citable document into local prose that nothing can verify. If the user explicitly asks for an
update, append to `$OKF/log.md` in the same change.

## 2. Pin the target before reading anything else

Three things are fixed before a concept page is opened. Never produce an environment-agnostic or
cloud-agnostic answer.

| Question | How to decide |
|----------|---------------|
| **Environment** | One of `local` / `test` / `staging` / `production`. The bundle's coverage differs *per environment* and the difference is load-bearing (§4). Ask when unspecified; when several are in scope, write one section per environment. See @rules/infra/environments.md |
| **Cloud** | AWS / Azure / GCP — which clouds, in which environments. Fill the cloud × environment grid before designing. See @rules/infra/multi-cloud.md |
| **Target repository** | Whether real IaC exists to read. When it does, the repository is the fact and the bundle is the standard: report the difference rather than describing the bundle as if it were the code |

## 3. Topic → document map

`$OKF/index.md` lists the documents by area. Open only what the task needs; when several rows
apply, read them all.

| Topic | Document |
|-------|----------|
| What is in use, versions, pinned provider values | `architecture/technology-stack.md` |
| Who applies what, ownership split, apply flow, blast radius | `architecture/platform-architecture.md` |
| End-to-end design / build / handover checklist | `architecture/design-build-checklist.md` |
| Kong, Gateway API, cert-manager, Keycloak, Falco, Velero, Karpenter, Descheduler, Chaos Mesh, per-cloud services | `architecture/supporting-stack.md` |
| State design, module split, lock file, plan/apply permissions, upgrade, import, destroy | `foundation/terraform.md` |
| Workloads, namespaces, RBAC, NetworkPolicy, probes, PDB, Pod Security, version skew | `foundation/kubernetes.md` |
| Chart/release, values, CRDs, hooks, upgrade and rollback | `foundation/helm.md` |
| Base/overlay, image transformer, generators, render verification | `foundation/kustomize.md` |
| GitOps, app-of-apps, AppProject, auto sync, prune/selfHeal, sync waves | `delivery/argocd.md` |
| Pipeline design, pinned CI templates, OIDC, Runner/DinD, environment protection | `delivery/gitlab-cicd.md` |
| Dockerfile, image digest, keyless signing, verify, SBOM | `delivery/docker-cosign.md` |
| Vault HA, auto-unseal, policies, hardening, backup/restore | `secrets/vault.md` |
| SecretStore/ExternalSecret, refresh policy, lifecycle, rotation | `secrets/external-secrets.md` |
| Metrics/logs/traces, label cardinality, recording rules, SLO, alerts, Grafana as Code | `operations/observability.md` |
| Admission policy, image verification, Audit → Enforce, PolicyReport | `security/kyverno.md` |

Example of a multi-row topic: "secret rotation" is `secrets/vault.md` +
`secrets/external-secrets.md` + `foundation/kubernetes.md` (Configuration and Secret section).

## 4. The three tiers — keep them separate in the output

The bundle itself distinguishes three kinds of statement (`architecture/technology-stack.md`,
"how to read this"). **Collapsing them is the most damaging thing an output can do**, because it
presents a recommendation as an observed fact or an unresolved decision as settled.

| Tier | Meaning | How the output must carry it |
|------|---------|------------------------------|
| **Observed implementation** (対象実装) | A fact confirmed in the two investigated repositories | State as fact: "today the platform does X" |
| **Design guidance** (設計指針) | A recommendation whose grounds are official documentation | State as recommendation, with the source URL |
| **Open question** (確認事項) | A judgement that depends on the environment and has not been made | List it in the deliverable's closing "Open questions" section — never resolve it silently |

The observed tier is scoped to a snapshot. The bundle was written against these commits:

| Repository | Commit |
|------------|--------|
| `aidd-infrastructure` | `ed2689dc47ade5b5ae5c0529ad39eaba403de279` |
| `aidd-ci-templates` | `44139cad79c8d8255ef81b0109e5b10f119b1612` |

Outside those two repositories the observed tier is **evidence, not authority**. When real code is
available, read it and report the difference between it and the bundle first.

## 5. Environment coverage is uneven — say so

| Environment | Bundle coverage | Required posture |
|-------------|-----------------|------------------|
| `local` | **Not covered at all** | Say "outside the bundle's scope". Answer from official documentation or general principle, and do not assert |
| `test` | Observed implementation (a documented procedure or CI `kubectl apply`, applied directly) | Citable as fact |
| `staging` | Observed implementation (Argo CD app-of-apps, GitOps) | Citable as fact |
| `production` | **No observed implementation** — only design guidance | Say "the investigated repositories contain no production implementation", then present production as staging plus approval, protection and sync windows, and record the apply path as an open question |

Detail, and the four things the bundle does say about production: @rules/infra/environments.md §0.

## 6. Freshness

Every document carries `stale_after` in its frontmatter.

| Document | `stale_after` |
|----------|---------------|
| `security/kyverno.md` | 2026-10-19 |
| all others | 2026-11-19 |

When citing a document whose date has passed, **say so explicitly** — "this statement is past its
`stale_after: YYYY-MM-DD` and needs re-checking against official documentation" — and WebFetch the
official source when the claim matters. Kyverno's date is shorter on purpose: v1.20 plans to
remove `kyverno.io/v1 ClusterPolicy`, so after that date the actual release state must be checked
rather than assumed.

Since the bundle has no upstream, `stale_after` will pass for the whole bundle on 2026-11-19 and
stay passed. That is not a reason to stop citing it — it is a reason to cite it as *dated
evidence* and to verify anything version-specific against the vendor.

## 7. Citation form

Put the relative path in square brackets immediately after the claim. Where the document's
frontmatter carries a `sources` entry for the source ID, resolve it to a URL and add it.

```
Terraform state can contain secret values, so it is not committed to Git
[foundation/terraform.md].
Source: https://developer.hashicorp.com/terraform/language/state
```

A claim with no bracket is a claim the bundle does not back. Either mark it "outside the bundle's
scope" and give an official source, or move it to the open-questions list.

## 8. Precedence among sources

1. **This bundle** — authoritative for the platform's design decisions, ownership model and
   conventions, within the snapshot of §4.
2. **The target repository's real code** — where it disagrees with the bundle, the code is what
   exists. Report the difference; do not silently prefer either.
3. **Official upstream documentation** (Terraform, Kubernetes, Helm, Argo CD, Vault, Kyverno …)
   via WebFetch — for anything outside the bundle, and for anything past `stale_after`. Label such
   answers as not bundle-grounded.
