# Changelog

All notable changes to Nexus Architect are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Version numbers refer to the per-plugin versions in `.claude-plugin/marketplace.json`;
all three plugins (`product`, `architect`, `scalardb`) are released together under one number.

## [0.24.1] - 2026-08-09

### Fixed
- **Six defects the first end-to-end run of the 0.24.0 pipeline exposed.** 0.24.0 shipped the
  contract-fidelity chain without ever having been executed. Running it for real — `design-api` →
  `design-implementation` → `generate-api-code` → `generate-contract-tests` →
  `verify-implementation --gate` against a Java 17 / Spring Boot 3.2.5 service, compiling and testing
  against ScalarDB 3.19.0 and the actual validator library — broke it in four places on contact.
- **The contract map had no notion of scope, so it could pass its own check while hiding endpoints.**
  In a brownfield tree — the legacy-refactoring case this toolkit exists for — controllers predate the
  contract, and a generator scanning only its own package emits `handlers_without_spec_operation: []`
  while real routes stay undeclared. The run produced exactly that: six reachable routes, including
  `/api/admin/users`, absent from the contract and from the map. The map now declares a `scope` with
  an explicit `out_of_scope_handlers` list derived from the tree, every reachable route must be
  accounted for by one list or the other, and out-of-scope entries are still reported as findings —
  the field records that the omission was named, not that it is acceptable.
- **The generated inventory assertion read the contract map instead of the code**, so it passed
  precisely when the map was wrong — which is when it needed to fail. It is now derived from the
  source tree and compared against the specification. Consumers are told, in the rule, never to
  conclude coverage from the map alone.
- **The default contract-test coordinate does not exist.** Atlassian publishes the library under both
  `com.atlassian.oai:swagger-request-validator-*` and `com.atlassian.oai:openapi-request-validator-*`;
  the MockMvc integration is the `-mockmvc` module, and there is no `-spring-mvc` artifact under
  either name. Pinning the documented name yielded an unresolvable dependency.
- **The current major of that library is Java 21 and will not compile into a Java 17 service**
  (`bad class file … version 65.0 … should be 61.0`). The `2.x` line is a Java 8 baseline and is the
  correct pin. Resolving the coordinate now means listing the group directory and checking the
  artifact's JDK baseline against the project's target release — @rules/dependency-versions.md §2 in
  its most literal form.
- **The contract tests loaded the specification from `reports/`, which is git-ignored** — green for
  the author, red in CI on a fresh checkout, so the contract stage would fail for everyone else. The
  spec is now pinned into `src/test/resources/contract/openapi/` and loaded from the classpath;
  `verify-implementation` compares the copy against the design original so a stale copy is not
  invisible drift.
- **`gitleaks detect` in a non-git tree reported "0 commits scanned … no leaks found" and exited 0** —
  a clean secrets scan that examined nothing, which the gate would have recorded as evidence.
  Directory mode over the same tree scanned 239 KB and found a leak. The gate now requires per-stage
  **coverage** evidence and treats zero coverage as `not-configured`, never `passed`; the same rule
  covers a test filter that matches no class, which is a green task and an ungated build.
- **`generate-api-code` reported success on code the project could not compile.** It emitted a
  controller using `@AuthenticationPrincipal Jwt` without adding
  `spring-boot-starter-oauth2-resource-server`. It now adds the dependencies its own output requires
  and compiles before reporting, with the command and exit code in the run summary.
- **`verify-implementation` now checks that a declared authorization control is enforced, not merely
  present.** `@PreAuthorize` compiles, reads as a control, and does nothing until method security is
  enabled — an operation whose authorization exists only as an annotation now raises a finding.

### Verified
The same run confirms the parts that were right: the RFC 9457 handler compiles against real ScalarDB
3.19.0, and the `UnknownTransactionStatusException` branch returns 503 with `Retry-After`,
`transaction_id` and `retry_after_ms` on an idempotency-protected operation — asserted by a passing
contract test. 404-not-403 for a non-owned order, the confidential field absent from the response,
and schema-derived validation returning Problem Details with `errors[]` pass the same way. The gate's
stage 1 caught the compile failure and stage 3 caught the inventory gap, which is the gate working as
designed.

## [0.24.0] - 2026-08-09

### Added
- **The OpenAPI document is now an enforceable contract, not a report.** The toolkit designed APIs
  well and had no way to tell whether the code implemented them: `design-api` emitted OpenAPI,
  `generate-scalardb-code` emitted entities, repositories and domain services, and nothing generated
  or checked the layer between them — no controller, no DTO, no validation, no error handler, and no
  step anywhere comparing code to the design it came from. For AI-written code that is the gap that
  matters, because a model produces plausible code far more reliably than correct code, and plausible
  code survives reading. Four new rules and four new skills close it.
- `rules/api-contract-fidelity.md` — the specification is the contract: code may not exceed it, may
  not contradict it, and a behaviour change edits the specification first. `operationId` is the join
  key, bound 1:1 to a handler and recorded in `reports/06_implementation/api-contract-map.json` whose
  `unmapped` arrays are never omitted. Where code and contract disagree the drift is **reported, not
  reconciled** — the same discipline `generate-docs` already follows.
- `rules/api-error-standard.md` — RFC 9457 Problem Details as the single error envelope, with a
  per-project problem type registry allocated the way the traceability graph and the Open Questions
  store are. Carries the ScalarDB exception mapping, including the row with real consequences:
  `UnknownTransactionStatusException` is neither a plain 500 nor a blanket 503. The commit may have
  succeeded, so it is 503 with `Retry-After` **only** when the operation is idempotency-key
  protected, and 500 with no retry hint and an explicit reconcile-don't-retry `detail` otherwise.
- `rules/api-security-checks.md` — OWASP API Security Top 10 (2023) as concrete checks, each split
  into a design question and a code question because they fail independently, plus the multi-tenant
  and transaction-boundary cases a generic scanner cannot see.
- `rules/ai-code-quality-gate.md` — eight stages before a human is asked to review. What makes it a
  gate rather than a checklist: **every stage produces evidence** — a command with its exit code, or
  a skill with its findings — and a stage that did not run is recorded with its reason. An omitted
  stage reads as a passed one, which is worse than no gate. FAIL blocks the review handoff instead of
  becoming a note on the PR.
