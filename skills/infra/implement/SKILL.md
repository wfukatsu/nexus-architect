---
description: |
  Write Terraform, Kubernetes manifests, Helm values, Kustomize overlays and CI definitions from
  an agreed infrastructure design, into a real infrastructure repository. Enforces pinned
  versions, single ownership, digest continuity and no secret exposure.
  /infra:implement [target] [--env=<env>] [--cloud=<cloud>] [--auto] to invoke.
  Use for "write the Terraform", "create the manifests", "implement the CI". For IaC scaffolding
  emitted into generated/ as a pipeline codegen step, use /architect:generate-infra-code instead.
model: sonnet
user_invocable: true
---

# Infrastructure Implementation

## Desired Outcome

Code that can be applied to the named environment, in which every version is pinned, every
touched resource has a single identifiable owner, the image digest is continuous from build to
deploy, and no secret value appears in any artifact — accompanied by the verification commands
that were actually run and their results.

## Decision Criteria

| Situation | Do this |
|-----------|---------|
| No design exists | Run a short design pass first — at minimum the ownership split, target clouds and target environments. Do not start writing without them |
| The repository and the bundle disagree | **Follow the repository** and report the difference. The bundle is a snapshot of specific commits (@rules/okf-k8s-tf-bundle.md §4) |
| The write target is owned by something else | Stop. Never hand-edit a Terraform-managed resource, never touch an Argo CD-managed resource from CI [architecture/platform-architecture.md] |
| A version must be written | Look it up; never recall it, and never copy it from an example in this repository (@rules/dependency-versions.md) |
| The work hits hard ground (complex migration, state surgery, CRD upgrade) | Do not push through. Say so and suggest `/model opus` |

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| `knowledge/okf-k8s-tf/` | **Required** | Vendored bundle (@rules/okf-k8s-tf-bundle.md) |
| The agreed design document | **Required** | /infra:design, or the user |
| The target repository | **Required** | Read its real structure before writing |

When invoked from `/infra:start`, environment, cloud, target path and `$OKF` arrive already
settled. **Do not re-ask them.**

## Step 0 — Fix the environment before writing anything

The environment changes both where the code goes and who applies it.

| Environment | Where it is written | Applied by | Bundle |
|-------------|--------------------|------------|--------|
| local | Shared base + a local overlay, plus a startup script | The developer | **Out of scope** |
| test | `kubernetes/test` or the app's `k8s/` | A documented procedure or CI `kubectl apply` | Observed implementation |
| staging | `kubernetes/staging` (the app-of-apps entry `kustomization.yaml`) | Argo CD | Observed implementation |
| production | To be decided (follows staging) | Argo CD + approval | **No observed implementation** |

Production code is written as staging's configuration **plus** approval, protection and sync
windows — stating explicitly that the bundle has no precedent for it
(@rules/infra/environments.md §0, §4).

## Step 1 — Read the target repository

The bundle describes specific commits. Where the real repository differs, the repository wins;
report the difference rather than quietly converging on the bundle. Confirm the owner of every
write target before writing.

## Directory Convention

Following the observed implementation
[foundation/terraform.md, architecture/platform-architecture.md]:

```
terraform/
  global/
  environments/<cloud>/<env>/infra/         # network, cluster, database, IAM, storage
  environments/<cloud>/<env>/kubernetes/    # shared components (helm_release etc.)
  modules/{aws,azure,gcp,kubernetes}/
  charts/                                   # per-environment values for upstream charts
kubernetes/
  base/          # common to every environment; no environment branching
  local/         # overlay onto base. Out of the bundle's scope (replica 1, substituted dependencies)
  test/          # overlay onto base. Applied by procedure or CI kubectl apply
  staging/       # overlay onto base. The app-of-apps entry point
  production/    # overlay onto base. To be decided (follows staging)
```

`<env>` is `test` / `staging` / `production`. **Local never enters the terraform tree** (it builds
no L1); its manifest differences live in the Kustomize overlay.

The observed implementation has only `kubernetes/test` and `kubernetes/staging`; factoring out
`base/` and adding `local/` and `production/` is **this skill's convention**, not the bundle's.
Where the existing repository is arranged differently, follow it and report the difference.

## Terraform

Mandatory [foundation/terraform.md]:

- Pin Terraform and provider versions **exactly** in the root module
- Commit `.terraform.lock.hcl` per root configuration; for several OS/arch, pre-register hashes
  with `terraform providers lock -platform=...`
