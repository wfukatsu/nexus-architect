---
description: |
  Explain a generated design or code (reports, generated code, UI mocks) from its files, and on
  request teach the terms, functions and patterns it uses.
argument-hint: '[target] [--focus=overview|terms|code|patterns|all] [--level=beginner|intermediate|expert] [--save] [--lang=en|ja]'
model: sonnet
---

# Explain Generated Designs and Code

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

**Usage:** `/architect:explain [target] [--focus=overview|terms|code|patterns|all] [--level=beginner|intermediate|expert] [--save] [--lang=en|ja]`

A read-only guide to what the two pipelines produced. It explains an artifact first, and teaches
the ideas underneath it only when the user asks to go deeper.

## Desired Outcome

The reader understands what they are looking at well enough to review it, change it, or explain it
to someone else:

- **What it is and where it sits.** Which skill produced the artifact, what it consumed, what
  consumes it, and where it sits in the product → architect → codegen chain.
- **How it works.** The parts, how they connect, and the path a request or a decision takes through
  them — with a diagram when the structure has more than a handful of parts.
- **Why it is this way.** The decisions behind it, cited from the ADRs, design reports and product
  artifacts that made them — not invented after the fact.
- **On request, the education underneath.** The vocabulary it uses, a walkthrough of its functions,
  and the architecture and implementation patterns it applies — each tied back to the exact place in
  this project where it appears.

## Decision Criteria

- **Ground every claim in a file.** What the artifact does or says is read from it and cited as
  `path:line` (code) or `path § heading` (documents). A claim that cannot be cited is not made.
- **Keep three kinds of statement apart.** Each explanation labels what it says as one of:
  - **Fact** — read from this project's files, with the citation.
  - **Concept** — general knowledge about a term or pattern, with its source in this repository's
    rules when one exists (see `reference/pattern-catalog.md`).
  - **Inference** — intent the files do not state. Marked as inference, and never presented as a
    decision someone made.
- **Explain, do not review.** No severity, no verdict, no fix list — that is the review skills'
  work. When the explanation exposes a gap between design and code, or between two documents, state
  the gap plainly as a Fact with both citations and name the skill that owns the check
  (`/architect:verify-implementation`, `/architect:review-consistency`, `/product:review`). Do not
  smooth it over in prose.
- **Read only.** Nothing in the project is edited. The one write is the optional saved explanation
  (Step 7), and only when the user asked for it.
- **Overview first, depth on request.** Terms, code walkthroughs and patterns are offered, not
  imposed. What `--focus` changes:

  | `--focus` | Overview (Step 4) | Offer to go deeper (Step 5) | Topics (Step 6) |
  |-----------|-------------------|-----------------------------|-----------------|
  | none, or `overview` | Full | Yes | Those the user picks |
  | `terms`, `code` or `patterns` | The one-paragraph summary, plus the gaps found while reading | Yes, for the other topics | The one named |
  | `all` | Full | No | All three |
- **Fit the reader.** `--level` sets how much is assumed: `beginner` defines every non-everyday
  term and uses an analogy before the precise statement; `intermediate` defines only domain and
  pattern terms; `expert` skips definitions and concentrates on the project-specific choices and
  their trade-offs.
- **Project vocabulary wins.** A term is explained as this project uses it first — the ubiquitous
  language and glossaries the pipelines wrote — and only then in its general sense. Where the two
  differ, say so.
- **Small, real examples.** Illustrations are excerpts from the project's own files. An invented
  example is allowed only to explain a general concept, and is labelled as one.

## Prerequisites

| File / source | Required/Recommended | Produced by |
|---------------|----------------------|-------------|
| The target: any file or directory under `reports/`, `generated/`, `design-system/`, or the project's source tree | Required | any architect or product skill, or the user |
| `work/pipeline-progress.json` | Recommended | `/architect:init-output`, `/product:init-output` |
| `work/traceability.json` | Recommended | product and architect skills that mint IDs |
| Ubiquitous language / glossary (`reports/01_analysis/ubiquitous-language.md`, `reports/03_domain/`) | Recommended | `/architect:analyze`, `/product:map-domains` |
| ADRs (`reports/03_design/adr/`, `reports/08_infrastructure/adr/`) | Recommended | `/architect:redesign` and later design skills, `/infra:design` |