- `/architect:verify-implementation` — the design↕code differential engine, on four axes: contract
  (handler binding, DTO shapes, status codes, error envelope, the indeterminate-commit branch),
  transaction (an operation the design placed in one transaction implemented as one; retry, catch
  order, saga compensations, 2PC completeness), security (delegated to `review-api-security --mode=code`),
  and requirement (`FR-` to code, acceptance criteria to tests). It edits nothing — when the two
  disagree it names both sides, because which one is wrong is the user's call. `--gate` runs the
  eight-stage gate.
- `/architect:review-api-security` — OWASP API Top 10 in three dimensions, as the **sixth** parallel
  design review and, with `--mode=code`, as the gate's security stage. The two modes are not
  redundant: a project can hold a correct Zero-Trust design and ship a controller that trusts a path
  parameter.
- `/architect:generate-api-code` — the API layer from the contract. One controller method per
  `operationId`; DTOs named from `components/schemas` with Bean Validation **derived** from the schema
  constraints rather than chosen; explicit DTO↔domain mappers, because binding a request body onto an
  entity is the mass-assignment defect; the RFC 9457 handler with the indeterminate-commit branch. It
  generates only what the specification declares, and stops rather than filling a gap with a plausible
  guess. Independent of ScalarDB.
- `/architect:generate-contract-tests` — the contract as executable assertions: in-process OpenAPI
  validation (`swagger-request-validator` + `@WebMvcTest` by default; Schemathesis, Pact and ArchUnit
  as recorded opt-ins), Problem Details conformance, authorization, idempotency, the
  indeterminate-commit contract, and an inventory assertion that fails when anything is unmapped.
  Expected values come from the specification, never from the implementation — a test written against
  the code passes whatever the code does.

### Changed
- `design-api` rewritten around a Contract Verifiability checklist — named schemas, every status code
  declared, constraints in the schema, per-operation authorization / idempotency / timeout. Each item
  exists because a specific downstream check is impossible without it. New outputs: `problem-types.md`
  and `operation-contracts.md`.
- `design-implementation` gains `api-layer-spec.md`: the per-`operationId` handler, DTOs, validation,
  mapper, transaction boundary and authorization enforcement point.
- `generate-test-specs` makes contract testing its own category with `contract-test-specs.md`, and
  records the selected test stack so `generate-contract-tests` emits what was decided.
- `design-security` gains object-level authorization, the tenant isolation model, and an OWASP API
  Security Top 10 mapping, so the code-time review has a baseline instead of a blank page.
- `generate-scalardb-code` declares the package seam it now shares — `domain/` + `infrastructure/`
  here, `api/` in `generate-api-code`. Emitting a controller from the domain generator would produce
  a second, unbound API surface.
- `generate-infra-code` emits the quality-gate CI workflow. The in-session gate is fast feedback; CI
  is the half that is actually enforced, so its jobs may not carry `continue-on-error` or `|| true`.
- `implement-backlog` gains Step 5c and `review-issue` gains Step 2b: the gate runs before a human is
  asked to look, and blocking `VER-`/`ASEC-` findings enter the existing auto-fix loop as `[B]`.
- The codegen follow-on order is now **generate → test → document → verify**, and the parallel design
  review is six perspectives rather than five — corrected across README, `CLAUDE.md`, `AGENTS.md`,
  `OMNIGENT.md`, both skill references and both getting-started guides.

## [0.23.3] - 2026-08-09

### Changed
- **The user-facing docs now describe the handoff the code enforces.** 0.23.0–0.23.2 turned the
  product→architect boundary into a contract with real invariants, but `README.md` and the getting
  started guides still showed it as a single arrow — a reader had no way to know that `NFR-` IDs
  are reused verbatim, that `FEAT-`→`FR-` links are recorded, that three things are left
  unanswered *by design*, or that both pipelines then share three files under `work/`. README
  gained a crosses/stays-behind table, both getting-started guides gained a "what the handoff
  actually does" section, and both architect input-requirements guides gained the three points
  that are easy to miss: a partial product run still hands off, Open Questions are one store, and
  new IDs are allocated from the graph. `docs/design.md` remains the contract; these are the
  doorways into it.

## [0.23.2] - 2026-08-09

### Fixed
- **`NFR-` IDs could be minted twice, by two skills, for different requirements.** `docs/design.md`
  §1.5 told architect to create `NFR-` nodes for architect-originated NFRs without saying where the
  number comes from, which silently assumed product had already run `define-nfr`. It has not always:
  a product run that stops at `--profile=mvp` hands off to `define-requirements`, which finds no
  `NFR-` and mints `NFR-001`; resume the product pipeline afterwards and `define-nfr` mints
  `NFR-001` too. An end-to-end run through the full profile produced exactly this — six IDs, each
  with two meanings, in the single graph both plugins share. §1.5 gained rule 4: allocate every new
  ID as `max` over the graph for that prefix `+ 1`, the same rule `OQ-` follows. The §1.5
  verification list now includes "no ID appearing twice", so `review-consistency` and
  `/product:review` catch a recurrence instead of leaving it to a later reader.

## [0.23.1] - 2026-08-09

### Changed
- **The Open Questions store is one file, and the architect deliverable is a view of it.** The
  protocol named two stores — `work/context.md` § Open Questions and
  `reports/00_requirements/open-questions.md` — without saying which was authoritative or how IDs
  were allocated. Two consequences, both reachable in a normal handoff run: product and architect
  could mint the same `OQ-004` for different questions, since neither had a rule saying where the
  next ID comes from; and an answer recorded on one side never reached the other, so a question
  architect resolved stayed `unasked` for a later product rerun. `work/context.md` is now **the**
  store for the whole project, `reports/00_requirements/open-questions.md` is rendered from it as
  a deliverable rather than kept as a second source, and a new ID is `max(OQ-###) + 1` over the
  store. This is the same rule `work/traceability.json` already followed — never start a second
  file — applied to the question that crosses the boundary in both directions.

