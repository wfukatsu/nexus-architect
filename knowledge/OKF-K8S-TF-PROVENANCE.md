# Provenance: `knowledge/okf-k8s-tf/`

`knowledge/okf-k8s-tf/` is an OKF v0.2 knowledge bundle covering Kubernetes / Terraform /
GitOps platform engineering. It is **vendored** — checked into this repository as real files —
rather than pulled in as a git submodule the way `knowledge/okf-scalardb-scalardl/` is.

## Why vendored rather than a submodule

The bundle's origin repository was **scheduled for deletion on 2026-08-19** (already renamed to
`okf-k8s-tf-deletion_scheduled-85532852`). A submodule pointing at a repository that is about to
disappear resolves to nothing on the next clone. Since `@rules/okf-k8s-tf-bundle.md` treats this
bundle as the *primary source* for `/infra:*` — not a convenience cache — losing it would leave
those skills with no grounds to answer from.

There is therefore **no origin repository to update from**.

## Where updates come from instead (since 2026-09-28)

The bundle's design-guidance tier (設計指針) was written from public official documentation, and
every document names those pages in its frontmatter `sources`. That documentation is the bundle's
upstream now:

| Piece | Role |
|-------|------|
| `tools/refresh-okf-k8s-tf.py` (`tools/update-okf-bundle.sh update --bundle=k8s-tf`) | Fetches every cited public page and every release feed in `knowledge/okf-k8s-tf-upstream/sources.yaml` from the internet |
| `knowledge/okf-k8s-tf-upstream/pages/` | The extracted page text, held locally. **Git-ignored**: it is third-party documentation under mixed licences, and this repository is public |
| `knowledge/okf-k8s-tf-upstream/state.json`, `REPORT.md` | Committed: per page a content hash and outline, per technology the latest stable release, and what moved since the previous run |
| `.github/workflows/refresh-okf-k8s-tf.yml` | Every Monday 23:00 JST, no model: collect, rewrite redirected source URLs, list the documents awaiting re-verification (`state.json` `pending`), open one pull request |
| `/architect:revise-knowledge` (`skills/revise-knowledge/SKILL.md`) | On demand, Claude: re-verify the pending documents against the fresh pages and revise the guidance that fell behind — the only path by which bundle prose changes |

The observed-implementation tier (対象実装) is **not** part of that upstream. It describes the two
private repositories below at fixed commits; those repositories are never fetched by this
repository (it is public), so nothing here can revise that tier. A version the snapshot pinned
stays as observed, and a newer release is recorded as an open question, not substituted.

## Chain of custody

| Step | Source | Commit | Date |
|------|--------|--------|------|
| 1. Original bundle | `gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/okf-k8s-tf` | `5aaa7716ed0377af02b876f48f601f11414ef886` | ingested 2026-08-19 |
| 2. Vendored into the infra-design plugin | `gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infra-design-plugin` | `6a834aa` | 2026-08-19 |
| 3. Vendored here | this repository | — | 2026-08-19 |

Step 1's history was a single commit ("Add AIDD infrastructure OKF knowledge bundle"), so no
history was lost in vendoring. The bundle content is byte-identical to step 2.

## What the bundle itself is pinned to

`architecture/technology-stack.md` is an investigation snapshot of two repositories. Every
statement the bundle makes as **fact** ("対象実装") is a fact about these commits and nothing else:

| Repository | Commit |
|------------|--------|
| `aidd-infrastructure` | `ed2689dc47ade5b5ae5c0529ad39eaba403de279` |
| `aidd-ci-templates` | `44139cad79c8d8255ef81b0109e5b10f119b1612` |

This is why `@rules/okf-k8s-tf-bundle.md` requires the three-way split between *fact*,
*design guidance* and *open question* to survive into every output: outside those two
repositories, the bundle's "fact" tier is evidence, not authority.

## Language

The bundle is written in Japanese and is kept **unmodified**. The repository convention that
skill prose and rules are English applies to what this repository authors, not to a vendored
external source — translating it would make it something other than the source it cites.
