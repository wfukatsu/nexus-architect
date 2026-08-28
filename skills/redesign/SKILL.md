---
description: |
  Redesign bounded contexts, define aggregates, and generate context maps.
  /architect:redesign to invoke. Requires integrate-evaluations output as a prerequisite.
model: opus
user_invocable: true
---

# DDD Redesign

## Desired Outcome

Based on evaluation results, formulate a new bounded context design:
1. **Bounded Context Redesign** -- Responsibilities of each BC, contained aggregates, public interfaces
2. **Context Map** -- Relationship patterns between BCs (ACL, OHS, Conformist, etc.) as Mermaid diagrams

## Decision Criteria

- Each BC must have a single, clear responsibility
- Minimize dependencies between BCs
- Reflect subdomain classification that invests most in the core domain
- Consider incremental migration paths from the existing system

### Bounded Context Canvas (one per context, in `bounded-contexts-redesign.md`)

Each context is written in the same nine-part shape (after Nick Tune's Bounded Context Canvas),
so product's `bounded-contexts.md` and architect's `bounded-contexts-redesign.md` can be laid side
by side and `review-consistency` can check that a context did not change meaning across the
handoff:

| Part | Content |
|------|---------|
| **Name** | `CTX-` id and the name in the ubiquitous language |
| **Purpose** | One paragraph: what this context is responsible for, and what it is not |
| **Strategic classification** | Core / Supporting / Generic; business model role (revenue, engagement, compliance, cost reduction); evolution stage (genesis / custom / product / commodity) |
| **Domain roles** | The archetypes it plays: specification, execution, analysis, gateway, draft, … |
| **Inbound communication** | Who calls it, with which messages (commands / queries), over which relationship type (Customer/Supplier, Conformist, ACL, OHS/PL, …) |
| **Outbound communication** | Whom it calls or notifies, with which events / requests, and the relationship type |
| **Ubiquitous language** | The five to ten terms that mean something specific here — the ones that would be misread from outside |
| **Business decisions** | The rules and policies this context decides — the `RULE-` entries and invariants it owns |
| **Assumptions and open questions** | What the boundary rests on, and the `OQ-` entries still open about it |

The aggregate list stays a separate section — the Canvas is the context's contract, the aggregate
list is its interior.

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/02_evaluation/unified-improvement-plan.md | Required | /architect:integrate-evaluations |
| reports/01_analysis/ubiquitous-language.md | Recommended | /architect:analyze |
| reports/03_domain/bounded-contexts.md | Optional | /product:map-domains — the product-side Canvas per `CTX-`; keep the `CTX-` id and say what changed when a boundary moves |

## Output

| File | Content |
|------|---------|
| `reports/03_design/bounded-contexts-redesign.md` | One Bounded Context Canvas per BC (above), plus the aggregate list |
| `reports/03_design/context-map.md` | Context map (Mermaid diagram) |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:integrate-evaluations | Input source |
| /architect:design-microservices | Output destination |
| /architect:map-domains | Related |
