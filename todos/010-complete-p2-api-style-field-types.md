---
status: complete
priority: p2
issue_id: "010"
tags: [code-review, validation, contract, graphql, quality]
dependencies: []
---

# Validate canonical API-style field types and shapes

## Problem Statement

The canonical decision validator checks most base fields only for presence and non-null values.
Structurally invalid values therefore pass and can be interpreted differently by downstream agents
or render as misleading strings.

## Findings

- `tools/lib/api_style_decisions.py:46` checks `field in surface` and `is not None` only.
- Only `selected_style`, `scalardb_backed`, and a subset of ScalarDB fields have type/value checks.
- A fixture using a string for `consumers`, object for `operations`, number for `data_access`, arrays
  for `security_model`/`execution_model`, and string for `requirement_ids` returns no errors.
- The JSON is explicitly described as a machine-readable canonical contract, so permissive coercion
  is not a safe compatibility behavior.

## Proposed Solutions

### Option 1: Define and enforce a field schema

Add one declarative schema for required type, allowed values, and empty-value policy; validate lists
of strings, non-empty decision strings, and structured security/control objects.

**Pros:** Deterministic errors and easier extension; tests can cover the schema systematically.

**Cons:** Requires choosing precise shapes for narrative fields.

**Effort:** Medium

**Risk:** Low

### Option 2: Publish and validate JSON Schema

Ship a JSON Schema and use a standard validator when available.

**Pros:** Portable contract and good tooling support.

**Cons:** Adds a dependency or requires a fallback implementation in plugin environments.

**Effort:** Medium

**Risk:** Medium

## Recommended Action

Use Option 1 without external dependencies, and expose the expected shape in
`api-style-selection.md`. Require non-empty string arrays for consumers, operations, rejected
alternatives where applicable, and requirement IDs; use explicit strings or objects for the
remaining fields.

## Technical Details

Affected files: `tools/lib/api_style_decisions.py`, `rules/api-style-selection.md`, and
`tools/graphql_skills.test.py`.

## Acceptance Criteria

- [x] Every canonical field has an explicit accepted type and empty-value policy.
- [x] Lists, mappings, booleans, and strings cannot be substituted for one another.
- [x] Error messages identify the surface and field.
- [x] A parameterized negative fixture covers every field class.
- [x] Valid Spring, non-ScalarDB, and approved-native decisions still pass.

## Work Log

### 2026-08-10 - Review finding recorded

**By:** Codex

**Actions:** Submitted deliberately wrong JSON types for all base fields; validation returned an
empty error list.

**Learnings:** Presence checks are not schema validation once downstream behavior depends on types.

### 2026-08-10 - Resolved

**By:** Codex

**Actions:** Added stable-ID validation, non-empty string and non-empty string-array schemas,
selected-style enumeration, boolean enforcement, and structured control-evidence validation.

**Verification:** `python3 tools/graphql_skills.test.py` passed all parameterized field fixtures.

## Resources

- Review target: `a57f666`
- `tools/lib/api_style_decisions.py:46`
