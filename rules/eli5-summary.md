# ELI5 Summary

Every report written for engineers opens with a short section a non-engineer can read: the
decision or finding in everyday words, what it means for them, and what they are being asked to
decide. The technical body below it is unchanged — it is what the next skill reads. This rule says
when the section is required, where it goes and what shape it has.

## 1. When

`options.eli5` in `work/pipeline-progress.json` (`skills/common/progress-registry.md` § Options):

| Value | The section is required in |
|-------|----------------------------|
| `technical` (the default — also when the option is absent) | every Markdown report whose frontmatter `skill:` is in `TECHNICAL_REPORT_SKILLS` of `tools/lib/report_audience.py` — investigation, analysis, evaluation, design, review synthesis, verification, estimation, the product pipeline's data-model / domain / SLA / NFR / architecture documents, and the infra design and review documents |
| `all` | every Markdown report under `reports/`, whatever its skill |
| `off` | none |

The list lives in that module and nowhere else; the hook, this rule and the tests read it. Two
documents are exempt in every mode: an Architecture Decision Record (its frontmatter carries
`decided_at` — the shape of @rules/architecture-decision-records.md §2; its Context section is
already the plain statement) and a document whose frontmatter declares `eli5: false` — the
opt-out for a technical skill's non-prose output, such as an environment matrix that is one table.

## 2. Where

Immediately after the `# Title` line, before any other `##`. The heading is the fixed token
`## ELI5` followed by a localized subtitle:

- `## ELI5 — the short version` (`output_language: en`)
- `## ELI5 — やさしい説明` (`output_language: ja`)

The hook matches the token, not the subtitle; keep `## ELI5` at the start of the line.

## 3. Shape

Three parts, in this order, 120–250 words in English or 300–600 characters in Japanese:

1. **The picture.** One paragraph. One everyday analogy, labelled as an analogy ("Think of it as
   …"), that says what this document decides or finds — the same device
   `/architect:explain --level=beginner` uses.
2. **What it means for you.** Three to five bullets stating the consequences in plain words —
   money, time, risk, what users will notice. Every bullet restates something the body says;
   nothing appears here first.
3. **What you are asked to decide.** One bullet per open point the body leaves to the reader,
   naming its ID (`OQ-012`, `ADR-004`, `RSK-203`) and the choice in one sentence. When there is
   none: "Nothing — this is for your information."

```markdown
# Transaction Boundary Design

## ELI5 — the short version

Think of it as a checkout line with one cashier per order (an analogy): every order is paid for in
one go, so a shopper never ends up half-charged. Payments that reach the card company are a
separate line, and we have to agree how a failed card payment is undone.

**What it means for you**
- An order is either fully placed or not at all; there is no "stuck" order to clean up by hand.
- Checkout is slower by about a tenth of a second at peak, which nobody will notice.
- If the card company is down, orders wait instead of failing.

**What you are asked to decide**
- OQ-014: whether an order that was paid but could not be recorded is refunded automatically
  (within a day) or handed to support.

## Overview
…
```

## 4. Writing rules

- No term a non-engineer would not know unless it is glossed in parentheses on first use; no
  acronym without its expansion. "Saga" becomes "a chain of steps that can each be undone".
- Numbers only when they change a decision; scores, counts and percentages stay in the body.
- No citations — the body carries them. The section is a restatement, so a reviewer checks it
  against the body like any other claim; a sentence the body does not support is a defect.
- Write it **after** the body, so it summarises what is actually there.
- The language is `options.output_language`; the heading subtitle switches with it (§2).
- It is not an executive summary of scores, and not a replacement for the body. A reader who
  wants more goes to `/architect:explain --level=beginner` on the same file.

## 5. Enforcement

`hooks/validate-frontmatter.sh` fires on every Write and Edit under `reports/**` inside a pipeline
project. When the section is required (§1) and no line starts with `## ELI5`, it fails with exit 2
and the message names this rule, so the writer adds the section and writes the file again. The
consolidated HTML report (`tools/build-report.py`) gathers every ELI5 section into its executive
summary as the "ELI5 digest", one entry per document, linked to the document.
