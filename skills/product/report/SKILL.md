---
description: |
  Consolidate all product artifacts into one self-contained HTML report (Mermaid inline) that leads
  with a mandatory "Key Assumptions & Validation Status" section — gate verdict, open assumptions,
  every TBD, and Open Questions — before any design content. /product:report [--auto] [--lang=ja|en].
model: sonnet
user_invocable: true
---

# Consolidated Report

## Desired Outcome

Produce one deliverable:

1. **Full report** — `reports/report/full-report.html`:
   - **Leads with "Key Assumptions & Validation Status"** — the gate verdict, untested/open
     assumptions with thresholds, every `TBD` / `TBD-assumption`, and Open Questions grouped by
     status (`deferred` / `unasked` / `external`) with their owners, so a question nobody has been
     asked yet is visibly different from one the user consciously deferred
     (@rules/open-questions.md §6)
   - Then a section per phase in pipeline order, each linking to its source file
   - Mermaid diagrams rendered inline; self-contained (inline CSS), no external assets beyond the
     Mermaid runtime

## Invocation

```
/product:report [--auto] [--lang=ja|en]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--auto` | Optional | Generate from whatever artifacts exist |
| `--lang` | Optional | Override output language |

## Decision Criteria

- **Assumptions first.** The validation status sits at the very top — the reader must see what is a
  bet before reading the design.
- **Never fabricate a "pass".** A missing artifact or a `no-go` verdict is stated prominently.
- **Self-contained.** Inline CSS; render Mermaid; no broken external references.
- **Stop condition**: the Key Assumptions section is present and complete, all existing artifacts are
  included in pipeline order, and Mermaid blocks render.

## Prerequisites

| Input | Required/Recommended | Source | If missing/empty |
|-------|---------------------|--------|------------------|
| `reports/**/*.md` | Required | all prior skills | include whatever exists; note missing phases |
| `work/pipeline-progress.json` | Required | `/product:init-output` | the gate banner says the gate has not been evaluated |
| `reports/00_core/assumptions.md` | Recommended | `/product:validate-assumptions` | assumptions section says the document does not exist |
| `work/context.md` § Open Questions | Recommended | all skills | Open Questions section says the store does not exist |

## Execution

**The report is built by a tool, not authored.** Do not read the report tree and write HTML
by hand, and do not convert the Markdown with pandoc or any other converter: the rendering —
Mermaid escaping, anchors, article ids, section order, the bilingual chrome, the
assumptions header — is a contract the tool owns and a test suite guards
(`tools/build_report.test.py`). A hand-written or pandoc-converted report drifts from that
contract silently; in particular a converter wraps a Mermaid fence as
`<pre class="mermaid"><code>…</code></pre>`, and Mermaid's `startOnLoad` reads
`innerHTML`, so every diagram then fails with "No diagram type detected". The tool emits
`<pre class="mermaid">` holding the escaped source and nothing else.

One command does the whole job:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/build-report.py" <project_dir> --layout product [--lang ja|en]
# --layout product    always passed: a project that has already handed off to /architect:*
#                     holds both report trees, and detection then prefers the architect layout
# --output PATH       write somewhere other than reports/report/full-report.html
# --mermaid-js PATH   inline this copy of mermaid.min.js instead of the resolved default
```

`<project_dir>` is the project root — the directory holding `reports/` and `work/`; it
defaults to the current directory. Without `--lang` the tool reads `options.output_language`
from `work/pipeline-progress.json` itself. Without an explicit layout the tool detects one
from the report tree — product when only `reports/00_core` / `01_ux` / `02_spec` /
`03_domain` exist, architect as soon as any architect directory does — which is why this
skill always names the product layout on the command line.

Steps:

1. **Run the command.** Exit 0 means the report was written. Exit 1 means the directory has
   no `reports/` (wrong project root), or the Python dependencies are missing — in that
   case run `pip install -r requirements.txt` and retry.
2. **Record what it printed.** One line: the article count, the number of Mermaid blocks
   embedded, the byte size, whether Mermaid was inlined or left to the CDN, the layout and
   the output path. Report those numbers to the user rather than re-describing the report's
   contents.
3. **Stamp the phase** in `work/pipeline-progress.json` per @skills/common/progress-registry.md
   — `in_progress` before the run, then `completed` with `outputs` and a one-line `summary`
   afterwards. Write `"plugin": "product"`: `report` is defined by both manifests, so that
   field is the only thing that says whose entry this is.
4. **Note it** in `work/context.md` — one line under the report phase with the printed numbers.

The tool inlines Mermaid from the first copy it finds — the one named on the command line,
then `<repo>/tools/docs-site/node_modules/mermaid/dist/mermaid.min.js`, then
`~/.cache/nexus-architect/mermaid.min.js` — and falls back to a CDN `<script src>` with a
visible note in the report when none exists.

## Input Sources

The tool compiles the directories below (skipping any that do not exist). Section headings
render in the configured language; the English names are the canonical section identifiers
and the `<h2 id>` of each section regardless of language.

| Directory | Section heading (English canonical) | Notes |
|-----------|--------------------------------------|-------|
| — | Key Assumptions & Validation Status (`summary`) | gate verdict from `gates.validate-assumptions`, the open `ASM-` rows of `assumptions.md` and `validation-plan.md` verbatim, `TBD` / `TBD-assumption` per document with the `OQ-` they cite, Open Questions grouped by status with owner and impact |
| `reports/00_core/` | Product Core (`core`) | |
| `reports/01_ux/` | UX Foundation (`ux`) | `domain-stories/` as a subgroup |
| `reports/02_spec/` | Specification (`spec`) | `examples/` as a subgroup, `index.md` first; `ui-mocks/` Markdown as articles, HTML mocks listed by name |
| `reports/03_domain/` | Domain & Architecture (`domain`) | `figures/`, `slides/` listed by name only |
| `reports/04_quality/` | Quality & NFR (`quality`) | |
| `reports/05_adaptation/` | Adaptation (`adaptation`) | |
| any other `reports/<dir>/` | Other Documents (`other`) | one subgroup per directory, top-level Markdown only |
| `reports/report/review.md` | Review (`review`) | |

Within a section, documents follow the pipeline order of
`skills/product/common/skill-dependencies.yaml` (`phases.*.outputs`); documents the manifest
does not declare come after them in name order. Non-Markdown assets are never embedded.

## Output

`reports/report/full-report.html`, leading with validation status and consolidating all artifacts.

## Reference Materials

| Resource | Purpose |
|----------|---------|
| `@rules/product/review-and-report.md` | Report structure and the mandatory assumptions header |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `/product:review` | Upstream — findings can be surfaced in the report |
| `/product:validate-assumptions` | Upstream — supplies the gate verdict and open assumptions |
| `/product:start` | Orchestrator — typically runs `report` as the final step |
