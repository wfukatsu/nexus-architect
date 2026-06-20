# Rules: Review & Report (review, report)

Reference for Phase R. `review` applies four lenses to the accumulated artifacts; `report`
consolidates everything into one HTML deliverable that leads with the validation status.

## review — four lenses (apply in order)

1. **Consistency** — missing/broken ID references, contradictions between documents, terminology
   drift (the same concept named differently). Cross-check `VIS-`/`NSM-`/`SCP-`/`FEAT-`/`ENT-`/
   `CTX-`/`API-`/`NFR-` usage across files.
2. **Traceability** — does `work/traceability.json` agree with the documents? Every node should
   have a valid Upstream chain to a `VIS-`/`NSM-` root; flag orphans (no upstream) and dangling
   references (upstream id that doesn't exist).
3. **Extensibility** — will the domain boundaries and API layering absorb likely future
   features? Flag boundaries drawn around current screens, System APIs exposed to UI, low reuse
   (1 Process → 1 Experience), and over-engineered Generic subdomains.
4. **Strategy (product lens)** — is the Vision consistent with the chosen scope? Are the unit
   economics healthy (LTV:CAC, payback)? Is the differentiation durable (delighters decay)? Surface
   goal–work misalignment, not cosmetic issues.

For each finding record: **lens, severity (blocker / major / minor), location (file + ID), and a
concrete fix**. The output is an actionable list, not prose praise.

## report — consolidated HTML

Merge all `reports/**/*.md` into `report/full-report.html` (render Mermaid diagrams inline).

**Mandatory: lead with "Key Assumptions & Validation Status"** at the very top — before any design
content. It aggregates:

- the gate verdict from `work/pipeline-progress.json` → `gates.validate-assumptions` (go / no-go)
- untested / open assumptions (`ASM-` with no passing test) and their kill/pivot thresholds
- every `TBD` and `TBD-assumption` across the artifacts
- the Open Questions collected in `work/context.md`

This keeps the reader honest about what is decided vs. still a bet. Follow with a section per phase
in pipeline order, each linking back to its source file. Keep it self-contained (inline CSS), no
external assets beyond the Mermaid runtime.

## Discipline

- **Never fabricate a "pass".** If an artifact is missing or a verdict is `no-go`, the report says so
  prominently.
- `review` is **rerunnable mid-pipeline** — it works on whatever exists (min: `map-journey`).

## Sources

- Google SRE / DDD context-mapping (extensibility lens)
- Amazon Working Backwards — assumptions-first framing (report header)
