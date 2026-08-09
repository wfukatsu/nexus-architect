# Rules: Open Questions (all skills)

Applies to **every skill that would write `TBD`** — product, architect, scalardb alike.

An Open Question is a decision the run needs and does not have. The default response is to **ask
the user through `AskUserQuestion`**, with free text available for whatever the options cannot
express. `TBD` is what remains *after* asking — never the first move.

## 1. Resolution order

1. **Resolve it yourself** from what is already available: `--input` documents, existing
   `reports/**`, `work/context.md`, `work/traceability.json`, the version-pinned OKF bundle
   (@rules/okf-knowledge-bundle.md), a registry lookup (@rules/dependency-versions.md). Never ask
   for something an input document already answers — re-asking is a defect, not diligence.
2. **Ask the user** with `AskUserQuestion` (interactive runs). This is the premise: an unknown that
   the user owns gets asked, in the run that needs it.
3. **Record what is left** as a `TBD` plus an Open Questions entry with a status saying *why* it is
   still open (§6).

In an interactive run, writing `TBD` for an item that was never asked is a defect. Guessing a value
is always a defect.

## 2. What to ask — and what never to ask

| Ask the user | Do not ask |
|--------------|------------|
| Decisions the user owns: scope in/out, priority, target numbers, budget, naming, tradeoffs, terminology, ownership, which of two designs to take | Facts you can look up — dependency versions, ScalarDB behavior, config keys, API shapes. Look them up |
| Confirmations that change the artifact: a consistency class, an SLO, a bounded-context boundary | Anything an input document or an upstream report already states |
| A choice between candidates you derived and can describe the consequences of | Verification the user cannot perform in-session — trademark clearance, vendor quotes, legal review, a security audit. These are `external` entries with an owner, not questions |

Two adjacent contracts are **not** Open Questions and keep their own rules: confirming a resolved
dependency-version set (@rules/dependency-versions.md §4 — looked up first, then confirmed per
`--confirm-versions`) and the validation gate's assumption tests (@rules/product/assumption-validation.md
— an `ASM-` is tested against reality, not answered in chat). Do not convert either into an `OQ-`.

**Budget the asking.** Prioritize by collapse impact — ask what changes the artifact, defer what is
cosmetic. Target at most 3–4 questions per stage and 2 rounds per skill; a long interrogation gets
abandoned, and an abandoned interview yields worse answers than a short one.

## 3. Question shape

- **1–4 questions per `AskUserQuestion` call.** Batch related ones into a single call rather than
  firing them one at a time.
- `header` ≤ 12 characters; `question` is one sentence, ending in a question mark.
- **2–4 options**, mutually exclusive, each a *candidate answer the skill derived from context* —
  not a generic placeholder. Each `description` states the downstream consequence of choosing it
  ("Strong consistency — pulls this process into a single ScalarDB transaction"), so the user is
  choosing an outcome, not a word.
- Put the recommendation **first**, labelled `(Recommended)`, when the skill has one.
- Use `multiSelect: true` when the answers are not exclusive (which channels are in scope, which
  personas to model).
- Use `preview` when the options are concrete artifacts to compare — mock layouts, schema
  fragments, token sets, naming candidates. `preview` works on single-select questions only, so a
  question that needs previews cannot also be `multiSelect`.
- Add an explicit **"Defer — record as TBD"** option only where deferral is a legitimate answer.
  Choosing it creates the Open Questions entry (`deferred`) with owner and impact; it does not
  discard the question.
- **Never author an "Other" option.** The harness always appends one, and it is the free-text path
  (§4). Authoring one duplicates it and eats an option slot.

## 4. Free text is always available — and must be usable

The appended "Other" option accepts arbitrary text. Design every question so that path stays open:

- When the option set is plausibly incomplete, say so in a `description` — "choose Other to enter
  the exact figure" / "choose Other to name a different owner".
- For an **inherently free-form answer** (an exact numeric target, a product name, a URL, a
  rationale, a list), take one of two shapes:
  1. `AskUserQuestion` whose options are **representative bands or candidates** — `p95 < 100 ms` /
     `< 500 ms` / `< 1 s` — so a user with a precise number reaches it through Other; **or**
  2. a plain chat question, when no meaningful bands exist. Ask it in prose and wait — do not skip
     straight to `TBD` because the answer would not fit a menu.
- **Record free text verbatim** and mark it as free text. It was not constrained by the options, so
  downstream skills must not treat it as if it had selected one. Never round a free-text answer to
  the nearest option — that silently discards the user's actual answer.
- Normalize only units, formats and IDs (`"about half a second"` → `p95 ≤ 500 ms`), and echo the
  normalization back for confirmation when the value becomes a requirement.
- A free-text answer that reveals the question was wrong (wrong framing, wrong granularity)
  supersedes the question: re-ask the corrected one rather than filing the answer under the old.

## 5. `--auto` and non-interactive runs

Do not ask. Every unresolved item becomes an Open Questions entry with status `unasked`, carrying
**the question text and the options that would have been offered**, so a later interactive pass — or
the user reading the report — can answer it directly instead of rediscovering it. `report` and
`review` surface these prominently — product via `work/context.md`
(@rules/product/review-and-report.md), architect via `reports/00_requirements/open-questions.md`,
which `define-requirements` writes as a first-class deliverable.

## 6. Recording

Open Questions are written to the run's Open Questions store — `reports/00_requirements/open-questions.md`
(architect), `work/context.md` § Open Questions (product), plus the artifact's own `## Open Questions`
section where its template has one. One row per question:

| Field | Meaning |
|-------|---------|
| `OQ-###` | Stable ID, allocated once and reused when the question is re-asked later |
| Question | The question as it was (or would be) asked |
| Status | `answered` \| `deferred` \| `unasked` \| `external` |
| Answer | The chosen option, or the free-text answer verbatim marked `(free text)`. Empty unless `answered` |
| Options offered | The options presented (or that would have been) — lets a later pass re-ask without re-deriving |
| Owner | Who must answer — required for `deferred` / `unasked` / `external` |
| Impact | Which downstream phases / IDs are blocked or are proceeding on an assumption |
| Asked at | ISO8601, when it was put to the user |

Rules:

- A `TBD` written into an artifact **carries its question ID** — `TBD (OQ-012)` — so review and
  report can join placeholder to question.
- `answered` means the artifact no longer says `TBD` for it: substitute the answer at the
  placeholder and keep the entry as the decision record.
- `external` items are never presented as cleared (trademark, availability, audit) — they stay open
  with an owner until evidence arrives.
- **A user answer that contradicts an input document or an upstream artifact wins** — but the
  contradiction is recorded in the entry (what the document said, what the user answered) and
  surfaced to the artifact that carried the old value. Never overwrite it silently.

## 7. Carrying questions forward

At its "read context" step, every skill loads the existing Open Questions and picks up any
`deferred` / `unasked` entry **in its own domain that it now needs an answer to**. It re-asks that
entry in its own first `AskUserQuestion` batch — reusing the recorded options, refined by what is
now known — and updates the entry **in place under the same `OQ-` ID**. Answering never creates a
duplicate entry, and a question already `answered` is never re-asked.

## 8. Other runtimes

Codex and the omnigent loader have no `AskUserQuestion` tool. They present the identical content as
a numbered list, followed by an explicit "or type your own answer" line, and wait for the reply — a
typed answer matching no number is a free-text answer and is recorded per §4. See `AGENTS.md` and
`OMNIGENT.md`.
