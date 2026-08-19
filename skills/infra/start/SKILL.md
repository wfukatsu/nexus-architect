---
description: |
  Triage entry point for multi-cloud (AWS / Azure / GCP) x four-environment
  (local / test / staging / production) infrastructure work: resolves the OKF k8s/tf knowledge
  bundle, checks its freshness, fixes the target environment and cloud, then routes to the
  design, implement or review skill.
  /infra:start [target] [--env=<env>] [--cloud=<cloud>] to invoke.
  Use for "design the infrastructure", "write the Terraform", "review this IaC" and anything
  that does not yet name a mode. Not for application domain design (/architect:*), ScalarDB
  data modeling (/scalardb:*), or GitLab MR review write-ups (gitlab-review).
model: sonnet
user_invocable: true
---

# Infrastructure Triage and Routing

Ground every infrastructure decision in the OKF `okf-k8s-tf` bundle
(@rules/okf-k8s-tf-bundle.md) rather than in model memory, and hand the real work to the skill
that is sized for it.

## Desired Outcome

Four things are settled and passed downstream, so the mode skill never re-asks them:

1. The resolved bundle root `$OKF`, and which of its documents are past `stale_after`
2. The **target environment(s)** — `local` / `test` / `staging` / `production`
3. The **target cloud(s)** — AWS / Azure / GCP, and which environments exist in each
4. The **mode** — design, implement or review — and the target path

## Decision Criteria

| The user wants | Mode | Route to |
|----------------|------|----------|
| A configuration decided from requirements; technology selection; an approach | **design** | `/infra:design` |
| Terraform / manifests / values / CI written or fixed | **implement** | `/infra:implement` |
| Existing code or a design document assessed, with findings | **review** | `/infra:review` |

