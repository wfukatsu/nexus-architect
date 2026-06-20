# Rules: Success Metrics (define-success-metrics)

Reference for `/product:define-success-metrics`. Turn the vision's "definition of winning" into a
single measurable shape that anchors downstream prioritization (RICE Impact, MoSCoW, positioning).

## North Star Metric (NSM)

One metric that captures the core value the product delivers to customers. It must:

1. **Lead revenue, not lag it.** The NSM is a *leading* indicator — improving it should reliably
   pull future revenue/retention up. Revenue itself is a lagging output, never the NSM.
2. **Express customer-received value**, measured in the customer's terms (e.g. "weekly active
   teams that complete a workflow", not "logins").
3. **Be movable by the team** through product work, and trackable on a regular cadence.

Anti-patterns: vanity metrics (raw signups, page views), pure revenue, or anything the team cannot
influence.

## Input metrics (3–5)

The NSM is driven by a small set of input metrics the team acts on directly. A common
decomposition: **breadth × depth × frequency × efficiency** (e.g. # active users × actions per
user × usage frequency × success rate). Each input metric should map to a lever product work can pull.

## Mapping frameworks (use one as a lens)

- **AARRR (Pirate Metrics)** — Acquisition → Activation → Retention → Referral → Revenue. Place
  the NSM and inputs on this funnel to expose which stage the strategy bets on.
- **HEART (Google)** — Happiness, Engagement, Adoption, Retention, Task success. For each chosen
  dimension define Goals → Signals → Metrics. Useful for UX-heavy products.

Pick the framework that fits the product; do not fill both mechanically.

## Targets & guardrails

For each metric record: **definition**, **measurement method/source**, **target value**, and a
**guardrail** (a counter-metric that must not degrade while optimizing the NSM — e.g. don't grow
engagement by harming retention or support load). Targets without a credible source are marked
`TBD` in Open Questions — never invented.

## ID convention

The North Star gets `NSM-001`; each input metric and guardrail gets its own `NSM-xxx` with an
Upstream column referencing the `VIS-` element it serves. Append every `NSM-` node to
`work/traceability.json`. Downstream skills (`define-scope`, `design-revenue`, `define-features`,
`design-positioning`) cite these IDs when tying Impact to a metric.

## Sources

- Sean Ellis / Amplitude — "North Star Metric" framework
- Dave McClure — "AARRR: Startup Metrics for Pirates"
- Google — "HEART framework" (Rodden, Hutchinson, Fu)