- Remote backend, encrypted, access-controlled, with locking and versioning/backup. State never
  goes in Git
- Modules are **high-level capabilities** (`network`, `database`, `kubernetes-cluster`). Keep the
  module tree shallow and prefer composing small modules
- `variables.tf` carries type, description and validation; `outputs.tf` carries description
- Prefer implicit dependencies through value references; use `depends_on` only where order cannot
  be expressed as a value
- Rename and refactor with `moved` blocks rather than relying on `terraform state mv`
- `sensitive = true` suppresses display; it does not remove the value from state. Keep secret
  values out of tfvars, plan artifacts, CI logs and `local-exec` arguments

For multi-cloud, align L1 module output names across the three clouds
(@rules/infra/multi-cloud.md §1).

Minimum verification after generating:

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform plan -detailed-exitcode   # only where credentials are available
```

## Kubernetes Manifests

Mandatory [foundation/kubernetes.md]:

- Never create bare Pods; use a controller (Deployment / StatefulSet / DaemonSet / Job)
- Stateless services: several replicas, readiness / liveness / startup probes, requests / limits
- PDBs consistent with replica count, rollout strategy and node upgrades
- Topology spread / anti-affinity across zone and node failure domains
- StatefulSets: design storage class, backup, restore, volume expansion and zone constraints
- Jobs: state retry, deadline, idempotency and cleanup
- Per namespace, provide naming / quota / limits / default-deny NetworkPolicy as a set
- Per ServiceAccount, RBAC and workload identity. No `cluster-admin`, no wildcard verbs or
  resources, no default ServiceAccount token
- Pod Security Standards: non-root, dropped capabilities, seccomp, read-only root filesystem
- Reference and verify images by digest and signing identity, never by tag

## Helm

[foundation/helm.md]

- Pin repository, chart and version. Record chart version, app version and image version as
  distinct facts
- `values.yaml` holds defaults, environment differences go in separate values, secret values come
  from an external secret store. Even `set_sensitive` can persist in Terraform state — prefer a
  design that never passes the secret at all
- One owner per release: Terraform. Never touch the same release from Argo CD or by hand
- CRDs: check upgrade ordering, conversion webhooks, stored versions and what survives uninstall.
  Treat rollback with the same care as a database schema migration
- If hooks are used, they are idempotent and have a cleanup policy and a TTL

Verification: run `helm lint`, `helm template` and a server-side dry-run equivalent in CI.

## Kustomize

[foundation/kustomize.md]

- The base carries common identity / selectors / ports / probes; the overlay carries **only the
  differences** — replicas, resources, hostname, storage, environment labels. Never branch the
  base on environment
- **Every environment difference is a value difference in an overlay**, local included. Wanting to
  edit the base for local use is a sign the base has drifted toward one environment
  (@rules/infra/environments.md §2)
- Keep the same difference axes (replicas / resources / storage / hostname) across overlays, and
  do not let patch style diverge between them
- Make each patch target unique, so an upstream change cannot make it hit a different resource
- Change images with the `images` transformer, never by string substitution in YAML
- Never commit plaintext secrets to a SecretGenerator; only the ExternalSecret declaration is in Git
- Pin remote bases to an immutable commit or tag, not a moving branch

Verification:

```bash
kubectl kustomize <overlay>
kubectl apply --server-side --dry-run=server -k <overlay>
```

Keep the Kustomize version used by Argo CD, by CI and locally in step.

## GitLab CI

[delivery/gitlab-cicd.md]

- Pin shared template includes to a release tag or commit SHA. Never `main` or `latest`
- Job-name collisions cause unintended overrides under merge semantics. Define the public
  interface and the hidden job names
- Scan / sign / verify all receive the **same immutable digest** the build produced
- A security job marked to allow failure does not make green mean safe. Define result collection
  and the severity gate separately
- Authenticate with GitLab ID tokens (OIDC) for short-lived credentials. No long-lived cloud keys
  in CI variables. Restrict audience, project path, ref type and protected-ref claims in the trust
  policy. Separate the plan / apply / deploy / sign roles
- DinD requires privileged mode and materially weakens container isolation. Keep it dedicated,
  ephemeral and limited to trusted projects; never put untrusted fork/MR pipelines and production
  credentials on the same runner. Pin to a patch or digest rather than a major tag like
  `docker:27`. Enable TLS
- Control apply/deploy with protected branches and tags, protected environments, approvals and
  `resource_group`

## Docker

[delivery/docker-cosign.md]

- Multi-stage builds; a `.dockerignore` that excludes `.git`, credentials and build artifacts
- Pin the base image by version and digest — and provide an update process, since a pinned digest
  never updates itself
- Package install and cache cleanup in the same layer
- Non-root user, read-only root filesystem, explicit ports
- Keep secrets out of `ARG` / `ENV` / layers; use BuildKit secret mounts
- Capture the registry digest immediately after build, store it as an artifact, and pass **the
  same digest** to scan, SBOM, sign, deploy and the incident record. Never re-resolve from a tag

## Secrets

[secrets/vault.md, secrets/external-secrets.md]

- No plaintext secrets in Git, values or tfvars. Synchronize through Vault + ESO
- `SecretStore` (namespace-scoped) is the default; use `ClusterSecretStore` only after designing
  namespace restrictions, controller class and RBAC
- Bind Vault's Kubernetes auth role strictly to the namespace and ServiceAccount. Separate the
  application / ESO / operator / administrator policies and avoid wildcards
- State the combination of `refreshPolicy` (`Periodic` / `OnChange` / `CreatedOnce`) with
  `creationPolicy` / `deletionPolicy` that the requirement calls for. For a value that must be
  immutable after first creation, consider `CreatedOnce` plus `immutable: true` and ownership on
  the target
- Verify the application can reload the volume or env after rotation, and provide rollout
  automation where it cannot

## Per-Environment Notes

### local (outside the bundle's scope)

- Do not build L1. Terraform is generally not involved
- Keep startup to one command — a long procedure means the environment goes unused and the gap widens
- If Vault / Kyverno / the observability stack are omitted, **write that and its limits into the
  README**: "it worked locally" is not evidence of passing signature verification or admission
- No plaintext secrets in Git. Use a generator script or a Git-ignored file
- No production data
- Check the Kubernetes version can be kept in step with test and above [foundation/kubernetes.md]

### test

- The only environment where direct apply is legitimate (procedure or CI
  [architecture/platform-architecture.md]). On the CI path, separate the deploy role from
  plan / apply / sign and use short-lived OIDC credentials [delivery/gitlab-cicd.md]
- Direct apply drifts. Ship a re-creation procedure with it
- Run Kyverno in Audit and inventory the violations [security/kyverno.md]

### staging

- **CI never touches the cluster.** It updates the manifest's image reference in Git
  [delivery/argocd.md]
- Write the `prune` / `selfHeal` settings together with the break-glass procedure and drift auditing
- Leave source digest and signature tracking information in the promotion commit
  [foundation/kustomize.md]

### production

- No implementation fact in the bundle. Write it as staging **plus** something, and name what the
  addition is
- Protected branches/tags, protected environments, approvals, `resource_group`
  [delivery/gitlab-cicd.md]
- Sync windows / manual approval [delivery/argocd.md]
- Vault in HA — three or more nodes, spread across zones, PDB, anti-affinity [secrets/vault.md]
- Kyverno in Enforce, but only after the canary namespace and rollback path exist
  [security/kyverno.md]
- Untrusted fork/MR pipelines never share a runner with production credentials
  [delivery/gitlab-cicd.md]

## Options

| Flag | Effect |
|------|--------|
| `--env=<env>` | Target environment: `local` / `test` / `staging` / `production`. Repeatable |
| `--cloud=<cloud>` | Target cloud: `aws` / `azure` / `gcp`. Repeatable |
| `--auto` | Do not ask. Unresolved items become open questions rather than questions |

## Output

Code is written into the target repository at the paths above — **never into
`${CLAUDE_PLUGIN_ROOT}`**, and never into `generated/` (that is
`/architect:generate-infra-code`'s output location).

Every delivery is accompanied by:

1. **The target environment**, and whether the same change must also land in other environments
2. The verification commands run and their results — or, where one could not run, why
3. The owner of each resource touched (Terraform / Argo CD / CI / the developer's machine)
4. Related changes that must follow, per the change-impact matrix in the design
5. The effect on environment parity — whether base / chart / digest identity still holds
6. Open questions: what could not be decided because it depends on the environment

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /infra:design | Upstream — supplies the design this implements |
| /infra:review | Reviews what this wrote |
| /architect:generate-infra-code | Sibling — emits IaC scaffolding into `generated/` plus the quality-gate CI workflow, as a pipeline codegen step. This skill writes merge-bound code into a real infrastructure repository |
| /architect:update-knowledge | Reports the bundle's state (`--bundle=k8s-tf`) |
