---
status: complete
priority: p2
issue_id: "011"
tags: [code-review, documentation, security, architecture, graphql]
dependencies: ["010"]
---

# Preserve decision and security evidence in the generated report

## Problem Statement

The generated `api-style-decisions.md` is presented as the human-readable projection of the
canonical decision, but its table omits most evidence needed to review the decision. A reviewer can
see that native exposure was approved without seeing the rationale, rejected alternatives,
security model, control evidence, consumers, operations, or traced requirements.

## Findings

- `tools/lib/api_style_decisions.py:146` renders only eight summary values.
- The canonical fields `security_model`, `control_evidence`, `rationale`, `rejected_alternatives`,
  `consumers`, `operations`, `operational_readiness`, and `requirement_ids` are not rendered.
- `skills/design-api/SKILL.md` still describes the Markdown as the human-readable projection used
  to communicate the decision.
- The source hash proves which JSON produced the report but does not make omitted evidence visible.

## Proposed Solutions

### Option 1: Add per-surface evidence sections

Keep the compact summary table and render a deterministic detail section per `surface_id` containing
consumers, operations, rationale, rejected alternatives, security/control evidence, readiness, and
requirement IDs.

**Pros:** Readable summary plus complete review evidence; straightforward localization.

**Cons:** Longer reports.

**Effort:** Medium

**Risk:** Low

### Option 2: Label Markdown as summary only

Rename/redefine the output as a non-authoritative summary and require reviewers to inspect JSON.

**Pros:** Minimal renderer.

**Cons:** Poor human review experience and raw JSON remains the only complete view.

**Effort:** Small

**Risk:** Medium

## Recommended Action

Use Option 1. Escape Markdown control characters consistently and keep the canonical hash in
frontmatter.

## Technical Details

Affected files: `tools/lib/api_style_decisions.py`, localization strings, renderer fixtures, and
`skills/design-api/SKILL.md`.

## Acceptance Criteria

- [x] Every contract-bearing canonical field is visible in the Markdown projection.
- [x] Native exposure approval is displayed with its five control-evidence references.
- [x] Rationale, rejected alternatives, consumers, operations, readiness, and requirement IDs are visible.
- [x] English and Japanese output pass frontmatter and Mermaid hooks.
- [x] Markdown metacharacters and multiline values cannot corrupt report structure.

## Work Log

### 2026-08-10 - Review finding recorded

**By:** Codex

**Actions:** Compared the canonical field inventory with the eight values emitted by the renderer.

**Learnings:** A deterministic projection can still be incomplete; provenance and reviewability are
separate properties.

### 2026-08-10 - Resolved

**By:** Codex

**Actions:** Kept the compact summary and added deterministic per-surface evidence tables containing
all canonical fields. Escaped HTML, pipes, backticks, CR/LF, arrays, and mappings.

**Verification:** English and Japanese generated reports passed frontmatter and Mermaid hooks;
hostile-value fixtures passed.

## Resources

- Review target: `a57f666`
- `tools/lib/api_style_decisions.py:146`