## [0.23.0] - 2026-08-09

### Added
- **The ID prefix namespace is declared, not just described.** Each phase in both
  `skill-dependencies.yaml` files now carries `id_prefix`, making the manifests the registry
  of which skill mints which ID prefix. The prefixes previously existed only in each SKILL.md's
  prose, where nothing could detect a collision or an omission — and three skills turned out to
  declare none at all. `tools/lib/pipeline_status_data.test.py` now asserts that every skill
  which appends to `work/traceability.json` declares a prefix, that its SKILL.md actually uses
  it, and that no two skills in one manifest claim the same one (`NFR-` is the single
  deliberate cross-manifest claim — the §1.5 carry-over, asserted as such).
- **Registry phase entries name their pipeline.** Every entry in
  `work/pipeline-progress.json` now carries `"plugin": "product" | "architect"`, written by
  `init-output` and by each orchestrator on its `in_progress` stamp. One registry serves both
  pipelines and keys phases by bare name, so for the four names both manifests define this
  field is the only thing that says whose entry it is. `tools/nexus-status.sh` reads it to
  settle the question outright — an entry labelled for the other pipeline is not this phase's
  status, whatever it says — and falls back to output corroboration where the field is absent.

### Fixed
- **A ScalarDB-free project no longer sits at 3/4 outputs forever.** The architect manifest listed
  `scalardb-applicability.md` among `define-requirements`' unconditional outputs, but the skill
  writes it only when ScalarDB is in play — so on a ScalarDB-free project the output bar could
  never fill and the phase read as unfinished rather than as one with nothing left to write. The
  manifest gained `conditional_outputs` (`"<condition>:<path>"`), and the dashboard counts such an
  output only when the project's options satisfy its condition.
- **The validation gate now says whose it is.** The gate is the *product* pipeline's, and it is
  deliberately surfaced on the architect tab as well — requirements resting on an unvalidated
  premise is exactly what an architect wants to know — but an unlabelled `gate: no-go` printed over
  the architect tree read as architect's own verdict. It now renders as `Product gate: no-go`
  everywhere except the product view.
- **Handoff detection matches files, not directories.** `/product:init-output` creates
  `reports/01_ux/domain-stories/` and `reports/02_spec/ui-mocks/` empty, so a directory-existence
  test reported a product handoff on any initialized product project, whether or not a phase had
  ever run. Corrected in `/architect:start`, `/architect:pipeline`, `define-requirements`,
  `AGENTS.md` and `OMNIGENT.md`; `define-requirements` additionally states which product artifacts
  it found and which were absent, since a partial product run changes what can be carried over.
- **`AGENTS.md` and `OMNIGENT.md` now document the handoff they were driving.** The repo runs the
  same skills under three orchestrators and requires their entry docs to stay in sync, but only
  `CLAUDE.md` mentioned the product→architect handoff at all — Codex and the omnigent loader were
  given no detection rule, no artifact mapping, and crucially no statement that
  `pipeline-progress.json`, `traceability.json` and `context.md` are shared by both pipelines and
  must be written additively. Both now carry the detection glob, a pointer to the `docs/design.md`
  §1 contract, the per-file additive rules including the `plugin` stamp and the four ambiguous
  phase names, and `adapt-change`'s report-and-stop boundary. `CLAUDE.md` gained the same
  shared-state paragraph.
- **Three skills wrote nodes nothing downstream could cite.** `research-landscape`,
  `generate-ui-mock` and `generate-frontend` all appended to the trace graph without saying
  under which ID prefix, which broke two chains for real: `/product:adapt-change --type=market`
  seeds its blast radius from market-landscape nodes that had no ID to seed from, and the
  journey → story → **screen** → feature chain had no screen ID to run through. They now mint
  `MKT-`, `SCR-` and `PG-` respectively, and `define-features` cites the `SCR-` each `FEAT-`
  comes from — so a `FR-` derived downstream traces all the way back. A generated React
  component creates no node of its own: it is the implementation of a design-system `CMP-` and
  is recorded on that node instead of being duplicated under a second ID.
- **Token cost is no longer merged across the pipeline boundary.** `work/token-usage.json` was
  keyed by bare phase name like the registry, so the product and architect spend on
  `map-domains` (or `design-api` / `create-domain-story` / `report`) accumulated in one bucket
  that neither view could claim. `hooks/record_token_usage.py` now records those four under
  `<plugin>:<phase>`, taken from the registry entry's `plugin` field; the dashboard charges a
  bucket only to its own pipeline, leaves the neighbour's to its own tab, and reports a legacy
  un-namespaced bucket as unassigned rather than to whichever tab happens to be open. Every
  other phase name is recorded bare, as before.
- **`/product:adapt-change` stops at the architect boundary instead of leaving it undefined.**
  After a handoff the trace graph holds architect's nodes, so the blast-radius closure reaches
  them by design — but the skill said nothing about what to do with them. It now splits the
  confirmed impact set by node ownership, re-runs only the product side, and writes an
  `## Architect-Side Impact` section naming each affected `FR-` / `NFR-`, the skill that owns
  it and the command to act on it. It never rewrites an architect artifact: a product-side
  change is grounds to revise the product spec, not authority to rewrite requirements that
  backlog items and shipped code depend on. `docs/design.md` §7.5 is the new contract, and
  §7.2 no longer implies the re-run crosses over.
- **`/architect:pipeline` detects a product handoff over the same reports `define-requirements`
  reads** — the same glob mismatch already fixed in `/architect:start`.
- **`init-output` no longer discards the other pipeline's state.** Both `/architect:init-output`
  and `/product:init-output` are now explicitly additive: they merge into an existing
  `work/pipeline-progress.json` instead of re-registering every phase as `pending`, keep the
  `options` already set (notably the `output_language` the user chose), and create
  `work/context.md` / `work/traceability.json` only when absent. On the product→architect
  handoff `/architect:start` runs `init-output` immediately before
  `/architect:define-requirements` — and `init-output` used to create `work/context.md` "as an
  empty file", erasing the product-side Open Questions table that `define-requirements` reads
  in its very next step. `/product:init-output` likewise no longer truncates
  `work/traceability.json`, which is the single cross-plugin trace graph architect appends its
  `FR-` / `NFR-` nodes to (`docs/design.md` §1.5).
