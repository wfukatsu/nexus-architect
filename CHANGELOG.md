# Changelog

All notable changes to Nexus Architect are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Version numbers refer to the per-plugin versions in `.claude-plugin/marketplace.json`;
all three plugins (`product`, `architect`, `scalardb`) are released together under one number.

## [Unreleased]

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

[0.8.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.2
[0.8.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.1
[0.8.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.0
[0.7.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.7.0
[0.6.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.2
[0.6.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.1
[0.6.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.0
[0.5.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.5.0
[0.4.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.4.0
[0.3.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.3.0
