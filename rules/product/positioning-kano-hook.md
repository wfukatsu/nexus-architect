# Rules: Positioning, Kano & Hook (research-landscape, design-positioning)

Reference for competitive analysis and differentiation. `research-landscape` uses the
**Competitive matrix**, **PoD / PoP**, and **Kano** sections to recommend a differentiation
strategy; `design-positioning` additionally uses the **Positioning statement** and **Hook model**.

## Competitive matrix

List direct competitors, indirect competitors, and the status-quo alternative (incl. "do nothing"
/ spreadsheet). Compare on the dimensions that matter to the target segment (capability, price,
segment focus, channel). Cite each competitor by name + URL. The goal is to find white space, not
a feature checklist.

## Points of Difference (PoD) vs Points of Parity (PoP)

- **PoP (points of parity)** — table-stakes attributes you must match to be considered. Meeting them
  *removes a reason not to buy*; exceeding them rarely wins. **Do not over-invest here.**
- **PoD (points of difference)** — attributes where you are meaningfully better/different and that the segment
  values. This is where investment compounds into preference.

Strategy: reach parity on PoP efficiently, concentrate resources on a few defensible PoDs.

## Kano model

Classify candidate attributes:

- **Must-be (basic)** — absence causes dissatisfaction; presence is neutral → these are **PoP**.
- **Performance (one-dimensional)** — satisfaction scales linearly with how well you do it.
- **Delighter (attractive)** — unexpected value; presence delights, absence is forgiven → these are
  **PoD**.

Delighters decay into expectations over time (today's delighter is tomorrow's must-be), so
recommend continuous refresh of the differentiation set rather than a one-off list.

## Positioning statement (Moore template) — quick form

> For **[target segment]** who **[need/opportunity]**, **[product]** is a **[category]** that
> **[key benefit / reason to believe]**. Unlike **[primary alternative]**, our product
> **[primary differentiation = the PoD]**.

## Positioning canvas (April Dunford) — 5 components

Use for `design-positioning`. Positioning is *deliberate*, derived in this order:

1. **Competitive alternatives** — what customers would do if you didn't exist (incl. status quo).
2. **Unique attributes** — capabilities you have that the alternatives lack.
3. **Value (and proof)** — the customer **outcome** those attributes enable. Claim the *value*,
   not the feature.
4. **Target segment / characteristics** — who cares most about that value (best-fit customers).
5. **Market category** — the frame of reference that makes the value obvious to that segment.

Claim **value (customer outcomes)**, never feature lists; do not fight on points of parity.

## Engagement & retention design (Fogg + Hook)

For the motivation/retention layer of `design-positioning`:

- **Fogg Behavior Model**: Behavior = **Motivation × Ability × Prompt**, all present at once. Use
  for the *activation/motivation* step — lower required ability (reduce friction) and place a clear
  prompt at the right moment.
- **Hook model (Nir Eyal)**: Trigger → Action → Variable Reward → **Investment**. Use for
  *retention* — the investment step should accumulate switching cost (data, content, network) so
  the loop compounds. Each loop must move an `NSM-` retention/engagement input metric.
- **Avoid dark patterns.** Engagement is earned through value, not coercion or deceptive UX.

## Touchpoint × device × timing matrix

Take the opportunities/touchpoints from `journey-maps.md` and, per touchpoint, assign the **device**
(mobile/desktop/in-product/email…) and the **timing** (which journey stage / moment) for the
intended message. This connects positioning to where and when it is actually delivered.

## ID convention

Positioning claims and chosen PoDs get `POS-xxx`; append to `work/traceability.json` with Upstream
`VIS-`/`NSM-` references. Competitive facts in `market-landscape.md` cite sources inline.

## Sources

- Kotler/Keller — Points of Difference / Points of Parity
- Noriaki Kano — Kano model of customer satisfaction
- Geoffrey Moore — "Crossing the Chasm" positioning template
- Nir Eyal — "Hooked" (Hook model)
