---
description: |
  Estimate the token usage and USD cost of running the architect pipeline on a codebase.
  /architect:estimate-token-cost [target_path]. Combines an a-priori model (from
  lines-of-code) with measured actuals recorded in work/token-usage.json when present.
model: sonnet
user_invocable: true
---

# Token Cost Estimation

## Desired Outcome

Produce a defensible estimate of the **LLM token cost** of running the architect
pipeline (investigation → analysis → evaluation → design → review → report, plus any
manual-extension-tier skills) against a target codebase and/or design documents.

This is distinct from `/architect:estimate-cost`, which estimates cloud infrastructure,
ScalarDB licensing, and operational costs. This skill estimates the cost of *running the
agent itself*.

## Inputs & Single Source of Truth

- **Pricing**: `@skills/common/references/model-pricing.json` — per-model prices (per 1M
  tokens), cache multipliers, and the a-priori estimation heuristics. Never hardcode
  prices in the report; read them from this file so estimates track pricing updates.
- **Measured actuals (preferred when present)**: `work/token-usage.json`, maintained by
  the `record_token_usage.py` hook during real runs (per-phase, per-model billed tokens
  and USD). Use it to calibrate or replace a-priori numbers.

## Acceptance Criteria

Gather (via AskUserQuestion, or infer from the target when possible):
- **Codebase size** — total lines of code (run `cloc`/`tokei` if available, else
  `find . -name '*.<ext>' | xargs wc -l`), and the size of any design documents.
- **Scope** — core pipeline only, or core + manual-extension tier (security, infra,
  observability, DR, implementation/test specs, code generation, migration).
- **Billing model** — per-token API/Console billing (report USD), or Claude
  subscription (report token consumption and note it draws down usage limits, not USD).
- **Currency** — USD or JPY (if JPY, ask for or assume an FX rate and state it).

## Method

### 1. If `work/token-usage.json` exists — calibrate from actuals
- Read the per-phase `by_model` billed tokens and `cost_usd`.
- If the run is **partial** (only some phases have data), extrapolate the remaining
  phases by scaling completed-phase actuals by the ratio of remaining to completed work
  (use `skill-dependencies.yaml` phase list and the code-heaviness of each phase).
- If the run is **complete**, report actuals directly as the estimate and stop.
- Always state clearly which numbers are measured vs. extrapolated.

### 2. Otherwise — a-priori estimate from lines-of-code
Using `estimation_heuristics` from the pricing file:
1. `raw_code_tokens = LOC × tokens_per_loc` (+ design-doc tokens).
2. `unique_ingested = raw_code_tokens × code_ingestion_ratio` (structural tools/sampling
   cover the rest — the agent does not read every line).
3. `effective_input = unique_ingested × effective_input_multiplier` (cache-adjusted billed
   input across the multi-turn pipeline; prompt-cache reads bill at 0.1×).
4. `output_tokens ≈ output_per_phase_tokens × phase_count`.
5. Price each phase with its `phase_model_tier` and sum. Report `typical`, `low`, and
   `high` bands by sweeping the `low`/`typical`/`high` heuristic values.

**The heuristics are uncalibrated defaults** — until real runs populate
`work/token-usage.json`, present the estimate as a wide band (the high/low spread can be
3×) and say so explicitly in the report. After a few recorded runs, recommend updating
the heuristic values in `model-pricing.json` from observed ratios.

### 3. Present cost drivers and levers
Always include: model mix, cache effectiveness, code-ingestion ratio, and scope (core vs
full). Give concrete reduction levers (staged execution, tier down simple phases to
haiku, narrow `target_path`, keep the prompt prefix stable for cache hits).

## Output

Write the report in the language configured in `work/pipeline-progress.json`
(`options.output_language`), defaulting to `en`.

| File | Content |
|------|---------|
| `reports/05_estimate/token-cost-estimate.md` | Assumptions, per-phase token & cost table (typical/low/high bands), calibration source (a-priori vs measured), cost drivers, and reduction levers |

Frontmatter per `@rules/output-conventions.md`. Show tokens *and* cost; if the billing
model is a subscription, lead with token consumption and mark USD as reference-only.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:estimate-cost | Sibling — infrastructure/license/operational cost (not token cost) |
| /architect:init-output | Creates `work/`, which enables the token-usage recorder |
| /architect:pipeline | The run whose token cost this skill estimates and whose actuals it calibrates against |
