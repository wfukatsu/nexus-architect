# product Plugin — Input Requirements Guide

A reference for the information **you (the user) need to supply** to run the `product` plugin.
Files that skills generate or hand off automatically (artifacts under `reports/`, etc.) are out of scope; this focuses on the information a human must bring to run the pipeline.

For the architect plugin, see [architect-input-requirements.md](architect-input-requirements.md).

## Common Principles

- **Never fabricate.** Market data, competitor names, numbers, and requirements must be grounded in an input document, a user answer, or cited web research. Unknowns are never guessed — they are recorded as `TBD` (Open Questions).
- **Gap-driven elicitation.** Provided materials are read first; only items the materials do not answer are asked. The richer your inputs, the shorter the dialogue.
- **Two execution modes.** Interactive (default) and `--auto` (skips elicitation, generates from input documents only; unknowns become `TBD`). `--auto` errors out if there are no inputs at all.
- **Output language.** Switched via `options.output_language` in `work/pipeline-progress.json` (`en` default / `ja`). The input material itself can be in any language (Japanese sources are fine).

## Purpose and Entry Points

**Purpose:** design product direction from vision to SLA/NFR in a validation-driven way, then hand off to `/architect:define-requirements`.

**Entry points:** `/product:start` (orchestrator) or `/product:define-vision` (first phase, standalone).

## 1. Minimum Inputs to Prepare

| Input | Necessity | Content | If absent |
|-------|-----------|---------|-----------|
| Product idea / one-liner (`target`) | Recommended (effectively required in interactive mode) | Product name, or a one-line "for whom / what problem / how solved" | Drawn out via dialogue (not possible under `--auto`) |
| Business overview material (`--input=<file\|dir>`) | Recommended | Business brief, RFP, meeting notes, prior docs. Text/Markdown/PDF. Repeatable / directory allowed | Filled in via dialogue |
| Output language (`--lang` or selection at init) | Recommended | `ja` / `en` | Confirmed via dialogue |

> Under `--auto`, **at least one** of the "idea" or the "`--input` material" is required.

## 2. Additional Inputs That Improve Accuracy / Shorten the Dialogue

Preparing these reduces questions in the relevant phase and reduces `TBD`s (all are otherwise supplied via dialogue or web research).

| Information category | Main phases | Examples |
|----------------------|-------------|----------|
| Target customers / segments | define-vision / generate-persona | Who it is for ("everyone" is not allowed — always segmented) |
| Problem / job to be done (JTBD) | define-vision / generate-persona | The job the customer wants done; existing alternatives |
| Market / competitor facts | research-landscape / define-vision | Market size, competitor names, alternatives (else cited web research or `TBD`) |
| Definition of success / KPIs | define-success-metrics | North Star candidates, metrics you care about |
| Revenue / business-model assumptions | design-revenue | Pricing model, price range, LTV/CAC assumptions |
| Constraints (`--constraints=<file\|text>`) | define-scope | Technical / budget / schedule / regulatory / existing assets |
| Design system (`--import=<path>`) | design-system | Existing Tailwind / DTCG / Figma Tokens / CSS theme |
| Customer expectations on SLA / availability | design-sla / define-nfr | Acceptable downtime, latency expectations, RPO/RTO |

## 3. Items Asked Interactively During Execution

In interactive mode, each phase confirms missing information as it goes. Representative checkpoints:

- **Vision:** target group (segmentation required), problem/job, benefit, Go/No-Go criteria
- **Validation gate (validate-assumptions):** the riskiest assumptions and their test results (re-runnable as evidence arrives). A `no-go` here loops back to revising earlier artifacts.
- **Scope:** what's in / out (MoSCoW / RICE)
- **Revenue:** assumptions such as price and CAC (sent to the validation gate as *hypotheses*, not facts)

## 4. Minimum Setup (`--profile=mvp`)

The smallest profile runs `vision + scope + validate` only. A **one-line product idea** is enough to start; the rest is completed via dialogue.

## 5. Handoff to architect

Once artifacts such as `define-nfr` / `map-domains` / `design-api` exist, they can be handed to `/architect:define-requirements` as input. The architect side auto-detects the product artifacts and confirms/extends them instead of re-eliciting. See the "product → architect handoff" section of [architect-input-requirements.md](architect-input-requirements.md) for details.

## Summary — Fastest Way to Start

| Goal | Entry command | Minimum to prepare |
|------|---------------|--------------------|
| Design product direction from scratch | `/product:start` | A one-line product idea |
| Generate from materials (no dialogue) | `/product:start --auto --input=<materials>` | At least one business document |
