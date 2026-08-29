---
description: |
  Generate Kubernetes manifests, Terraform modules, and Helm charts.
  Invoked via /generate-infra-code.
model: sonnet
user_invocable: true
---

# Infrastructure Code Generation

## Desired Outcome

Generate IaC code based on the infrastructure design:
- Kubernetes manifests (Kustomize base + overlays)
- Terraform modules (multi-cloud support)
- Helm values (for ScalarDB Cluster)
- NetworkPolicy and PodDisruptionBudget
- Multi-environment configuration (dev/staging/prod)
- **The CI workflow that runs the quality gate** (see below)

## Quality Gate CI

The in-session gate that `implement-backlog` runs (@rules/ai-code-quality-gate.md) is fast feedback.
**The CI run is the one that is actually enforced** — it holds for hand-written changes, for changes
made months later, and for the times nobody thought to run it. A gate that exists only as a checklist
a model is asked to follow is the weakness this pipeline is closing, so emit the CI half whenever the
project has CI.

Generate a workflow for the project's platform (GitHub Actions / GitLab CI — detect it from the repo,
never assume), running the eight stages as jobs:

| Job | Runs |
|-----|------|
| build | The project's real build target |
| unit | The unit test task with coverage verification (`jacocoTestCoverageVerification`), and the mutation run (`pitest`) scoped to `domain/` — thresholds per @rules/ai-code-quality-gate.md §Test quality, read from the build files, never re-typed in the workflow |
| contract | The named contract-test task `generate-contract-tests` wired into the build |
| integration | The integration test task, including the transaction scenarios (OCC conflict, 2PC failure, saga compensation) |
| sast | Semgrep, or the project's configured scanner |
| dependency-scan | OSV-Scanner / Dependency-Check / `npm audit`, plus Gitleaks over the change |
| image-scan | Trivy, when the pipeline builds an image |

Rules the generated workflow must satisfy:

- **A stage that cannot run fails loudly.** Never emit `continue-on-error` or `|| true` on a gate job —
  a green pipeline that skipped its scanners is worse than a red one, because it is read as evidence.
- **Never invent a command.** Every task named in the workflow is verified to exist in the project's
  build files first; a missing target is reported as a gap, not papered over with a command that
  happens to work.
- **Pin the actions and tool versions** per @rules/dependency-versions.md — a floating action tag is
  an unpinned dependency in the security path.
- **Publish the evidence.** Each job uploads its report so the gate result is inspectable after the
  fact, which is what makes stage evidence meaningful rather than ceremonial.

Stages 7–8 (API security, design↕code conformance) are model-driven and are **not** emitted as CI
jobs; the workflow records that they are covered in-session by
`/architect:verify-implementation --gate`, so their absence from CI is visible rather than silent.

## Dependency Versions

IaC is almost entirely version pins — Kubernetes `apiVersion` and cluster version, Terraform
`required_version` and provider constraints, Helm chart versions, container image tags. Follow
@rules/dependency-versions.md: resolve each from its registry (Terraform registry, chart repo, image
registry, `endoflife.date` for the supported Kubernetes window), pin **stable, non-EOL, mutually
compatible** versions, never leave a moving `:latest`/`stable` image tag in a manifest, and honour
what the target environment already runs over what is newest. Confirm the version decision table per
`--confirm-versions` / `--no-confirm-versions` / `options.confirm_versions`, and record it with the
generated IaC plus `work/version-decisions.json`.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/08_infrastructure/ | Required | /architect:design-infrastructure |
| reports/03_design/target-architecture.md | Recommended | /architect:design-microservices |

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `generated/infrastructure/k8s/` | Kubernetes manifests |
| `generated/infrastructure/terraform/` | Terraform modules |
| `generated/infrastructure/helm/` | Helm values |
| `generated/infrastructure/ci/` | The quality-gate workflow for the detected CI platform |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-infrastructure | Input source |
| /architect:generate-contract-tests | Input source — the named contract-test task the CI workflow invokes |
| /architect:verify-implementation | Related — runs the same gate in-session; the CI workflow is its enforced half |
| /architect:generate-docs | Downstream — run after generation to write the README and the `operations` docs for the emitted IaC |