Ambiguous? Ask **one** question with AskUserQuestion. A compound request ("design it and then
build it") splits into design → user confirmation → implement; never proceed to implementation
without agreement on the design.

**Route by invoking the mode skill with the Skill tool**, passing the four settled facts as
arguments. This skill does triage only — design and review carry a higher reasoning tier
(see Model Policy).

The exception is a single factual lookup ("what does the bundle say about Vault HA?") or a
request whose whole point is the triage itself. Answer those here.

## Prerequisites

| Input | Required/Recommended | Source |
|-------|---------------------|--------|
| `knowledge/okf-k8s-tf/` (the bundle) | **Required** | Vendored; `tools/update-okf-bundle.sh status --bundle=k8s-tf` |
| The target repository or design document | Recommended | The user |
| reports/03_design/target-architecture.md | Recommended | /architect:design-microservices |
| reports/08_infrastructure/infrastructure-design.md | Recommended | /architect:design-infrastructure |

## Step 1 — Resolve the bundle

Run `${CLAUDE_PLUGIN_ROOT}/tools/update-okf-bundle.sh status --bundle=k8s-tf` and take the
resolved path as `$OKF`. The resolution order, the reason there is no remote, and what to do when
it cannot be found are all in @rules/okf-k8s-tf-bundle.md §1.

**If the bundle cannot be resolved, do not answer from memory.** It is the primary source for
this skill, not a convenience.

## Step 2 — Check freshness

Each document carries `stale_after`. When quoting one whose date has passed, say so and re-verify
against official documentation (@rules/okf-k8s-tf-bundle.md §6). `security/kyverno.md` expires
earlier than the rest, because Kyverno v1.20 plans to remove `kyverno.io/v1 ClusterPolicy`.

## Step 3 — Fix the environment

Infrastructure has four environments and **no output is produced before the environment is
settled**. Use `--env=<env>`; when absent, ask with AskUserQuestion. When several are in scope,
the deliverable gets one section per environment.

Coverage differs sharply per environment, and the difference is not cosmetic:

| Environment | Bundle | Posture in the output |
|-------------|--------|-----------------------|
| `local` | **Absent** | Say "outside the bundle's scope". Do not assert |
| `test` | Observed implementation (a procedure or CI `kubectl apply`, direct apply) | Citable as fact |
| `staging` | Observed implementation (Argo CD app-of-apps, GitOps) | Citable as fact |
| `production` | **No observed implementation** — guidance only | Say the investigated repositories contain no production implementation, and present production as staging plus approval/protection/sync windows |

Full matrix and promotion path: @rules/infra/environments.md.

## Step 4 — Fix the cloud

Multi-cloud is the default premise; never answer as if one cloud were assumed. Use
`--cloud=<cloud>`; when absent, ask. Settle the four items in @rules/infra/multi-cloud.md §0 and
fill the cloud × environment grid before routing — an empty cell means "not deployed here", and
must not be left implicit.

## Step 5 — Route

Pick the mode from Decision Criteria and invoke the corresponding skill, passing environment,
cloud, target path and `$OKF`.

## Non-Negotiable Rules

These bind the mode skills too.

1. **Cite the bundle for anything it covers.** Never write from memory. Attach
   `[foundation/terraform.md]`-style sources to each claim (@rules/okf-k8s-tf-bundle.md §7).
2. **Say "outside the bundle's scope" when it is.** Then WebFetch official documentation, or
   leave it as an open question. Do not assert.
3. **Keep fact, guidance and open question separate.** The bundle itself distinguishes observed
   implementation / design guidance / open question; the output preserves the same three tiers
   (@rules/okf-k8s-tf-bundle.md §4).
4. **Multi-cloud is the default.** Pass every conclusion through the portability boundary in
   @rules/infra/multi-cloud.md before writing it.
5. **There are four environments.** Differences stay in overlay and values as **value
   differences**; base, chart and image digest stay identical everywhere. Never write
   `if env == "production"` into a base (@rules/infra/environments.md §2).
6. **One resource, one owner.** A resource managed by two or more of Terraform / Argo CD / CI /
   manual is the highest-priority finding there is — in a design, in an implementation, or as
   something a review missed [architecture/platform-architecture.md].
7. **Pin versions.** Terraform, providers, charts, images and CI templates never reference a
   moving target (`main`, `latest`, a floating tag). Resolve the version rather than recalling it
   (@rules/dependency-versions.md).
8. **No secrets in deliverables.** Never propose putting plaintext secrets in tfvars, values, a
   plan artifact, CI logs or Git.
9. Write deliverables in the project's `options.output_language`; code identifiers stay English.

## Output Location

The user's choice wins. Otherwise resolve `$OUT` in this order:

1. A location the user named
2. `reports/08_infrastructure/` — when `work/pipeline-progress.json` exists (pipeline context)
3. `docs/infra/` at the target repository root (`git rev-parse --show-toplevel`), or in the
   working directory when there is no repository context

| Deliverable | Path | File name |
|-------------|------|-----------|
| Design document | `$OUT/` | `infra-design-<system>.md` |
| Environment matrix | `$OUT/` | `env-matrix-<system>.md` |
| ADR | `$OUT/adr/` | `adr-<NNN>-<slug>.md` |
| Review report | `$OUT/reviews/` | `review-<target>-r<round>.md` |

- Review rounds are numbered from the existing files; round 2 and later open with a
  reconciliation against the previous round (resolved / still open / new).
- Anything written under `reports/` must carry YAML frontmatter and valid Mermaid — the
  repository's hooks enforce both (@rules/output-conventions.md).
- **Never write deliverables into `${CLAUDE_PLUGIN_ROOT}`.** The plugin is replaced on update and
  the deliverable would be lost.

## Model Policy

| Skill | Model | Why |
|-------|-------|-----|
| `/infra:start` | sonnet | Triage: resolution, freshness, environment/mode. The heavy work is delegated |
| `/infra:design` | opus | Design judgement, trade-offs, ADRs. A wrong structural call propagates to everything downstream |
| `/infra:implement` | sonnet | The conventions are written down and verification commands back them. Highest output volume, so the largest cost saving |
| `/infra:review` | opus | Multi-step reasoning and finding what is absent. A missed finding stays as risk |

The criterion is "how hard the error is to undo" times "how many tokens it generates". When
implementation hits genuinely hard ground — a complex migration, state surgery, a CRD upgrade —
do not push through on sonnet; suggest the user switch with `/model opus`.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /infra:design, /infra:implement, /infra:review | The three modes this skill routes to |
| /architect:design-infrastructure | Upstream — the logical infrastructure design this refines into a concrete multi-cloud configuration |
| /architect:generate-infra-code | Sibling — emits IaC into `generated/` as a pipeline codegen step; `/infra:implement` writes into a real infrastructure repository |
| /architect:design-security, /architect:design-observability, /architect:design-disaster-recovery | Upstream — policy (authorization model, SLI/SLO, RTO/RPO); this plugin decides the implementation means |
| /scalardb:* | ScalarDB schema and transaction design. This plugin treats ScalarDB only as something that runs on Kubernetes |
| /architect:update-knowledge | Reports the bundle's state (`--bundle=k8s-tf`) |