- **A phase name both pipelines define is no longer read as done on one pipeline's word.**
  `map-domains`, `design-api`, `create-domain-story` and `report` are defined by both
  manifests, and the progress registry keys phases by bare name — so a *product* phase
  recorded `completed` rendered as the *architect* phase being complete, and
  `/architect:pipeline --resume-from` would have skipped it. `tools/nexus-status.sh` now
  trusts such an entry only when the phase's own declared outputs exist to corroborate it,
  and otherwise derives the status from the filesystem and reports `shared-name` drift; a
  running phase (`in_progress`) and a skip the project actually asked for are exempt.
  `skills/common/progress-registry.md` states the same rule for the orchestrators — confirm
  an ambiguous entry against the outputs on disk before treating it as satisfied — plus the
  additive-write rule the shared registry requires. `init-output` additionally records each
  such entry in `warnings[]`.
- **`/architect:start` detects a product handoff over the same reports `define-requirements`
  reads.** Detection globbed only `reports/02_spec|03_domain|04_quality`, so a product run
  that stopped early (`--profile=mvp` writes only `reports/00_core/`) could be announced as
  having no product artifacts by the skill about to consume them. The two sets are now
  identical.

### Changed
- **Open Questions are asked, not filed.** Every skill that could write `TBD` now runs the
  protocol in the new `rules/open-questions.md`: an unknown it cannot resolve from its own
  inputs is put to the user with `AskUserQuestion` — 2–4 candidate answers the skill derived
  from context, each described by what it changes downstream — and only what the user defers,
  cannot answer in-session, or was never asked (`--auto`) becomes a `TBD`. Previously an
  unknown went straight to "record it as `TBD` in Open Questions", so a question the user
  could have answered in one click was instead deferred into a report nobody re-opened.
- **Anything the options cannot express is answered in free text.** Skills never author an
  "Other" option (the harness appends one, and that is the free-text path) and never round a
  free-text answer to the nearest option — it is recorded verbatim and marked as free text,
  with only units/IDs normalized and the normalization echoed back. Inherently free-form
  answers are asked as representative bands (`p95 < 100 ms` / `< 500 ms` / `< 1 s`) so the
  exact figure arrives through "Other", or in prose when no meaningful bands exist — never
  skipped to `TBD` because the answer would not fit a menu.
- **What stays open now says why.** Open Questions entries carry an `OQ-` ID, a status
  (`answered` / `deferred` / `unasked` / `external`), the answer, the options offered, an
  owner and the downstream impact; a `TBD` in an artifact carries its question ID
  (`TBD (OQ-012)`). `/product:report` groups the header by status so a question nobody was
  asked is visibly different from one the user consciously deferred, and `/product:review`
  reports an unasked `TBD` as a finding. `--auto` runs record the question *and the options
  that would have been offered*, so a later pass can answer instead of re-deriving.
- **Questions carry across phases.** Each skill picks up the `deferred` / `unasked` entries in
  its own domain at its read-context step, re-asks them in its first question batch, and
  updates them in place under the same `OQ-` ID — no duplicates, and nothing already answered
  is re-asked. `/product:init-output` seeds `work/context.md` with the `## Open Questions`
  table; the product→architect handoff carries the IDs into
  `reports/00_requirements/open-questions.md`.
- Wired through `CLAUDE.md`, `AGENTS.md` and `OMNIGENT.md`: Codex and the omnigent loader have
  no harness-appended "Other", so they print an explicit "or type your own answer" line under
  the numbered choices and record a non-matching reply as a free-text answer.
- **The token-cost dashboard now prices its component columns.** In the live
  `/architect:report-token-cost` dashboard the per-model `in` / `out` / `cache-read` /
  `cache-write` columns hold money (`$`) instead of token counts — the dashboard is read to
  answer "what did this cost", and the token total is already its own column. `b` switches
  them back to counts and the bottom bar names the current unit, so the toggle is
  discoverable rather than documented-only. The static and `--md` report keeps token counts
  (there the columns break down the token total the same table carries); `--breakdown=` still
  overrides either default.
- **A nonzero cost never renders as `$0.0000`.** Amounts below a hundredth of a cent now show
  as `<$0.0001` (`<¥1` under `--currency=jpy`), instead of rounding a real charge down to
  something that reads as free — visible now that the dashboard prices per-component columns,
  where cheap models land in that range.

## [0.22.1] - 2026-08-08

### Fixed
- **The status dashboard's `c` key opened a browser instead of copying.** `c` is documented
  as "copy the default command for the selected row", but the default action for a finished
  row is an open (`open URL` on a merged Issue, `open output` on a completed phase) and the
  shell dispatched on the label alone — so `c` launched a browser tab or an editor and
  reported it as `command <url>`, having copied nothing. `c` now always copies, including
  the path or URL of an open-type default; `o` remains the key that opens, and choosing
  `open output` from the action menu still opens it.
- **A filtered-empty tree claimed the pipeline had never run.** With `f` cycled to a status
  nothing matched, or `--group`/`--epic` narrowing to nothing, the dashboard printed "the
  product pipeline has not run in this project" / "no backlog manifest" directly beneath a
  header summarizing the phases and Issues it had just counted. The empty state now names
  the filter responsible, and offers `f` only when `f` is what would clear it.
- **`Esc` quit the dashboard on a stray escape sequence.** A terminal that emits a sequence
  ncurses cannot map — application-cursor-mode off, a mouse report, a bracketed-paste or
  focus-change marker, an unknown `$TERM` — delivers the leading `27` as a bare keypress,
  which the shell bound to quit. `Esc` now only closes a menu or the help panel; `q` is the
  only key that quits, and `? help | q quit` is pinned to the bottom bar so it survives a
  key legend too long for the terminal (the Japanese legend overflows before 120 columns).
- **The action menu never said how to close itself without `--exec`.** Building the hint by
  slicing the legend at its first separator dropped `Esc close` along with the run key.
  Relatedly, pressing `e` on an `open output` entry *with* `--exec` enabled answered "run
  with `--exec` to launch claude from here" — it now opens the entry — and pressing `e`
  without `--exec` no longer closes the menu, so the selection is not lost to a hint.
