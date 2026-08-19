# Infrastructure ADR — Template

Used by `/infra:design`. One file per decision, at `<out>/adr/adr-<NNN>-<slug>.md`.
Write the content in the project's `options.output_language`.

```yaml
---
title: "ADR-<NNN>: <decision title>"
schema_version: 1
phase: "Infrastructure"
skill: infra-design
generated_at: "<ISO8601>"
input_files: []
---
```

---

# ADR-<NNN>: <decision title>

- Status: proposed / accepted / rejected / superseded (by ADR-xx)
- Date:
- Layers involved: L1 / L2 / L3 / L4 / cross-cutting
- Target clouds:
- Target environments: local / test / staging / production (as applicable)

## Context

(Which requirement or constraint forced this decision. State it in numbers.)

## Options

| Option | Benefits | Drawbacks | Multi-cloud consequence | Effect on environment parity |
|--------|----------|-----------|-------------------------|------------------------------|
| A | | | | |
| B | | | | |

## Decision

(The option taken, and the requirement that decided it.)

## Consequences

- Trade-offs accepted:
- Existing design affected:
- Conditions that should trigger revisiting this decision:

## Grounds

- Bundle:
- Official documentation:
