# Explanation Formats

The shapes Steps 4, 6 and 7 use. Headings are written in the output language; the labels
**Fact**, **Concept** and **Inference** are translated into the output language like the headings,
but are always present. A section with nothing to say is left out rather than filled.

## Labelling

Put the label at the start of the sentence or bullet it governs, and the citation at its end:

```markdown
- **Fact** — `OrderService.place` begins one transaction, writes the order and the stock
  reservation, and commits (`generated/order/src/main/java/.../OrderService.java:42-71`).
- **Concept** — An aggregate is the unit a single transaction writes, so its invariants hold
  after every commit (`rules/aggregate-design.md` §1).
- **Inference** — The stock reservation is written in the same transaction, probably to avoid
  overselling; no ADR states this.
```

A paragraph made of one kind may carry the label once, at its start.

## Overview

```markdown
## {Target name} — overview

**In one paragraph.** What it is, who it is for, what it decides or does.

### Where it sits
Producer skill, its inputs, what consumes it. A short chain:
`define-requirements → design-microservices → (this) → generate-scalardb-code`.

### Parts and how they connect
A table of parts (name, responsibility, file) and, past about five parts, a Mermaid diagram.

### How one {request | decision} flows through it
A numbered walk through one representative case, each step cited.

### Why it is this way
Each decision: what was chosen, over what, why — cited from the ADR or report. Unstated reasons are
Inference.

### Gaps found while reading
Fact-labelled discrepancies with both citations, and the skill that owns the check.
```

## Terms

One entry per term, ordered so that no term is used before it is defined:

```markdown
### {Term} ({English term, when the output language is not English})
- **Analogy** — `beginner` only: one everyday comparison, labelled as an analogy.
- **In this project** — meaning as used here, with citation.
- **In general** — the textbook meaning (Concept).
- **Difference** — only when the two differ.
- **Also appears in** — other files that use it.
```

## Code walkthrough

```markdown
### `{Symbol}` — {responsibility in one sentence}
| | |
|---|---|
| Inputs | parameters and their meaning |
| Output | return value, or what it writes |
| Side effects | database writes, messages, external calls |
| Errors | what can fail and how it is handled |
| Transaction | where it begins and ends, and who owns it |
| Implements | the design element, with its citation |

**Step by step**
1. Lines 42–48: … (Fact)
2. …

**Worth noticing** — one to three points the reader would otherwise miss (a retry, an ordering
constraint, a deliberately missing check), each labelled.
```

Quote only the lines being discussed, at most about fifteen per excerpt, with their path and line
range.

## Pattern

```markdown
### {Pattern}
- **Problem it solves** (Concept)
- **Structure in general** (Concept; a small diagram when it helps)
- **Where it appears here** — every participating file or section (Fact)
- **This project's version** — how it differs from the textbook one, and why if a file says why
- **Trade-off** — what it buys and what it costs, in this project's terms
- **Governing rule** — the repository file from `pattern-catalog.md`
```

## Saved explanation (`--save`)

```markdown
---
title: "Explanation: {target} ({focus})"
schema_version: 1
phase: "Utility: Explanation"
skill: explain
generated_at: "{ISO8601}"
input_files:
  - {the target — always first}
  - {every other file cited}
level: {beginner|intermediate|expert}
---
```

The body is the overview followed by each topic covered in the session, in the order given.
