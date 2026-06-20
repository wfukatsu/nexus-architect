# Rules: Revenue & Market Models (research-landscape, design-revenue)

Reference for market sizing and the revenue/business model. `research-landscape` uses the **Market
sizing** and **Revenue model taxonomy** sections; `design-revenue` uses **Business model canvas**,
**Unit economics**, and **Value hypothesis**.

## Market sizing — TAM / SAM / SOM

- **TAM** (Total Addressable Market) — total demand if you had 100% share.
- **SAM** (Serviceable Available Market) — the slice your product/segment/geography can serve.
- **SOM** (Serviceable Obtainable Market) — the realistic share you can win near-term.

Prefer **bottom-up** sizing (# target customers × price × frequency) over top-down "X% of a big
number". Every figure carries a source (name + URL). Unsourced numbers are not written — they
become `TBD` in Open Questions.

## Revenue model taxonomy

Common patterns: subscription/SaaS, usage/metered, transactional/take-rate, licensing,
freemium → paid, marketplace, advertising, services. Selection criteria: fit to how value is
delivered, customer willingness/ability to pay, sales motion, and margin structure. State *why*
the chosen model fits the value created — not just which one.

## Business model canvas / Lean Canvas (9 blocks)

- **BMC (Osterwalder)**: Customer Segments, Value Propositions, Channels, Customer Relationships,
  Revenue Streams, Key Resources, Key Activities, Key Partners, Cost Structure.
- **Lean Canvas (Maurya)** swaps four blocks for early-stage risk: Problem, Solution, Key Metrics,
  Unfair Advantage (keeps Customer Segments, Value Prop, Channels, Revenue Streams, Cost
  Structure). Prefer Lean Canvas for new/uncertain products.

## Unit economics (set up as a recomputable template, not a verdict)

- **LTV** = ARPA × gross margin × average customer lifetime (or ARPA × margin ÷ churn).
- **CAC** = total sales & marketing spend ÷ new customers acquired.
- **LTV:CAC ≥ 3** is the healthy benchmark; **CAC payback < 12 months** for most SaaS.
- **ROI / NPV** for larger bets (discount future cash flows).

> **Price and CAC are assumptions, not arithmetic.** Record them as `TBD-assumption` and hand them
> to `/product:validate-assumptions` to test in the market (e.g. Van Westendorp, pre-sale) — do not
> present spreadsheet outputs as facts. The template makes the math *recomputable* once real
> evidence arrives.

## Value hypothesis

Frame each business benefit as a falsifiable statement: **"If we ship X, metric Y moves Z% within
T"** — referencing `NSM-` metrics. Pair each with how it will be validated.

## ID convention

Revenue streams and benefit hypotheses get `REV-xxx`; append to `work/traceability.json` with
Upstream `VIS-`/`NSM-` references. Market facts in `market-landscape.md` cite sources inline.

## Sources

- Osterwalder — "Business Model Generation" (Business Model Canvas)
- Ash Maurya — "Running Lean" (Lean Canvas)
- David Skok — "SaaS Metrics 2.0" (LTV:CAC, CAC payback)