Read the output language from `work/pipeline-progress.json` (`options.output_language`, default
`en`); `--lang` overrides it. With neither, answer in the language the user wrote in. Code
identifiers, file paths, commands and config keys stay verbatim.

## Step 1: Resolve the Target

1. With a `target`, resolve it as a path first, then as a name: a service under `generated/`, a
   bounded context, an aggregate, an ID (`ADR-007`, `FR-012`, `RULE-003`), or a symbol (find it with
   Serena `find_symbol`, or Grep).
2. With no `target`, list what exists — the top-level groups of `reports/`, each service under
   `generated/`, `design-system/`, and the project's own source roots (`src/`, or each module's) —
   ordered by the newest file inside each, ties alphabetical. Ask with `AskUserQuestion` which to
   explain, offering the first four ("Other" takes a path or name); the four-item cap is the
   question's, so a candidate list shown without a question lists them all.
3. Identify the owner of each file: the `skill` key in its frontmatter first; otherwise the
   `phases` entry in `work/pipeline-progress.json` whose outputs list it (the entry's `plugin` field
   tells architect from product, since `map-domains`, `design-api`, `create-domain-story` and
   `report` exist in both); otherwise the location table in `reference/artifact-map.md`.

When the target is ambiguous — a name matching both a product and an architect artifact, or several
symbols — ask rather than pick.

## Step 2: Settle Level and Focus

Without `--level`, take the level from the request when it states one ("I'm new to DDD" →
`beginner`; "I know Spring well, just show me the ScalarDB parts" → `expert`), and say in one line
which level was taken and from what. Only when the request gives no sign, ask once with
`AskUserQuestion`: beginner / intermediate / expert, each option's description saying what will
and will not be defined. What `--focus` does is the table in Decision Criteria.

**When the user cannot be asked** — the skill runs inside a sub-agent, in a non-interactive
session, or `AskUserQuestion` is refused — nothing waits for an answer: the level defaults to
`intermediate`, Step 5 is skipped, and a missing `target` ends the run with the candidate list from
Step 1 instead of a question. State every default that applied, including a skipped Step 5, in
one line at the top of the explanation.

## Step 3: Gather the Context

Read, in this order, and stop once every section of the overview (Step 4) can be written from what
has been read:

1. The target itself — whole for a document; for code, the files the target names plus their build
   file and entry point.
2. What it consumed: the `input_files` in its frontmatter, or the upstream phases in
   `@skills/common/skill-dependencies.yaml` and `@skills/product/common/skill-dependencies.yaml`.
3. Why it is this way: ADRs whose `upstream` names the target's IDs, and the design reports the
   code was generated from (`reports/03_design/`, `reports/03_design/aggregates/`, the API
   specifications).
4. What consumes it: downstream phases in the manifests, and edges in `work/traceability.json`.
5. The project vocabulary: the ubiquitous language and glossaries named in Prerequisites.

When the target is a directory with more than about twenty files, delegate the inventory to one
sub-agent — `subagent_type: "Explore", model: "sonnet"` — asking for a digest: each file's role in
one line, the entry points, the main call or dependency paths, and the IDs and ADRs it references,
every item with its path. Explain from the digest and read only the files the explanation cites.

## Step 4: Give the Overview

Write the overview in the shape of `reference/explanation-formats.md` § Overview: a one-paragraph
summary, where it sits in the chain, its parts and how they connect (a Mermaid diagram per
@rules/mermaid-best-practices.md when there are more than about five parts — components, classes
or files, counting references to other aggregates or services), how one representative
request or decision flows through it, the decisions behind it with their citations, and the gaps
found while reading. Every statement carries its Fact / Concept / Inference label as that format
shows.

## Step 5: Offer to Go Deeper