- **The help panel printed its glyph legend once per tab and ran off the bottom of the
  screen.** The three pipeline tabs are one class returning one legend, so it appeared two
  or three times; the panel had no height bound either, and below ~30 rows its closing
  border and its "how to close this" hint were clipped away with no way to scroll. The
  legend is now de-duplicated and the panel scrolls (`^v`/PgUp/PgDn/`g`/`G`) when it does
  not fit — verified at 80x24.
- **A `failed` phase could be invisible.** The progress fraction is measured over the
  required path, so a phase that failed in the manual extension tier — or one recorded
  outside the manifest — was absent from the header's status counts and its row sat below
  the fold, while the one-shot renderer printed an explicit `failed:` footer. The dashboard
  header now names every failed phase, as the static render always did.
- **A misspelled `--phase` / `--epic` was accepted by the live dashboard.** The one-shot
  renderers exit 2 on an unknown name; live mode ignored `--phase` entirely and drew an
  empty backlog for an unknown `--epic`, so a typo looked like an answer. Both are now
  checked before curses takes the screen, in every mode.
- **The 10-second poll walked the output tree once per pipeline tab.** Product, Architect
  and Code Generation scan the same project directory, and each did so independently. The
  shell now computes one walk per poll for views that declare the same `stamp_key`.

## [0.22.0] - 2026-08-07

### Changed
- **The status dashboard now has four views instead of two: Product, Architect, Code
  Generation and Backlog Delivery.** The single "pipeline" tab had to *detect* whether a
  project was running the product or the architect pipeline and then showed only that
  one — so on a project that ran both, one pipeline was simply unreachable, and every
  phase the other manifest knew was dumped into the tab's "recorded outside the manifest"
  group as if it were an anomaly. Product and architect are separate pipelines with
  separate manifests, so they are now separate tabs, each stating which pipeline it shows
  rather than guessing; `Tab` / `Shift-Tab` cycle all four, dimming and skipping any the
  project has nothing behind. A registry entry the other plugin's manifest defines is no
  longer reported as unmanifested — it is the tab next door.
- **Code generation is its own view.** `generate-scalardb-code`, `generate-infra-code`,
  `generate-docs` and `/product:generate-frontend` are run by hand after whichever
  pipeline designed the system and emit code into the target project rather than reports
  under `reports/`, so they no longer sit inside a pipeline tree they are not a step of.
  The Code Generation view collects them from **both** plugins, grouped by plugin, and
  each row offers its own plugin's slash command (`/product:generate-frontend`,
  `/architect:generate-infra-code`) rather than the view's. `generate-test-specs` stays in
  the architect pipeline: it writes specifications, not code. Cross-boundary dependencies
  and staleness are unaffected — `generate-scalardb-code` is still blocked by
  `design-implementation` and still goes stale when it is rerun; only the grouping and the
  progress fraction are per-view.
- **`--view=` takes the new names**: `product`, `architect`, `codegen`, `backlog`, plus
  `pipeline` (whichever pipeline this project runs, from `--plugin=` or detection) and
  `auto` (unchanged: the detected pipeline, else the backlog). `--group=core|extension`
  keeps applying to the architect pipeline view only; it has no meaning in the codegen
  view, whose groups are plugins. `--md` for the codegen view defaults to
  `reports/codegen-status.md`. `--json` gained `view`, `section`, and a per-phase
  `plugin` / `section`, and each phase's `group` is now the group header it actually
  renders under.

## [0.21.2] - 2026-08-07

### Fixed
- **The pipeline dashboard reported a finished project as entirely `pending`.** The
  progress registry held unconditional authority over a phase's status, but it is written
  by a soft "update `pipeline-progress.json`" step at the end of each SKILL.md — a step
  that is routinely skipped, and never runs at all when a phase is invoked outside an
  orchestrator. Every unstamped phase therefore stayed at the `pending` it was born with,
  so a project with all 23 phases' reports on disk rendered `2/23 完了`, with each row
  contradicting itself (`[====] 4/4 ○ pending`). `pending` is now treated as what it is —
  the initial value, asserting nothing — and loses to declared outputs that actually
  exist; `in_progress` / `completed` / `failed` / `skipped` are claims a skill really made
  and keep their authority. The disagreement is still surfaced as drift, so an unstamped
  registry stays visible rather than being silently papered over. This also restores
  staleness on those phases: a `pending` phase can never go stale, so the invalidation
  chain that un-completes everything downstream of an edited report was suppressed
  wherever the registry had gone unstamped.
- **The status dashboard's two tabs no longer contradict each other.** The backlog view's
  pipeline strip counted the progress registry directly — so its total was "however many
  phases the registry happens to mention" and it ignored staleness, leaving the same
  screen reading `pipeline 2/5` in one tab and `Phases 2/24 done` in the other one Tab
  away. The strip is now derived by the pipeline view's own state layer: the manifest
  supplies the total, the filesystem fills in phases no skill recorded, invalidated
  phases leave the completed count, and the strip carries their number (`↺ 2`).
- **The backlog view's key legend and Japanese labels caught up with the unified
  dashboard.** `Tab` (switch view), `a` (ask Claude) and `?` (help) all worked but were
  missing from the bottom bar, and four header labels stayed English under `--lang=ja`
  (`Issues 1/2 done` beside the pipeline tab's fully localized `フェーズ 1/24 完了`).
- **`/architect:investigate-security` declared an output filename it should never have
  written**: `reports/before/{project}/architect:investigate-security.md` — a colon in a
  filename, off the kebab-case convention, and unmatchable in practice. It is now
  `security-assessment.md`, in the skill and in the dashboard's output table alike.
- **A misspelled `--phase` / `--epic` is a usage error (exit 2), not an empty tree.** Both
  rendered a header with nothing under it and exited 0, which reads like "this phase is
  empty" rather than "no such phase"; they now name the real phases / Epic IDs on stderr.
  A filter that legally matches nothing — `--group=extension` on a product project —
  says so on the render ("nothing to show", plus the reason) and still exits 0.

### Changed
- **`--group` / `--phase` / `--epic` now narrow `--json` exactly as they narrow the
  tree**, instead of being silently dropped, and every JSON render carries a `filters`
  object recording what was applied (`summary` still covers the whole project). The
  per-phase footers of a filtered text render — stale, drift, failed — likewise report on
  the rows on screen rather than on phases the reader deliberately narrowed away.
- **The live dashboard notices an overwritten report.** The refresh poll compared
  directory mtimes two levels into `reports/`, and overwriting an existing file changes no
  directory mtime at all — precisely the case staleness is about, and precisely where
  architect writes (`reports/before/{project}/*.md`, `reports/review/individual/*.json`).
  It now stats the files themselves, three levels deep, under a bounded entry budget.
- **The manual extension tier is declared as completely as the core pipeline.** Its
  phases listed one output where the skill writes three or four (`estimate-cost`,
  `design-implementation`, `generate-test-specs`, `generate-scalardb-code`,
  `generate-infra-code`), so their output bars could only read 0/1 or 1/1; each now lists
  what its SKILL.md promises. `report-token-cost` joins the tier as its fifteenth member.

### Added
- **`tools/nexus-status.test.sh`** — an executable check of the dashboard's CLI contract,
  the layer above the two data modules: project resolution and the 0/1/2 exit codes, view
  selection, every output mode (including `--md` frontmatter and `--ascii` purity), the
  filters applying to `--json`, unknown filters failing as usage, the two views agreeing,
  and the refresh poll noticing an overwritten depth-3 report. The derivation test now
  also pins the extension tier against the docs and each skill's own Output table, so a
  skill added to the tier cannot quietly go unrepresented in the dashboard.
- Dashboard options that existed but were undocumented are now in the skill docs:
  `--watch[=SEC]` / `--live`, `--glyphs`, `--color` / `--no-color`, and `--plugin`.

## [0.21.1] - 2026-08-07

### Fixed
- **`completed` now expires: `/architect:report-status` and `/product:report-status` invalidate a
  finished phase when its upstream changes.** The dashboard read the progress registry as the last
  word on status, so fixing an earlier phase — rerunning it, or hand-editing the report it wrote —
  left every phase downstream sitting at `completed`, and the tree kept claiming a finished
  pipeline built from inputs that no longer existed. A completed phase whose dependency wrote an
  output *after* it finished is now shown as **`stale`** (`↺`, `@` in ASCII) in place of
  `completed`, naming the dependency that changed and when it changed. Invalidation propagates down
  the dependency graph in one topological sweep, so one edit at the top of the pipeline
  un-completes the whole chain below it: those phases leave the `n/m done` fraction and the group
  counts, become runnable again, take a rerun as their default action, answer the `f` status
  filter, and the suggested `next:` becomes the earliest of them — rerunning from the top is what
  clears the rest. Nothing is written back: the registry is untouched and `--json` carries both
  `status` (as recorded) and `display_status`. Deliberate limits, so the flag stays trustworthy: a
  5-second grace absorbs same-run write ordering, a dependency that never ran invalidates nothing,
  and a phase that declares outputs but wrote none stays plain drift — a claim already contradicted
  by the filesystem is no basis for deciding what it is older than. Asserted by
  `tools/lib/pipeline_status_data.test.py`.

## [0.21.0] - 2026-08-06

### Added
- **`/architect:report-status` and `/product:report-status` (new skills, haiku): live pipeline
  progress, in the same dashboard as the backlog.** The backlog delivery loop already had a live
  terminal view; the product and architect pipelines that precede it had none — `work/pipeline-progress.json`
  was readable only as raw JSON, and most skills only wrote to it when a phase finished, so
  "where are we right now" was unanswerable. The dashboard is now one tool, `tools/nexus-status.sh`,
  with two views switched by `Tab`: **pipeline** (new) and **backlog** (the existing one;
  `tools/backlog-status.sh` remains as a thin alias and `/architect:report-backlog-status` is
  unchanged). The pipeline view renders the phase tree grouped by category — the architect manual
  extension tier is its own foldable group — with each phase's status, how many of its declared
  `outputs:` actually exist (`[==..] 2/4`), whether it wrote a file or burned tokens in the last
  five minutes, its unmet dependencies, its model tier and its recorded cost; the product view adds
  the `validate-assumptions` gate verdict and open-assumption count in the header. Status is
  registry-first and filesystem-second: a phase with no registry entry is derived from its outputs,
  and a disagreement (`completed` with nothing written, `pending` with everything written) is
  flagged as drift rather than smoothed over. Both views share the action menu that generates the
  next slash command (clipboard, or `claude` under `--exec`), a new `a` key that asks Claude about
  the selected row with its context attached, and `?` for a help panel. `--once`, `--json` and
  `--md` render non-interactively for in-session use. New contract test:
  `tools/lib/pipeline_status_data.test.py`.
- **Progress registry `in_progress` contract (@skills/common/progress-registry.md).** Orchestrators
  (`/architect:pipeline`, `/architect:start`, `/product:start`) now write each phase twice —
  `in_progress` + `started_at` *before* invoking the skill, then `completed`/`failed` with
  `completed_at`, `outputs` and `summary` after — plus optional `note`/`updated_at` for a long
  phase's current step. This is what makes a running phase visible while it runs, and it is also
  what the token-usage hook uses to attribute cost; without it, tokens land in the pending bucket.
- **`/architect:capture-followup` (new skill, sonnet): follow-up capture for backlog delivery.**
  Work discovered mid-delivery — deferred tasks, out-of-scope findings, doc drift, split-off scope,
  waived acceptance criteria — previously dead-ended in comments and review prose. The skill
  captures it into a reviewable queue (`reports/backlog/followup-queue.md`) without interrupting
  the semi-autonomous implement run, then, after an explicit approval gate, registers the entries
  as tracker Issues labeled `status::todo`, linked to the in-flight Sub-Epic/Epic (native Epic
  link, or an unticked child box appended in place), and appended to `backlog-manifest.json` under
  a dedicated `F`-suffixed local-ID namespace (`I1.2.F1`) with an `origin` trail — disjoint by
  construction from `export-backlog`'s positional IDs, which now explicitly preserve follow-up
  nodes on `--update`. `implement-backlog`, `review-issue`, and `merge-issue` route their deferral
  points to the queue via `--queue-only`; `deliver-backlog` picks the created Issues up as
  ordinary `status::todo` work. The ID/manifest contract is asserted by
  `skills/capture-followup/followup-contract.test.py`, and the checklist contract gains the
  "append an unticked child box" operation owned by this skill.

- **`/architect:report-backlog-status` (new skill, haiku) + `tools/backlog-status.sh`: a live
  terminal dashboard for backlog delivery.** The Epic → Sub-Epic → Issue tree, foldable, with each
  item's delivery status (`todo/doing/review/done/blocked` — derived tracker-first, then
  `impl.status`, never the seed `labels` array) and its Implemented/Reviewed/Merged stage boxes;
  header shows overall Issue counts, the follow-up queue, and a pipeline phase strip. `Enter`
  opens a per-item action menu that generates the next slash command
  (`/architect:implement-backlog I1.2.3`, …) — copied to the clipboard by default, or run in the
  foreground via `claude` under `--exec`. `s`/`--sync` overlays live `glab`/`gh` labels and flags
  drift. The manifest is re-polled every 10s; `--once`/`--json`/`--md` render non-interactively.
  Built on the `token-cost-report` display layer (same `--ascii`/`--ambiguous-width` handling);
  the derivation contract is asserted by `tools/lib/backlog_status_data.test.py`.

