# Rules: Assumption Validation (validate-assumptions)

Reference for `/product:validate-assumptions`. The core of validation-driven design: turn a
plausible strategy into a set of falsifiable bets, each with the cheapest test and a stop rule.

## Classify every assumption (desirability / viability / feasibility)

- **Desirability** — do customers want it? (the problem is real and ranked high; the solution is
  preferred over alternatives)
- **Viability** — does it make money? (willingness to pay, price, CAC, channel, unit economics)
- **Feasibility** — can we build and operate it? (key technical, data, regulatory risk)

## Rank by collapse impact (Riskiest Assumption Test)

For each assumption ask: "if this is wrong, how much of the strategy falls?" Validate the most
dangerous, highest-uncertainty assumption **first and cheapest** — before the MVP, not after.

## Test catalog (cheapest credible test per assumption)

| Test | Validates | Cost |
|------|-----------|------|
| Customer / switch interview | desirability, JTBD | low |
| Smoke test / fake-door landing page | demand (sign-up / click rate) | low |
| Concierge MVP | desirability + delivery | medium |
| Wizard-of-Oz | desirability without building the backend | medium |
| **Pre-sale / letter of intent** | **viability — the strongest signal** | medium |
| Van Westendorp PSM (4 questions: too expensive / expensive / cheap / too cheap) | acceptable price band | low |

## Kill / pivot threshold (mandatory per top assumption)

Set the threshold **before** running the test. Example: "if the landing-page sign-up rate < 5%,
reject the demand assumption and revisit Phase 1." A test without a pre-committed threshold is not
a validation.

## Price is an assumption, not arithmetic

`LTV:CAC ≥ 3` validates the spreadsheet, not the market. Pull `TBD-assumption` price/CAC values
from vision/scope/revenue and validate them with pre-sale or Van Westendorp, not by computing.

## Go / No-Go verdict

- **No-Go** — any collapse-critical assumption is both untested and lacks a defined test+threshold.
- **Go** — otherwise; list still-open assumptions for tracking.

Write the verdict and `open_assumptions` to `work/pipeline-progress.json` → `gates`. Re-run as
evidence arrives — the gate is meant to be revisited.

## ID convention

Assumptions → `ASM-`, with an Upstream column (`VIS-`/`SCP-`/`NSM-`/revenue). Append all nodes to
`work/traceability.json` so `adapt-change` can re-open the gate on change.

## Sources

- Bland & Osterwalder — "Testing Business Ideas" (Strategyzer)
- Intercom — Riskiest Assumption Test
- Van Westendorp — Price Sensitivity Meter