Unless `--focus=all`, ask with `AskUserQuestion` (`multiSelect: true`) what to explore next —
after a named topic, offering only the topics not yet covered. The options are the three topics of Step 6, each with a description naming two or
three concrete items found in this target — "Terms: Aggregate, Saga, error budget", "Code:
`OrderService.place`, `OrderRepository`", "Patterns: Hexagonal, Saga". "Other"
takes a specific term, function or pattern. When the user picks nothing, stop.

After each topic, offer the menu again with the items not yet covered, until the user stops.

## Step 6: Teach the Topics

Read `reference/explanation-formats.md` for the shape of each, and
`reference/pattern-catalog.md` before explaining any pattern.

- **Terms.** Collect the terms the target uses that the reader's level does not assume: domain
  terms from the ubiquitous language, design terms (bounded context, aggregate, idempotency key,
  SLO), and technology terms (ScalarDB Microservice Transaction API, Problem Details, DTCG token). For each: the
  meaning in this project with its citation, the general meaning, how they differ if they do, and
  where else in the project it appears. Order them so that no term is used before it is defined.
- **Code.** When the target is a class or module and no function was named, walk through its
  public entry points: the one carrying the most logic in full, the rest in one line each, with an
  offer to expand any of them. For each chosen function, class or module: its responsibility in one sentence, inputs
  and outputs, a walkthrough of the body in steps with line references, side effects (writes,
  messages, external calls), error and exception paths, transaction boundaries, and the design
  element it implements (the aggregate command, API operation or state transition it realises,
  with the design file's citation). For ScalarDB code, ground the explanation of its API and
  exception behaviour in @rules/okf-knowledge-bundle.md and the ScalarDB rule it follows.
- **Patterns.** For each architecture or implementation pattern found: the problem it solves, its
  structure in general, where it appears in this project (every participating file or section,
  cited), how this project's version differs from the textbook one and why if a file says why, the
  trade-off it buys, and the repository rule that governs it. Detect patterns from the signals in
  `reference/pattern-catalog.md`; name a pattern only when its signals are present, and say "looks
  like X, but …" when they are only partly present.

Product artifacts are explained the same way: their frameworks — JTBD, Kano, RICE and MoSCoW,
North Star Metric, Lean Canvas, Domain Storytelling, Example Mapping, API-led connectivity, Atomic
Design, DTCG tokens, SLO and error budgets — are the "patterns" of a product document, and the
catalogue lists them with their rule files.

## Step 7: Save (only with `--save`)

Write the explanation given in this session to
`reports/explanations/{target-slug}-{focus}.md`, where `{focus}` is `overview`, `terms`, `code`,
`patterns` or `all`, and `{target-slug}` is the file or directory name without its extension, in
kebab-case (`aggregate-order`, `order` for `generated/order/`, `order-service` for
`OrderService.java`) — prefixed with its parent directory's name
(`aggregates-aggregate-order`) when a file with that slug already exists and the first entry of its
`input_files` is a different target. The target is therefore always the first `input_files` entry. It
carries the frontmatter of @rules/output-conventions.md with `phase: "Utility: Explanation"`,
`skill: explain`, `generated_at` set to the current time, and `input_files` listing every file
cited. The body is the overview followed by each topic in the order it was covered, under the
headings of `reference/explanation-formats.md`.
Re-running on the same target and focus replaces the file. Without `--save`, nothing is written; when
something was explained, mention at the end in one line that `--save` keeps it as a document.

## Error Handling

| Situation | Action |
|-----------|--------|
| Target not found | Say what was searched, list the nearest matches, and ask |
| Target is binary or generated output too large to read (minified bundle, lock file) | Explain it from its source or build configuration instead, and say so |
| No `work/pipeline-progress.json` | Explain from the files alone; owner and upstream come from frontmatter and `reference/artifact-map.md` |
| No `generated/` tree (a legacy project, or code not generated yet) | Explain the code in the project's own source tree the design refers to, and say which tree was read |
| A cited upstream file is missing | Explain without it and state as a Fact that the input it names is absent |
| The user asks for a review, a fix or a redesign | Name the skill that does it and stop; this skill does not change artifacts |