### Changed
- **Checkboxes now render implementation state, not merge state.** The Epic/Sub-Epic child
  task-list boxes previously flipped only when `merge-issue` merged the child, so a fully
  implemented, tested, review-pending Epic still rendered 0% progress. The checklist contract now
  splits the two kinds of state: **checkboxes = implemented + tests passing** (ticked by
  `implement-backlog` once every acceptance criterion is ticked with test evidence, reconciled —
  including unticking with a reason — by `review-issue`), while **delivery state (merged/done)
  stays in the `status::*` labels and `impl.status`**. `merge-issue` no longer ticks in the normal
  flow; it verifies at merge and ticks only a missed box (the merged, CI-green result being the
  evidence). Updated across `backlog-checklists.md`, `implement-backlog`, `review-issue`,
  `merge-issue`, `deliver-backlog`, and `capture-followup`.
- **Every Epic/Sub-Epic/Issue body now carries a `## Delivery Status` section** — a `Status:` line
  mirroring the tracker label plus a stage checklist (`Implemented` / `Reviewed` / `Merged`; parents
  carry `Implemented`/`Merged`) — so the body answers "did it merge?", which the implementation
  checkboxes deliberately do not. `export-backlog` and `capture-followup` author it on new items;
  `implement-backlog`, `review-issue`, and `merge-issue` tick the stage they establish and rewrite
  the status line on every label transition; labels/`impl.status` remain the machine-readable
  source of truth. **Existing items are retrofitted**: any skill about to edit a body that lacks
  the section first appends it, initialized from the live tracker state. `export-backlog --update`
  preserves the section (and all ticked boxes) when syncing bodies.

### Documentation
- **`docs/analysis-mechanism_ja.md` (new): how the architect plugin actually analyzes existing code
  and design documents.** Walks the pipeline from `skills/common/skill-dependencies.yaml`, the two
  intake paths (`investigate` over code, `define-requirements` over RFPs/minutes/design docs), and
  the AST-first tool hierarchy (Serena MCP → Glob/Grep → Read → sub-agents), then opens the internal
  logic: symbol/reference traversal and how it detects naming drift, the two-stage rubric scoring
  that keeps evaluators on documented evidence, template-matching + gap-driven elicitation, LLM
  reading constrained by deterministic schemas, and the ubiquitous-language derivation. Closes with
  the progress-registry state machine, the exit-2 hook self-correction loop, the 5-perspective ×
  3-dimension review with its externalized quality gate, and a worked example on a fictional legacy
  EC monolith. Japanese only.

## [0.20.0] - 2026-08-05

### Added
- **`rules/scalardb-saga-patterns.md` (new rule): ScalarDB Saga.** The OKF knowledge bundle now
  carries ScalarDB Saga as a fourth product, so the toolkit treats saga orchestration as a
  first-class design option rather than a hand-rolled pattern: SAGA vs TCC selection, the
  idempotency and compensation constraints that are non-negotiable, saga definitions (declarative
  service steps vs embedded-only code steps), the saga lifecycle and `ESCALATED` operator queue,
  server vs embedded deployment with the artifact/Java matrix, and the `scalar.db.saga.server.*`
  configuration rules (security provider, `owner_id`, recovery timeout, retention).
- **ScalarDB 3.19 in the design and adoption path.** The cross-service transaction decision now
  ranks four mechanisms — shared-cluster one-phase commit, the 3.19 **Global Transaction API** with
  a Transaction Coordinator node, application-driven 2PC, and ScalarDB Saga — instead of defaulting
  to 2PC. Applied across `rules/scalardb-2pc-patterns.md` (renamed in scope to cross-service
  transactions), `design-scalardb`, `design-microservices`, `select-scalardb-edition`,
  `define-requirements`, `review-scalardb`, and `skills/common/references/interface-matrix.md`.
- **ScalarDB Saga added to the product plugin's standing technology-fitness checklist**
  (`/product:design-architecture`, `rules/product/architecture-and-tech-fitness.md`) — assessed
  every run alongside Kong, ScalarDB, ScalarDB Analytics and ScalarDL, triggered by eventual
  consistency across contexts rather than implied by a ScalarDB adoption.

### Changed
- **The greenfield applicability decision tree now routes eventual consistency to ScalarDB Saga.**
  `workflow/greenfield/01_requirements_analysis.md` Step 1.4 — the tree `/architect:define-requirements`
  actually walks — terminated the eventual-consistency branch at "ScalarDB not needed"; it now reaches
  ScalarDB Saga, gated on whether a compensation is definable for every step. The step is renamed to a
  Scalar **product** applicability assessment (ScalarDB / ScalarDB Saga / neither), assessed per
  business process, and it no longer presumes that a ScalarDB verdict implies 2PC. Step 1.5's XA
  comparison gains an application-complexity row reflecting the shared-cluster and Global Transaction
  API paths.
