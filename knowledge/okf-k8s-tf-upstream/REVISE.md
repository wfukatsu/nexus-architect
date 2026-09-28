# Revising the k8s-tf bundle from its upstream

Instructions for the reviser — the Claude step of `.github/workflows/refresh-okf-k8s-tf.yml`, or a
person (or a local `claude` session) doing the same by hand after
`tools/update-okf-bundle.sh update --bundle=k8s-tf`. The result is always a pull request a human
reviews; nothing here is merged unread.

## Inputs

| File | What it is |
|------|------------|
| `knowledge/okf-k8s-tf-upstream/REPORT.md` | This run's findings: **Bundle documents to re-verify** (and why), redirected pages, release table, documents past `stale_after` |
| `knowledge/okf-k8s-tf-upstream/pages/*.md` | The freshly extracted text of every cited public page. The first comment line names its source URL and the bundle documents that cite it |
| `knowledge/okf-k8s-tf-upstream/state.json` | Per page the content hash and outline; per technology the latest stable release |
| `knowledge/okf-k8s-tf/**/*.md` | The bundle — what you revise |

## Scope — which documents

Every document listed under **Bundle documents to re-verify**, plus every document listed under
**Past `stale_after`**. No others. If the report lists none, change nothing and say so.

## The one rule that cannot bend: the three tiers

Each bundle document separates three kinds of statement (`architecture/technology-stack.md`, 読み方):

| Tier | Revise from public sources? |
|------|-----------------------------|
| **対象実装** (observed implementation) — facts about a snapshot of two private repositories | **Never.** The public internet says nothing about those repositories. A version the snapshot pins stays as observed, even when it is behind or EOL |
| **設計指針** (design guidance) — recommendations grounded in official documentation | **Yes** — this is what the refresh exists for |
| **確認事項** (open questions) | Add to it, never resolve it. A pinned version that is now behind, EOL, or facing a removal is recorded here as a question for the platform |

## Per document

1. Read the document, then the page text in `pages/` for each of its `sources` (match on the URL in
   the page's first comment line). Read the page itself with WebFetch only when the local text is
   missing or truncated.
2. For each design-guidance statement, check it against the current page:
   - still supported → leave the wording alone (do not rephrase for style);
   - contradicted, superseded or deprecated upstream → revise it, keeping the `[source-id]`
     citation that now supports it;
   - no longer supported by any cited source → remove it, or move it to 確認事項 as a question.
3. Version and lifecycle notes (deprecations, removals, support windows — e.g. Kyverno's
   `ClusterPolicy` removal): update them from the release table and the pages, with the release
   and date stated.
4. A cited page that **redirected**: set its `resource` to the final URL from REPORT.md, keep its
   `id`. A page that no longer exists: find its successor on the same official site, or drop the
   source and every claim that rested only on it.
5. New sources only when a revision needs one, only public official documentation, in the same
   `{ id, resource, title, author }` form. Never a `gitlab.com/scalar-labs/` URL.
6. Frontmatter of every document you re-verified (revised or not):
   - `verified: { by: "process:official-document-cross-check", at: "<run date>T00:00:00+09:00" }`
   - `stale_after:` the run date plus three months — or earlier, when a removal or EOL the document
     warns about falls inside that window; state the reason in the document (as Kyverno does).
   - `status` stays `stable` unless the document now describes something upstream has deprecated.

Keep the documents in **Japanese**, in their existing voice and section structure. They are the
bundle's source text; the repository's English-only convention does not apply to them
(`knowledge/OKF-K8S-TF-PROVENANCE.md`, Language).

## After the documents

1. Append to `knowledge/okf-k8s-tf/log.md` a section for the run date: which documents were
   re-verified, what was revised in each (one line apiece), and which upstream change caused it.
2. Write `knowledge/okf-k8s-tf-upstream/REVISION.md` (English): per document, *revised* or
   *re-verified, unchanged*, with the reason; then anything you could not decide, as questions for
   the reviewer. It becomes the pull request's description.
3. Run both suites and fix what they report; do not finish with either failing:
   ```bash
   python3 skills/infra/infra-contract.test.py
   python3 tools/lib/okf_upstream.test.py
   ```

## Do not

- touch any file outside `knowledge/okf-k8s-tf/` and `knowledge/okf-k8s-tf-upstream/REVISION.md`;
- change `index.md`'s structure, add or rename documents (the topic map in
  `rules/okf-k8s-tf-bundle.md` would no longer match — the suite checks it);
- copy page text into the bundle — summarise and cite, as the bundle already does;
- commit or open the pull request yourself — the workflow does that.
