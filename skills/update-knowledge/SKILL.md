---
description: |
  Fetch or update an OKF knowledge bundle — ScalarDB/ScalarDL, or the vendored Kubernetes/Terraform
  platform bundle.
argument-hint: '[--latest] [--status] [--bundle=<name>]'
model: haiku
---

# Knowledge Bundle Update

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

**Usage:** `/architect:update-knowledge [--latest] [--status] [--bundle=<name>]`

Run with no flag to make the bundle available locally (first fetch); --latest pulls the newest
bundle from remote; --status reports the resolved path, commits, and bundled versions; --bundle
selects which bundle (scalardb, the default, or k8s-tf).

## Desired Outcome

The OKF knowledge bundle the caller named is present locally and, where it has a remote, updated
to that remote's newest state — so the skills that treat it as their primary source can ground
decisions in version-pinned documentation rather than model memory.

## The Two Bundles

| `--bundle=` | Covers | Obtained by | Rule |
|-------------|--------|-------------|------|
| `scalardb` (default) | ScalarDB / ScalarDL / ScalarDB Saga | git submodule `knowledge/okf-scalardb-scalardl`, else a shallow clone cache. **Has a remote** | @rules/okf-knowledge-bundle.md |
| `k8s-tf` | Kubernetes / Terraform / Helm / Kustomize / Argo CD / GitLab CI / Vault / Prometheus / Kyverno | **Vendored** at `knowledge/okf-k8s-tf`. Its origin repository was deleted; its **upstream is the public documentation it cites**, collected into `knowledge/okf-k8s-tf-upstream/` | @rules/okf-k8s-tf-bundle.md |

That difference is the one thing to get right when reporting: `--latest` on `k8s-tf` does **not**
rewrite the bundle. It collects the public upstream — the text of every cited official page, held
locally in the git-ignored `knowledge/okf-k8s-tf-upstream/pages/`, and the latest release of every
technology — and writes what moved, and which documents await re-verification, to
`knowledge/okf-k8s-tf-upstream/REPORT.md`. Revising the documents is `/architect:revise-knowledge`.
The user should learn from the output which documents now await re-verification, rather than
assume the bundle was refreshed. See
`knowledge/OKF-K8S-TF-PROVENANCE.md`.

## Execution

All modes run one script: `${CLAUDE_PLUGIN_ROOT}/tools/update-okf-bundle.sh`, which resolves the
bundle in the same order as its rule and prints the resolved root.

| Invocation | Command | Effect |
|------------|---------|--------|
| `/architect:update-knowledge` | `tools/update-okf-bundle.sh` | Ensure the bundle is available locally; fetches from remote only if absent (submodule init, else cache clone). No-op when present. |
| `/architect:update-knowledge --latest` | `tools/update-okf-bundle.sh update` | Fetch the newest bundle from remote. On the submodule this moves the pinned commit; on the cache it fast-forwards to `origin/main`. |
| `/architect:update-knowledge --status` | `tools/update-okf-bundle.sh status` | Show resolved path, local commit vs remote `main`, and the bundled products with their latest versions. |
| any of the above `--bundle=k8s-tf` | same, with `--bundle=k8s-tf` | Operates on the vendored platform bundle. `--status` reports the OKF version, document count, earliest `stale_after`, the last upstream check and sections; `--latest` collects the public upstream and reports the documents to re-verify. |

After running, report to the user:
1. The resolved path and whether anything was fetched
2. For `scalardb`: the product/version table from `status` (run it after `update`)
3. For `k8s-tf`: the earliest `stale_after` from `status` — a document past that date is
   re-verified against official documentation before being quoted as current. After `--latest`,
   also the "Bundle documents to re-verify" table and any release the bundle is behind on, from
   `knowledge/okf-k8s-tf-upstream/REPORT.md`, and that `/architect:revise-knowledge` revises them
4. When `--latest` moved the submodule pointer: remind that the change is a modification in the
   parent repository — commit it to pin the new bundle state, or leave it uncommitted to discard

## Failure Handling

- Script exit 1 with no network: report that the bundle could not be fetched and that
  ScalarDB/ScalarDL skills will fall back to online docs labeled as not version-pinned
- Never edit files under `knowledge/okf-scalardb-scalardl/` — the bundle is generated upstream;
  changes belong in the OKF-ScalarDB-ScalarDL repository
- Never edit files under `knowledge/okf-k8s-tf/` from this skill — it only collects; revision is
  `/architect:revise-knowledge`
- `--latest --bundle=k8s-tf` exit 1: over half the cited pages were unreachable — report a network
  problem, not a documentation change; nothing was recorded

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /scalardb:docs | Consumer — searches the ScalarDB bundle this skill fetches |
| /architect:design-scalardb, /architect:generate-scalardb-code | Consumers — ground design/implementation decisions in the ScalarDB bundle |
| /infra:start, /infra:design, /infra:implement, /infra:review | Consumers — the `k8s-tf` bundle is their primary source |