- **`/architect:design-scalardb-analytics` no longer claims "Enterprise Premium only"** — ScalarDB
  Analytics is a separately contracted Enterprise **Option**, so the skill now confirms licensing
  rather than assuming a Premium project has it. The same correction is applied to the edition tables
  in the Oracle / MySQL / PostgreSQL migration references (which also mislabelled ABAC as plain
  Premium rather than an Enterprise Premium Option) and to the skill-reference tables' condition
  column.
- **`/scalardb:migrate` checks whether a 1PC → 2PC migration is needed at all** before advising one —
  the shared-cluster pattern and the 3.19 Global Transaction API both keep application code one-phase
  across services — and notes that 2PC → 1PC simplification is correspondingly more often available.
- **OKF knowledge bundle updated to `7a723b8`** — adds ScalarDB 3.19 and ScalarDB Saga 3.19;
  2,015 concepts across 4 products and 21 version lines (was 1,800 / 3 / 19).
- **`rules/scalardb-edition-profiles.md` rewritten against the bundle's own feature matrix.** It
  had material errors: the SQL/JDBC/Spring Data/GraphQL interface is Enterprise **Premium**, not
  Standard, and ScalarDB Analytics is a separately contracted Enterprise **Option** rather than
  part of Premium. Now carries the five edition values the bundle uses (including
  `Enterprise Premium Option` for ABAC), the 3.19 capability table, cluster topologies for
  microservices, per-line maintenance-support windows, and the note that SLA figures come from the
  commercial contract rather than the edition name.
- **`rules/scalardb-exception-handling.md`**: the 3.19 Consensus Commit recovery APIs
  (`finishTransaction()`, `recoverRecord()`, write-set logging) are documented as low-level
  operational APIs that must not be called from application error handling, plus the new `ABORTED`
  / `ErrorInfo` semantics on the Cluster pause RPC (never unpause on `TIMED_OUT_STILL_PAUSED`).
- **`rules/scalardb-config-validation.md`**: the two properties added in 3.19, the group-commit /
  2PC incompatibility, and the `single-crud-operation` caveat.
- **ScalarDB artifact pins bumped `3.16.0`/`3.17.x` → `3.19.0`** across `spring-boot-integration`,
  all six code-pattern references, and the Oracle/MySQL/PostgreSQL migration templates; each
  coordinate verified against Maven Central and the v3.19.0 release assets.
- `/architect:design-observability` prefers ScalarDB Cluster's native OpenTelemetry support (3.19+)
  and adds saga-level signals when ScalarDB Saga is in the architecture.

## [0.19.0] - 2026-08-04

### Added
- **`/architect:report-token-cost` (new skill, haiku): report the cost the agent actually
  recorded, on the terminal.** The reporting counterpart to `/architect:estimate-token-cost` —
  where that one estimates a run a priori from lines of code, this renders what the
  `record_token_usage.py` hook logged into `work/token-usage.json` + `work/token-usage.jsonl`.
  Per-model cost is **recomputed** from `skills/common/references/model-pricing.json` rather
  than trusted from the ledger, so the report tracks price updates.
  - `tools/token-cost-report.sh` dispatches five modes over `tools/lib/token_cost_*.py`:
    an interactive **two-pane dashboard** (default on a TTY — select a phase / model / session
    / day / event above, read its detail below, where a session shows its transcript log
    including extended thinking; re-checks the ledger every 10s), `--once` for a single static
    render (summary, per-phase, per-model with input / output / cache-read / cache-write
    columns, daily timeline, top sessions, recent events), `--session=ID` for one session and
    its log non-interactively, `--follow` to stream each ledger event as it is appended, and
    `--json` / `--md` export.
  - Sessions are **named** — and their logs read — from the Claude transcripts the ledger
    points at, so the per-session table reads as prompts rather than as bare UUIDs.
  - Display options: `--since` window, `--breakdown=tokens|cost`, `--top=N`, `--lang`,
    `--currency=jpy --fx=RATE`, `--width`, `--color` / `--no-color`.

### Fixed
- **The report is measured in terminal columns, not characters.** Rules emitted one character
  per column, so on a terminal that renders East Asian *ambiguous* characters double-width a
  100-column rule drew at 200 and every separator ran past the edge; bars had the same defect.
  Both now budget columns. Tables shrink to the terminal in three passes and drop the
  per-model component columns rather than wrap, and `--follow` sizes its text columns to the
  real width instead of emitting constant 140-column lines.
- **The live dashboard no longer keeps fragments of the previous frame.** curses miscounts
  double-width cells, so its update optimizer skipped cells it believed already matched and a
  session's cost table could show the previous tab's numbers. The dashboard now forces a full
  repaint; `touchwin()` was not enough, since it re-copies the window but diffs against the
  same stale model.
- Scroll counters are drawn on the header and separator rows instead of over table content;
  the list pane never grows past its own content; and the key-bar row no longer fails its
  write on every frame by touching the bottom-right cell.

### Changed
- **New drawing options for terminals where the Unicode glyphs do not render.** `--ascii`
  (`--glyphs=ascii|unicode`) draws bars, rules and separators with `# . - | ->`; this is now
  the **default when the output language is `ja`**, since Japanese terminals commonly render
  ambiguous-width characters double-width and their fonts are chosen for kana and kanji rather
  than for shade blocks. English output keeps the Unicode set. `--ambiguous-width=1|2` tells
  the layout how many columns ambiguous characters occupy — never guessed, because no terminal
  reports the setting. `--debug[=PATH]` records the rendering environment and any dropped
  curses write. Only the *drawing glyphs* change; Japanese labels stay Unicode throughout.

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

[0.22.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.22.0
[0.21.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.21.2
[0.21.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.21.1
[0.21.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.21.0
[0.20.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.20.0
[0.19.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.19.0
[0.18.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.18.0
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
