# Changelog

All notable changes to Nexus Architect are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Version numbers refer to the per-plugin versions in `.claude-plugin/marketplace.json`;
all three plugins (`product`, `architect`, `scalardb`) are released together under one number.

## [Unreleased]

## [0.18.0] - 2026-07-28

### Added
- **ScalarDB / ScalarDL implementation decisions are now grounded in version-pinned official
  documentation.** The [OKF-ScalarDB-ScalarDL](https://github.com/wfukatsu/OKF-ScalarDB-ScalarDL)
  bundle — the complete developers.scalar-labs.com docs split per product and per version
  (ScalarDB 3.14–3.18, ScalarDL 3.10–3.13, ScalarDB Community 3.4–3.13; 1,800 concepts) — is
  vendored as a git submodule at `knowledge/okf-scalardb-scalardl/`, so skills answer from the
  release a project actually runs instead of model memory or unpinned "latest" docs.
  - `rules/okf-knowledge-bundle.md` (new shared contract): resolve the bundle (submodule →
    `~/.cache/nexus-architect/` shallow clone → online docs explicitly labeled as **not**
    version-pinned), pin **product, version, and edition** before reading anything, filter
    concepts by `lifecycle_phase` (design / implement / operate) mapped to the skill families,
    never mix versions, cite each concept's canonical `resource` URL, and pin dependencies with
    the frontmatter `patch_version` — feeding the `rules/dependency-versions.md` /
    `work/version-decisions.json` flow.
  - `tools/update-okf-bundle.sh` + `/architect:update-knowledge` (new skill, haiku): fetch,
    update, and inspect the bundle from remote — no-arg *ensure* fetches only when absent,
    `update` pulls the newest state (moving the submodule pointer, to be committed to pin it),
    `status` reports the resolved path, local vs remote commits, and bundled versions.

### Changed
- **19 skills across all three plugins now consult the bundle.** `architect`: `design-scalardb`
  (Context7 demoted to fallback), `design-scalardb-analytics`, `select-scalardb-edition`
  (edition claims verified against frontmatter `editions` / `feature_status`),
  `generate-scalardb-code` (API signatures, config keys, and exception retryability come from
  the pinned release's `implement`-phase concepts), `review-scalardb` (findings cite `resource`
  URLs as evidence), `define-requirements`, `migrate-database`. `scalardb`: `docs` now searches
  the bundle first with WebFetch demoted to an explicitly-labeled fallback; `build-app`,
  `model`, `config`, `crud-ops`, `jdbc-ops`, `error-handler`, `scaffold`, `review-code`,
  `migrate`, `local-env` gain a knowledge-grounding note. `product`: `design-architecture`
  grounds ScalarDB / ScalarDL fitness claims in the bundle.
- Entry docs kept in sync: `CLAUDE.md` (Rules & References row, Conventions, command reference),
  `AGENTS.md` and `OMNIGENT.md` (grounding rule + update commands), `README.md` (clone with
  `--recurse-submodules`, new **ScalarDB / ScalarDL Knowledge Bundle** section),
  `rules/scalardb-coding-patterns.md` (bundle listed first in the rule index).

## [0.17.7] - 2026-07-27

### Documentation
- **How to invoke the codegen and delivery paths is now written down.** The codegen skills were
  catalogued but never explained: nothing stated that they sit outside `/architect:pipeline`, in what
  order they chain, or what each one needs before it can run — and the whole backlog-delivery family
  (`export-backlog`, `deliver-backlog`, `implement-backlog`, `review-issue`, `merge-issue`) was absent
  from `README.md` and `docs/skill-reference*` altogether, though `CLAUDE.md` documents it.
  - `README.md`: Quick Start gains the codegen and delivery entry points; a new **Code Generation &
    Delivery** workflow section lays out the four paths and the distinction that matters — path A
    emits a disposable scaffold under `generated/`, path B writes merge-bound code into the project's
    real source tree; new **Backlog Delivery** command table; the Implementation & Codegen table gains
    a *Requires* column; the dependency graph now explains the manual extension tier; new **Dependency
    Versions** section covering the v0.17.6 flags and the project-level option.
  - `docs/getting-started.md` / `_ja.md`: new §5 *Generating Code*, §6 *Delivering Code Through a
    Backlog*, §7 *Choosing Dependency Versions* (the ScalarDB and migration sections renumber to 8/9).
  - `docs/skill-reference.md` / `_ja.md`: the Implementation table gains a *Requires* column and the
    manual-tier note; new **Backlog Delivery** section with per-skill models and roles.

### Fixed
- `CLAUDE.md` claimed the manual extension tier could be invoked "via `/architect:start`". It cannot:
  `start` executes only the phases in `skill-dependencies.yaml`, and references no codegen skill.
  Corrected, with pointers to the new invocation chains.

## [0.17.6] - 2026-07-27

### Added
- **Dependency versions are looked up before they are pinned, and the confirmation is the user's
  choice** (`rules/dependency-versions.md`, new shared contract). The codegen skills wrote version
  numbers that came from model memory or from the examples inside this repo's own skill files — and
  those drift: `config`, `local-env`, `migrate` and the code-pattern references all pinned ScalarDB
  `3.16.0` while `spring-boot-integration.md` said `3.17.0`, with the current stable line at `3.18.0`
  (verified against `gh release list -R scalar-labs/scalardb` and
  `repo1.maven.org/.../scalardb/maven-metadata.xml`). A recalled version is an unverified claim, and a
  stale one ships into a real build.

  The contract applies to every generated file that pins a version — Gradle/Maven, `package.json`,
  image tags, Helm/Terraform/Kubernetes, CI runner images:
  - **Never write a version from memory.** Resolve it from the registry of record, with the lookup
    named per ecosystem: `repo1.maven.org/.../maven-metadata.xml` (**not** `search.maven.org`'s solr
    endpoint, whose default ordering returns an older release as if it were newest),
    `npm view <pkg> dist-tags --json` (the `latest` tag, not `next`/`canary`), `gh release list` (its
    `Pre-release` marker is explicit), the Docker Hub and Terraform registry APIs (Terraform's version
    array is **unsorted** — sort semver yourself), `helm search repo --versions`,
    `endoflife.date/api/<product>.json` for LTS and EOL dates, and context7 for compatibility
    statements.
  - **Choose stable, not merely newest.** No prereleases, no moving `:latest`/`stable` tags, prefer
    the ecosystem's LTS (usually *not* the highest number), never pin an EOL line, treat a
    brand-new major as a flag rather than a default, let the target project's existing
    lockfile/BOM/parent-POM win over "latest" (no ambient upgrades as a side effect), and gate the
    whole set on mutual compatibility — the newest of each is frequently not a working combination.
  - **Record the decision.** A version decision table (chosen / latest stable / released / source /
    why / rejected) goes into the artifact, mirrored to `work/version-decisions.json` and reused for
    7 days (`--refresh-versions` to re-resolve) so parallel sub-agents and later skills cannot pin two
    different versions of the same library.
  - **A failed lookup is never filled in with a guess.** Fall back to the project's existing pin, mark
    the entry `verified: false` with the reason, and surface it.

- **`--confirm-versions` / `--no-confirm-versions` + `options.confirm_versions`.** Whether the resolved
  set is confirmed with the user or adopted silently is configurable: the flag per run, the
  `work/pipeline-progress.json` option as the project default, and unset means interactive runs ask
  while `--auto` runs adopt. `/architect:start` and `/product:start` now ask for this preference
  alongside the output language, and `init-output` seeds it. Some situations ask regardless of the
  setting: a failed lookup, a brand-new major as the only current option, an EOL current pin, no
  compatible set without a downgrade, or a licensed/private registry requirement.

### Changed
- Wired the contract into every skill that emits a pinned file: `/architect:generate-scalardb-code`,
  `/architect:generate-infra-code`, `/architect:implement-backlog` (Step 5 — versions resolved once and
  handed to the sub-agents, with the project's lockfile binding), `/architect:design-infrastructure`
  (state the version *and* its support horizon), `/product:generate-frontend` (React/Vite/Storybook
  compatibility is explicit), `/scalardb:scaffold` (new Step 4), `/scalardb:config`,
  `/scalardb:local-env`, `/scalardb:build-app`, `/scalardb:migrate`.
- Stale in-text pins are no longer readable as current truth: `config`, `migrate`, `local-env`'s
  schema-loader commands and the migrate routers' `SCALARDB_TARGET_VERSION` now use version-agnostic
  placeholders, while the code-pattern references, `spring-boot-integration.md` and the migration
  templates carry an explicit dated-example banner pointing at the lookup rule.
- `/scalardb:local-env` no longer ships a moving `:latest` image tag — a compose file must pin a
  concrete tag to be reproducible.
- Entry docs kept in sync: `CLAUDE.md` (rules table, conventions, flags), `AGENTS.md` (the shell
  lookups Codex should use), `OMNIGENT.md`, and `skills/common/progress-registry.md` (which now
  documents the whole `options` block, including `confirm_versions`).

## [0.17.5] - 2026-07-27

### Added
- **Backlog checklists are now maintained as work progresses** (`skills/common/backlog-checklists.md`,
  new shared contract). The backlog family advanced status labels, progress comments and the
  manifest, but nothing ever flipped a markdown checkbox on the tracked items — and GitLab/GitHub
  render a task list as a progress counter, so a delivered Issue left its acceptance criteria and its
  box in the parent's task list unticked, under-reporting real progress to everyone reading the Epic.
  Two checklists, each with one exclusive owner:
  - **Child task list** (Epic `## Sub-Epics`, Sub-Epic `## Issues`) → `/architect:merge-issue`, and
    only when that child actually reaches `done`, since merging is what establishes it.
  - **Acceptance criteria** (Issue `## Acceptance Criteria`) → `/architect:implement-backlog`
    (implemented) then `/architect:review-issue` (verified).

  Rules the whole family follows: tick on evidence, never on intent; edit the body **in place**,
  flipping only the `[ ]` → `[x]` marker (never regenerate a body from `backlog-manifest.json`, which
  would discard human edits); idempotent re-runs; unticking allowed when a review or revert disproves
  a criterion, with a stated reason; skip entirely on the GitLab native-Epic / GitHub sub-issue path,
  where the parent carries links instead of a task list; `--dry-run` edits no body.

### Changed
- **`/architect:export-backlog`** authors both checklists as unticked `- [ ]` boxes — one per
  criterion, one per child — and ticks nothing itself. A Given/When/Then scenario now goes *inside* a
  single box: a criterion written as prose can never be ticked by the downstream skills.
- **`/architect:implement-backlog`** (Step 7) ticks the acceptance criteria its committed code
  satisfies (commit/test/doc as evidence) and names every box it left unticked in the same progress
  comment. It leaves the parent's task list alone — an Issue is not done until its PR/MR merges.
- **`/architect:review-issue`** (Step 5) reconciles the checklist against the review verdict before
  raising the PR/MR: confirmed criteria ticked, refuted ones unticked with the reason on the Issue,
  and anything still open surfaced in the PR/MR body.
- **`/architect:merge-issue`** reports unticked acceptance criteria at the **Step 2 confirmation
  gate** — deliberately not as a preflight check, so the "every preflight must pass" invariant stays
  absolute — and Step 4 ticks the Issue's box in its Sub-Epic, plus the Sub-Epic's box in the Epic
  when that Sub-Epic completes. Criteria the user waived are recorded in the merge comment, never
  ticked to look complete.
- **`/architect:deliver-backlog`** states that checkboxes are *output*, not resume input: stage
  selection still reads `impl.status` and the tracker labels, and a mismatched box is a defect for
  the owning skill to fix.

## [0.17.4] - 2026-07-26

### Fixed
- **`/architect:generate-docs` — three ambiguities closed after a session-wide review of the
  v0.16.2–v0.17.3 work.** None change behaviour that was already exercised; they pin down what was
  previously derivable but implicit.
  - **Standalone mode determination is now stated.** Invoked with no `--issue` and not as a step of
    another skill, the resolved root decides the mode: a root under `generated/` is scaffold,
    anything else is delivery — with `--issue` required before any tracker write, and, when the run
    has no Issue to reference, commits still landing on the working branch and drift findings going
    to the user only.
  - **The `findings` section has a stated writer and timing.** It is produced by Step 5
    verification but was listed only in Step 4's section table, leaving a first run with no stated
    writer. Step 5 now writes it after verification in scaffold mode; the Step 4 listing covers
    re-runs, where prior findings already exist to carry.
  - **The stable key list has one source of truth.** It lived in both SKILL.md prose and the
    contract test's `STABLE` set, with only a comment as sync guard. The test now parses the list
    from SKILL.md's "Section keys are stable (…)" sentence — failing hard if the sentence
    disappears, with a fallback list so the mechanics checks still run if the file is copied
    elsewhere. Verified: all 8 keys parse, both fixtures pass, the fallback path passes.

## [0.17.3] - 2026-07-26

Everything here came out of exercising the backlog-delivery path for real — the marker contract
against a live `/product:generate-frontend` scaffold, the Output Location interlock on a scratch
repository, the Step 1 sub-agent delegation, and the full tracker write path (status transitions,
progress comments, PR linkage, merge, close, roll-up) against a throwaway repository rather than
live work items.

### Fixed
- **`/architect:merge-issue` — parent completion now reaches the manifest.** Step 4 said "update the
  node", singular, alongside `pr.merged` and a merge SHA — fields that only exist on an Issue. A
  Sub-Epic or Epic transitioned to `status::done` on the tracker therefore had nothing written back.
  Observed exactly that in a real 35-node backlog: all 27 Issue nodes carried `impl`, while the Epic
  and four completed Sub-Epics had no `impl` key at all — so a later `deliver-backlog` resume, which
  reads `impl.status`, would see a finished Sub-Epic as unstarted. Step 4 now updates every node the
  roll-up moved, with `pr` fields scoped to the Issue.
- **`/architect:export-backlog`, `/architect:deliver-backlog` — the manifest's `labels` array is a
  creation seed, not live state.** It records what was attached at creation (`status::todo` plus
  type/domain labels) and is never advanced; status lives on the tracker and in `impl.status`. In the
  real backlog every node still read `status::todo` while the tracker held 7 done and 9 doing.
  Harmless today because nothing reads it, but a trap for resume logic — so `export-backlog` states
  what the field is (and that `--update` is the one case it is rewritten), and `deliver-backlog` is
  explicit that state comes from `impl.status` and the tracker, never from `labels`, with the tracker
  winning on disagreement.
- **`/architect:generate-docs` — the inventory digest separates observed from inferred.** Exercising
  the Step 1 delegation validated the design (a haiku Explore agent returned a digest covering all
  six fields, matching independently verified ground truth on every count and command, with no source
  pasted and nothing fabricated) but exposed a gap: it asserted "Node.js 18+" as inventory when
  `package.json` declares no `engines` — an inference from Vite 5's requirement. The conclusion was
  right, but the orchestrator holds only the digest and cannot tell inference from observation, so it
  reaches the README as fact, defeating the skill's central discipline. Derived values must now be
  marked `inferred: <value> (<basis>)` and are documented with their basis or hedged, never asserted
  as read from the code.
- **`/product:generate-frontend` — regeneration says so before it overwrites.** The output location
  is correct (the tree is meant to be replaced, which is why `adapt-change` re-runs the skill), but
  nothing warned that a re-run destroys hand-edits under the output root; `adapt-change` carries a
  reversibility guarantee while the skill doing the writing said nothing. It now states plainly that
  it will overwrite and confirms (unless `--auto`), offers `--out=<path>` to regenerate alongside
  instead of over, and notes that a scaffold which has graduated into a hand-maintained frontend
  belongs outside `generated/`.

### Added
- **`skills/implement-backlog/output-location.test.sh`** — the Output Location interlock asserted as
  behaviour. Builds a scratch repository whose `.gitignore` carries the usual
  `reports/`/`generated/`/`work/` block and checks that `check-ignore` rejects a source root under
  `generated/` and names the matching rule, accepts a real `services/` root inside the worktree, that
  a docs commit lands on `feature/<issue-id>-<slug>` with the Issue reference and stages the intended
  file, and that an output path git ignores stages nothing so the commit is refused rather than
  silently empty. 11 checks, exit 1 on failure.

### Changed
- Both changelogs' link-reference blocks were stale — `CHANGELOG.md` stopped at `0.8.2`, leaving 13
  tagged versions unlinked plus a broken `[0.7.0]` link to a tag that was never cut, and
  `CHANGELOG_ja.md` had no references at all. Both now carry one reference per existing tag.
- `docs/codex-gap-analysis_ja.md` said the repo currently has 80 skills; it has 87 (architect 50 /
  product 26 / scalardb 11).

## [0.17.2] - 2026-07-26

### Fixed
- **`/architect:generate-docs` — region insert and remove are now exact inverses.** Re-run testing
  showed the whitespace around a marked region was unspecified, so remove → re-insert did not
  reproduce the file and repeated cycles left whitespace-only diff noise — in a file whose whole
  point is being reviewable. The rule is now explicit: exactly one blank line separates a region
  from its neighbours (or it sits flush against start/end of file); removal takes the region plus
  the single blank line that follows it, or at end of file the one that precedes it; the file ends
  with exactly one newline and no run of two or more blank lines is introduced. Verified before the
  rule was written: under it, remove → re-insert reproduces the file byte-for-byte for both a
  mid-file and an EOF-adjacent region, and five remove/append cycles produce zero drift.

### Added
- **`skills/generate-docs/marker-mechanics.test.py` — the ownership-marker contract asserted as
  behaviour.** SKILL.md states the marker rules in prose, so a later edit could quietly break
  re-run safety. 17 checks over five properties: in-place update leaves human prose byte-identical
  and duplicates nothing; re-application is a no-op; removal takes the region without touching
  other content; keys outside the stable list are refused for both update and removal; and
  insert/remove round-trip byte-for-byte with no drift over repeated cycles. Self-contained via an
  embedded fixture, or pass a path to check a real README; exit 1 on failure, matching the
  `hooks/*.sh` CLI convention.

### Changed
- CLAUDE.md's verification note lists the new test and no longer pins a plugin version number that
  had gone stale (it said `0.15.0`); it now states that the three plugins share one version and are
  bumped together, and records the tag + GitHub release steps in the release flow.

## [0.17.1] - 2026-07-26

### Fixed
- **`/architect:generate-docs` — drift findings now have a home, and generated sections can be
  removed.** Exercising the skill against a real `/product:generate-frontend` scaffold surfaced
  three gaps:
  - **Drift findings had nowhere to go in scaffold mode.** Step 5 said to report them to the user
    and append them to the Issue, but scaffold mode has no tracker — so a run had to invent a
    section key at write time. `findings` joins the stable key list, and a table now states where
    drift goes per mode: appended to the **Issue** in delivery mode (the tracker is the record,
    nothing written into the docs), written to the **`findings` section** in scaffold mode. Drift is
    never resolved in prose either way — the docs must not assert a reconciliation the code has not
    made.
  - **No removal rule.** A marked section a later run no longer justifies — resolved drift, a
    deleted service, a surface that no longer exists — is now removed together with its markers and
    listed in the run report; a stale generated section is worse than a missing one. Only keys in
    the stable list may be removed, so hand-written content is never touched. Inventing a key
    outside the list is now forbidden, since an unrecognized key makes the region unfindable on the
    next run.
  - **Non-git targets produced a raw git error.** Delivery mode now says plainly that it cannot
    commit outside a git worktree and offers scaffold mode, which needs no repository.

  Validated on the test run against a hand-written, unmarked README: the original prose was
  preserved 24/24 lines, every generated region sat inside markers with a stable key, and the
  verification step confirmed 6/6 documented commands and 18/18 paths against the real project
  while catching three genuine documentation defects in it.

## [0.17.0] - 2026-07-25

### Added
- **`/architect:generate-docs` — documentation for the code that was generated or implemented
  (`architect` plugin, new skill). The architect plugin is now 50 skills.** Code was being emitted
  by the codegen skills and by `implement-backlog` with nothing producing the README/`docs/` that
  describe it; this skill fills that step and has a fixed place in both paths.
  - **Two modes.** *Scaffold* documents `generated/` after `generate-scalardb-code` /
    `generate-infra-code` / `/product:generate-frontend` and does not commit (that tree is
    regenerable). *Delivery* documents the resolved `source_root` on the working branch and commits
    with the Issue reference, so the docs reach the same PR/MR as the code — reusing the
    `git check-ignore` / in-worktree checks, since documentation git ignores cannot reach a PR.
  - **Updates in place.** Ownership markers (`<!-- nexus:begin:<section> -->` …
    `<!-- nexus:end:<section> -->`) scope regeneration to this skill's own regions; human-authored
    prose is preserved and an unmarked, hand-written README is never rewritten in place without
    confirmation. Section keys (`overview`, `build-and-run`, `configuration`, `layout`, `api`,
    `operations`, `traceability`) are stable, so a later run updates the same region.
  - **Documents what exists.** Content is derived from the actual code, build files and
    configuration; the design reports supply only the *why*. A verification step checks every
    documented build/run/test command against a real build target, resolves every link and path,
    rejects config keys and routes absent from the code inventory, and reports design-vs-code drift
    as a finding (appended to the Issue in delivery mode) instead of smoothing it over in prose.
  - **Cost-tiered execution.** A thin sonnet orchestrator holding digests rather than sources:
    haiku agents for the code inventory, design-intent extraction and verification; one sonnet
    agent per page in parallel; opus only for judgment-heavy design prose (2PC boundaries,
    consistency model, failure/recovery semantics).

### Changed
- **`/architect:implement-backlog` — new Step 5b documents the implemented code.** Between
  implement (Step 5) and review (Step 6), the skill now runs `/architect:generate-docs
  --scope=changed --source-root=<resolved> --issue=<iid>` and commits the doc changes to the same
  working branch, so code and documentation are reviewed and merged together in one PR/MR. Skipping
  is allowed only when the item changes no documented surface, and the skip must be justified in
  the progress comment. The sub-agent assignment table, desired outcome and acceptance criteria are
  updated accordingly.
- **`/architect:deliver-backlog`** — stage (a) now notes that the implement step carries the
  README/`docs/` updates into the same PR/MR.
- `generate-scalardb-code`, `generate-infra-code` and `/product:generate-frontend` point downstream
  to `generate-docs`; the CLAUDE.md manual extension tier records the fixed **generate code →
  `generate-docs`** ordering. AGENTS.md model tiers, README.md and
  `docs/skill-reference{,_ja}.md` are synced.

## [0.16.2] - 2026-07-25

### Fixed
- **`/architect:implement-backlog` — merge-bound code now lands in the source tree, not
  `generated/`.** The skill produces deliverables: code is committed to
  `feature/<issue-id>-<slug>`, reviewed in a PR/MR by `/architect:review-issue`, and merged by
  `/architect:merge-issue`. Defaulting its output to `generated/` contradicted that, because
  `generated/` is regenerable pipeline output that target projects commonly git-ignore alongside
  `reports/` and `work/` — so `git add` could silently stage nothing and break the
  implement → review → merge chain on an empty commit. A new **Output Location** section resolves
  the source root by precedence (`--out` → the `source_root` recorded in
  `shared-context/decisions.md` → the existing repo layout → `services/{service}/` confirmed with
  the user on a greenfield repo) and records it in `decisions.md` so every item under the Epic
  writes to the same place. Two preflight checks now gate Step 4 before any code is written:
  `git check-ignore -q <source_root>` must exit 1 (any other status is surfaced as a git error, not
  assumed safe), and the root must resolve inside the target worktree. Step 5 confines implementer
  sub-agents to the resolved root — a unit needing to write elsewhere stops and reports instead of
  widening scope — and verifies each commit actually staged the intended files (`git show --stat`),
  routing an empty commit back to Output Location instead of on to review. `generated/` keeps its
  meaning for the one-shot codegen skills (`generate-scalardb-code`, `generate-infra-code`,
  `generate-frontend`), and `--out=generated/<service>/` still selects it for throwaway
  scaffolding. `templates/output-structure.md` and the CLAUDE.md command reference are synced with
  the new contract.

## [0.16.1] - 2026-07-25

### Changed
- **`/architect:implement-backlog` — token-optimized sub-agent execution.** The skill now runs as a
  thin **sonnet** orchestrator (was opus) that delegates heavy steps to model-tiered sub-agents,
  documented in a new "Sub-Agent Execution & Model Assignment" section: parallel sonnet agents
  derive the shared-context pack (Step 1), a haiku Explore agent digests the Epic/siblings/design
  reports (Step 3), an opus agent drafts the mini-plan against Epic-wide contracts (Step 4),
  sonnet agents implement per coherent unit with opus escalation only for judgment-heavy design
  (Step 5), opus agents issue the Epic-consistency verdict and roll-up review (Step 6), and a
  haiku agent drafts progress comments and the impl-log mirror (Step 7). Two cost rules are now
  explicit: the orchestrator holds compact digests instead of full report/source bodies, and each
  step uses the cheapest capable model tier — opus is reserved for planning and consistency
  judgment. AGENTS.md model tiers and the CLAUDE.md command reference are synced (with guidance
  for runtimes without model switching to preserve the delegation structure at the session model).

## [0.16.0] - 2026-07-24

### Added
- **Backlog Delivery skill family (`architect` plugin, 5 new skills)** — takes the generated
  reports all the way to merged code on GitLab/GitHub. **architect plugin now at 49 skills.**
  - `/architect:export-backlog` — turns the product/architect reports into a three-level work-item
    hierarchy: Epic (What/Why) → Sub-Epic (What/Key Results) → Issue (How). Review-first
    (`reports/backlog/backlog-plan.md` + `backlog-manifest.json` approved before any remote write),
    idempotent re-runs, native GitLab Epics with a scoped-label fallback, GitHub label + task-list
    scheme, traceability IDs carried through every level, and `status::todo` seeded on every node.
  - `/architect:implement-backlog` — implements a selected item while keeping the whole Epic
    consistent: reads the parent Epic and same-Epic siblings, builds and consults a shared
    engineering-context pack (`reports/backlog/shared-context/`: architecture guardrails, coding
    standards, ubiquitous language, data contracts, NFR budgets, ADR-lite decisions), writes code
    to `generated/{service}/` on the shared `feature/<issue-id>-<slug>` branch contract, appends
    progress to the Epic/Sub-Epic/Issue, and runs a lightweight + on-demand (`--review-epic`)
    consistency review. Defaults to the `status::doing` item, confirming with the user.
  - `/architect:review-issue` — reviews an implemented Issue for whole-Epic consistency (parent
    Sub-Epic/Epic + related Issues), auto-fixes `[B]` blockers via fix subagents in a bounded loop
    (`--max-fix-rounds` + no-progress detection; on non-convergence writes a "decision needed"
    comment, sets `status::blocked`, and asks the user), then opens a PR/MR linked to the Issue and
    hands off for approval. Distills every round's findings into a deduplicated project knowledge
    base (`shared-context/review-knowledge.md`, `KN-` entries) consumed by later planning and
    implementation.
  - `/architect:merge-issue` — merges the approved PR/MR behind a strict preflight (open, Mergeable
    verdict, approvals, CI green, no conflicts) and an explicit confirmation gate (skippable only
    via `--yes-merge`; preflight never skippable), then closes the Issue (`status::done` — single
    authority for done), rolls up Sub-Epic/Epic progress, and triggers the whole-Epic review when a
    Sub-Epic completes.
  - `/architect:deliver-backlog` — semi-autonomous orchestrator that drives implement → review →
    (human approval) → merge per Issue under an Epic, resuming from `backlog-manifest.json`; hard
    stops at the human gates and never auto-merges unless `--yes-merge`.
- **Shared status taxonomy** across the family: `status::todo/doing/review/done/blocked` (GitHub
  `status:` form), seeded by export-backlog and advanced by the downstream skills.

## [0.15.0] - 2026-07-15

### Added
- **`architect` plugin: `/architect:estimate-token-cost` skill** — estimates the token usage and
  USD cost of running the architect pipeline on a codebase. Combines an a-priori model (lines of
  code → ingested tokens → cache-adjusted billed input, with typical/low/high bands) with measured
  actuals from `work/token-usage.json` when present (extrapolates remaining phases on partial
  runs). Distinct from `/architect:estimate-cost`, which covers infrastructure/license/operational
  costs. **architect plugin now at 44 skills.**
- **Automatic per-phase token-usage recording (`hooks/record_token_usage.py`)** — a fail-safe hook
  (`PostToolUse` on `Write|Edit|MultiEdit|Task|Agent`, plus `Stop`/`SubagentStop`) that
  incrementally parses the session transcript and attributes billed tokens (input/output,
  cache read, 5m/1h cache writes, web-search requests) to pipeline phases: `in_progress` phases
  first, then phases newly transitioned to `completed` (sweeping the pending bucket), else
  `_unassigned` at turn end. Writes `work/token-usage.json` (per-phase/per-model ledger + USD) and
  `work/token-usage.jsonl` (append-only audit log). Inert outside initialized pipeline projects;
  flock-serialized against parallel subagent firings; message-id deduped across chunk boundaries.
- **`skills/common/references/model-pricing.json`** — single source of truth for model prices
  (including time-limited introductory pricing), cache multipliers, server-tool pricing, and the
  a-priori estimation heuristics shared by the recorder hook and the estimation skill.
- **`rules/token-pricing.md`** — ledger schema (`token-usage-v2`), attribution semantics and
  caveats, estimation methodology, and the subscription-vs-API billing distinction. Referenced
  from the `CLAUDE.md` Rules & References table.

## [0.14.0] - 2026-07-13

### Added
- **Input-requirements guides (`docs/product-input-requirements.md`,
  `docs/architect-input-requirements.md`, EN/JA)** — document the information the user must supply
  to run each plugin's pipeline (entry points, required vs. recommended inputs, interactive vs.
  `--auto` mode, per-phase elicitation, and the product→architect handoff). Linked from README,
  `getting-started`, `skill-reference`, `AGENTS.md`, and `CLAUDE.md`.

## [0.13.0] - 2026-07-07

### Added
- **`product` plugin: `/product:name-product` skill** — names the product as an **alphabetic
  acronym**: a short, pronounceable Latin-letter name whose every letter is the initial of an
  English word, so the name expands into a value phrase. Grounded in vision/positioning, it
  shortlists candidates and recommends one. Optional; included in the `full` profile. New rule
  `rules/product/naming-frameworks.md`. **product plugin now at 26 skills.**
- **Omnigent compatibility layer** — `OMNIGENT.md` plus a loader (`tools/omnigent/load-skill.sh`)
  let a generic multi-agent orchestrator run the ~90 `SKILL.md` files unchanged: the loader
  resolves `plugin:skill` names to file paths, prints a translation preamble, and expands
  `${CLAUDE_PLUGIN_ROOT}`. Non-invasive (no skill files modified); ships with tests.

### Changed
- **`AGENTS.md` model-tier recommendations synced** to the current 26 product skills
  (16 opus / 10 sonnet), matching each skill's `model:` frontmatter and both dependency manifests.

### Fixed
- **Stale flat paths in the nested migrate sub-skills (30 fixes across 12 files)** — runnable
  `cd` blocks, Related Skills sections, output trees, and extractor script comments still
  referenced pre-nesting paths (e.g. `skills/analyze-mysql-schema/...` instead of
  `skills/migrate-mysql/analyze-mysql-schema/...`).
- **Documentation drift**: README skill count corrected (77 → 80); CLAUDE.md model-tier table
  corrected (`analyze` = opus, `report` = haiku) and its product tier list completed to all
  26 skills; `/product:design-architecture` added to CLAUDE.md; `/product:create-domain-story`
  and `/product:design-system` added to the skill reference (EN/JA); `generate-ui-mock`
  description updated to its actual drivers (domain stories + design system).
- **Pipeline scope clarified**: the 12 architect skills outside `skill-dependencies.yaml`
  (infrastructure, security, observability, DR, implementation, codegen, cost estimation,
  security investigation) are now documented as a **manual extension tier** not executed by
  `/architect:pipeline`; the pipeline skill's "all skills" claim was softened to match.
- **Product→architect bridge artifacts declared at the receiving end**:
  `design-microservices` lists `architecture.md` / `tech-stack-fitness.md` and `design-api`
  lists `api-design.md` as optional inputs with refine-not-rederive semantics.
- Review-phase `parallel_with` declarations made symmetric; headings normalized to
  `Desired Outcome` / `Decision Criteria` (5 skills); "Use when" triggers added to 5 scalardb
  utility skill descriptions; `workflow/` and `research/` marked with README status notes;
  documentation language policy added to README; snapshot notes added to the Codex audit docs;
  getting-started (EN/JA) now points at `samples/ec-monolith`; stale `research/` filenames
  fixed in the define-requirements brainstorm doc.

### Documentation
- `/product:generate-frontend` surfaced in the getting-started guides (EN/JA).

## [0.12.0] - 2026-06-29

### Added
- **`product` plugin: `/product:generate-frontend` skill** — turns the navigable UI mocks and the
  active design system into a **runnable React + TypeScript frontend** under `generated/frontend/`.
  Decomposes the screens with **Atomic Design** (design tokens → atoms → molecules → organisms →
  templates → pages): each `CMP-` from the design system becomes a component at its atomic level and
  each UI-mock screen becomes a page. Components are styled with **CSS Modules + CSS variables** that
  reference design tokens only (no raw values), the story flow (`next`/`prev`) is wired with
  **react-router**, and every component is registered in **Storybook** with one story per
  variant/state. Emits a self-contained, installable scaffold (React 18 + Vite + Storybook 8 + TS).
  New rule `rules/product/atomic-react-storybook.md`; traceability records `COMP-`/`PAGE-` nodes with
  Upstream `CMP-`/`TOK-`/`STORY-` references. Runs in the spec phase, after `generate-ui-mock`.
  **product plugin now at 25 skills.**

### Changed
- **`product` plugin: `/product:start` now offers `generate-frontend` as a selectable step.** After
  the UI mocks, the orchestrator asks whether to generate the runnable React + Storybook frontend
  (interactive) or follows the profile under `--auto` (included in `ux-to-spec` / `full`). New flags
  `--frontend` / `--no-frontend` force the choice; the decision is recorded in
  `work/pipeline-progress.json` → `options.frontend`. The step is non-blocking — downstream phases
  read the mocks, not the generated code.

## [0.11.0] - 2026-06-26

### Changed
- **`product` plugin: `/product:generate-ui-mock` now produces a navigable, clickable prototype**
  instead of a set of disconnected single-screen HTML files. Screens are ordered by the domain
  story's numbered activities, and each screen's flow-advancing action is a real `<a href>` to the
  next activity's screen, so a reader can click through the whole story end to end. Adds back/next
  navigation and a `step N of M` indicator per screen, branch links to alternate-path targets, and a
  per-story flow index (`{STORY}-index.html`) as the entry point. Screens use deterministic file
  names (`{STORY}-NN-{slug}.html`); a story step missing from the source renders as a disabled `TBD`
  link (never a dead end). Traceability now records `next`/`prev` screen edges.

## [0.10.0] - 2026-06-24

### Added
- **`product` plugin: `/product:create-domain-story` skill** — persona-anchored Domain Storytelling.
  Actors come from personas (`PER-`), activities from job stories (`JOB-`) ordered by the journey
  (`JNY-`), work items from the things handled. Each story is the chosen happy-path scenario for a
  persona pursuing a key job, scoped per persona×job (bounded contexts are optional enrichment via
  `--domain`). Runs in the UX phase, after journey/positioning and **before** UI mocks; outputs
  `reports/01_ux/domain-stories/` with `STORY-` traceability. The product-pipeline counterpart of
  `/architect:create-domain-story`.
- **`product` plugin: `/product:design-system` skill** — build or `--import` a **separately-managed**
  design system. Build derives **W3C DTCG** tokens (color/type/spacing/radius/elevation/motion) from
  positioning/personas/vision with a WCAG contrast gate; `--import` normalizes an existing system
  (Tailwind config / DTCG JSON / Figma Tokens / CSS theme) into the same schema. Output lives in a
  dedicated `design-system/<name>/` tree (not under `reports/`), carries a semver `manifest.json`,
  supports multiple coexisting named systems, and is **standalone** (runnable any time). The active
  system is recorded in `work/pipeline-progress.json` → `options.design_system`. New rule
  `rules/product/design-system.md`. **The product plugin now has 24 skills.**

### Changed
- **`/product:generate-ui-mock` is story-driven and design-system–styled** — screens are derived from
  the domain story for each persona×job (one activity ≈ one screen interaction), and styled by the
  active design system: its `tokens.css` is injected into every self-contained screen, rendered at
  `--fidelity=lo` (tokens only) or `mid` (tokens + `CMP-` component styles). Falls back to ad-hoc
  lo-fi styling when no system is configured. Screens now also trace `STORY-`/`CMP-`.
- **UX-phase ordering** — `create-domain-story` and `design-system` run after positioning and before
  `generate-ui-mock` in the `full` profile, so mocks render a chosen flow in a shared visual language.

## [0.9.0] - 2026-06-24

### Added
- **`product` plugin: `/product:design-architecture` skill** — synthesizes bounded contexts, API
  layers, the data model and NFRs into a runtime architecture (Mermaid container / critical-path /
  deployment-scaling views), and runs an evidence-driven **technology-fitness** assessment over a
  standing checklist — **Kong (API Gateway), ScalarDB, ScalarDB Analytics, ScalarDL** — emitting an
  Adopt / Conditional / Reject decision with rationale and architecture placement for each. A
  ScalarDB/ScalarDL *Adopt* bridges to the `architect` plugin's ScalarDB pipeline. Outputs
  `reports/03_domain/architecture.md` and `reports/03_domain/tech-stack-fitness.md`. Added to the
  `full` profile (capstone after `define-nfr`) and the dependency graph; new rule
  `rules/product/architecture-and-tech-fitness.md`. Product plugin now has 22 skills.
- **Product → architect handoff contract (`docs/design.md`)** — a single source of truth for how
  `product` output feeds the `architect` plugin, resolving previously dangling `design.md`
  references in four SKILL/rule files. Defines the artifact mapping (per-output ID prefixes →
  `define-requirements` deliverables, §1.3), the by-design gaps `product` does not supply (§1.4),
  the cross-plugin **traceability write-back** contract (`FEAT-→FR-` links, verbatim `NFR-` reuse,
  §1.5), and the canonical **adaptation-engine** spec (§7).

### Changed
- **`/architect:define-requirements` consumes product output** — auto-detects product reports under
  `reports/0*_*/`, carries product IDs forward, uses `tech-stack-fitness.md` as the ScalarDB
  applicability prior, and writes `FR-`/`NFR-` nodes back to `work/traceability.json`.
- **`/architect:start` and `/architect:pipeline` are product-aware** — run handoff detection up
  front and route to the greenfield path with product reports fed in.
- **`/product:map-domains`** now emits a coarse per-`CTX-` consistency hint (`Strong`/`Eventual`/
  `TBD`) that seeds architect's transaction-consistency classification.
- **`/architect:review-consistency`** checks cross-plugin traceability continuity.

## [0.8.2] - 2026-06-20

### Changed
- Bumped all three plugin versions to 0.8.2.

### Documentation
- Documented the `create-domain-story` (Design) and `review-report` (Reporting) skills
  in `README.md` and the skill reference (en/ja), which previously listed 41 of the 43
  architect skills.
- Corrected the `/architect:pipeline` flag reference
  (`--resume-from`, `--rerun-from`, `--skip-{phase}`, `--no-scalardb`, `--lang`).
- Surfaced the `product` plugin in the Getting Started and Codex usage guides (en/ja):
  added a "Product Direction (greenfield)" entry point, the `/product:*` skill mapping
  (`skills/product/<name>/SKILL.md`), and the product install command.

## [0.8.1] - 2026-06-20

### Fixed
- Fixed a plugin namespace collision that prevented `product:` and `scalardb:` namespaced
  skills from loading. Skills are now scoped per plugin via explicit `skills[]` arrays in
  the marketplace manifest, so each plugin registers only its own commands.

## [0.8.0] - 2026-06-20

### Added
- **`product` plugin** (21 skills, 14 rules) — a validation-driven, dialogue-based product
  direction pipeline from product vision to SLA/NFR. Extracts and validates the riskiest
  assumptions before deep design, propagates changes through a traceability graph, and hands
  off to `/architect:define-requirements` for system implementation design.

Nexus Architect is now a three-plugin toolkit (`product`, `architect`, `scalardb`)
with 75 skills total.

## [0.7.0] - 2026-06-11

### Added
- `/architect:define-requirements` skill as the greenfield entry point: functional/
  non-functional requirement classification, data and transaction requirement analysis,
  and ScalarDB applicability assessment. Supports `--input`, `--auto`, and `--no-scalardb`.

## [0.6.2] - 2026-06-11

### Added
- `/architect:create-domain-story` skill for Domain Storytelling (visualize business
  processes per domain).
- `/architect:review-report` skill to review the quality of the generated HTML report.
- `ec-monolith` sample project for toolkit validation.

### Fixed
- Resolved agent component audit findings across hooks, skills, and manifests.
- Repaired Mermaid validator block parsing and added a ubiquitous-language term alignment rule.
- Added calculation procedures and self-verification to the `investigate` skill.

## [0.6.1] - 2026-05-12

### Added
- Parallel sub-agent execution in the review and evaluation skills.
- Parallelized `migrate-oracle` SA3/SA4/SA5 stages after the schema report.

### Fixed
- Multi-perspective review fixes across 28 files.
- Corrected skill invocations and nested sub-skill paths across the migration pipeline.

## [0.6.0] - 2026-05-07

### Added
- Codex compatibility layer (`AGENTS.md`): the same skill files are usable from Codex
  without installing Claude Code plugins.

### Fixed
- Removed the `name` field from all SKILL.md files to enable `/architect:` prefix registration.
- Resolved skill audit findings (manifest naming, frontmatter, JDBC patterns).

## [0.5.0] - 2026-03-24

### Changed
- Split the ScalarDB development skills into a separate `scalardb` plugin.

## [0.4.0] - 2026-03-23

### Added
- Database migration support (Oracle / MySQL / PostgreSQL → ScalarDB): schema extraction,
  migration analysis, and stored-procedure/trigger conversion to Java.

## [0.3.0] - 2026-03-23

### Added
- ScalarDB application development skills (schema modeling, configuration, CRUD/JDBC patterns,
  scaffolding, code review, migration advisory).

## [0.2.0]

### Changed
- Restructured the repository into a Claude Code plugin-compatible layout.

[0.17.4]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.4
[0.17.3]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.3
[0.17.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.2
[0.17.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.1
[0.17.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.0
[0.16.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.16.2
[0.16.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.16.1
[0.16.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.16.0
[0.15.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.15.0
[0.14.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.14.0
[0.13.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.13.0
[0.12.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.12.0
[0.11.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.11.0
[0.10.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.10.0
[0.9.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.9.0
[0.8.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.2
[0.8.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.1
[0.8.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.0
[0.6.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.2
[0.6.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.1
[0.6.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.0
[0.5.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.5.0
[0.4.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.4.0
[0.3.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.3.0
