# Rules: Scope & Prioritization (define-scope)

Reference for `/product:define-scope`. Recommended order: Discovery → Kano → RICE → MoSCoW →
In/Out-of-Scope boundary.

## MoSCoW

| Band | Meaning |
|------|---------|
| **Must-have** | Non-negotiable; the product fails without it. Maps to the MVP. |
| **Should-have** | High value but dispensable if the timeline slips. |
| **Could-have** | Nice-to-have polish; first to be cut when time is tight. |
| **Won't-have (now)** | **Explicitly deferred.** Naming exclusions is what stops scope creep. |

Discipline: without strict facilitation, bands drift to opinion. Tie "Must" to the goal — if you
ship everything except this item, does the product still achieve its success metric?

## RICE

```
RICE = (Reach × Impact × Confidence) ÷ Effort
```
- **Reach** — users affected per period (absolute number)
- **Impact** — 3 massive / 2 high / 1 medium / 0.5 low / 0.25 minimal. **Impact must reference a
  success metric (`NSM-`)**, not a feeling. If no metric exists yet, mark the basis `TBD`.
- **Confidence** — 100% high / 80% medium / 50% low
- **Effort** — person-months

## Kano (when classifying emotional value)

Must-be (table stakes) / Performance (linear) / Attractive (delighters) / Indifferent / Reverse.
Prioritize Attractive > Performance > Must-be threshold. Delighters decay into Must-bes over time.

## Constraints intake

Classify each constraint: budget / deadline / technical / legal-regulatory / organizational.
Give each a `CON-` ID. **No scope item may violate a constraint** — if it does, reject or defer it
with an explicit reason.

## In-Scope / Out-of-Scope boundary (mandatory)

Produce an explicit table. The **Out-of-Scope (Won't) list is required** — it is the single most
effective guard against scope creep and the clearest alignment artifact for stakeholders.

## ID convention

Constraints → `CON-`, scope items → `SCP-`, each with an Upstream column (`VIS-`/`NSM-`).
Append all nodes to `work/traceability.json`.

## Sources

- Dai Clegg — MoSCoW (DSDM)
- Intercom — RICE scoring
- Noriaki Kano — Kano model
