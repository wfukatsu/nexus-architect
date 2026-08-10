---
status: complete
priority: p1
issue_id: "006"
tags: [code-review, security, graphql, scalardb, validation]
dependencies: []
---

# Close the ScalarDB decision validation bypass

## Problem Statement

The machine-readable security contract fails open when a surface omits or falsifies
`scalardb_backed`. The validator then skips every provider, exposure, approval, release, edition,
and control-evidence check, so an unsafe native GraphQL surface can pass validation.

## Findings

- `tools/lib/api_style_decisions.py:33` treats a missing value as `False` and immediately continues.
- `rules/api-style-selection.md` does not list `scalardb_backed` as a required decision field.
- Existing fixtures set the flag correctly and do not exercise omission, `null`, strings, or a
  native provider paired with `false`.
- A document such as `{"surfaces":[{"surface_id":"public","graphql_provider":"scalardb-native",
  "native_exposure":"external"}]}` currently returns no validation errors.

## Proposed Solutions

### Option 1: Require an explicit typed backend decision

Require `data_backend` or a boolean `scalardb_backed` on every surface, reject missing/non-boolean
values, and reject ScalarDB-native fields when the declared backend is not ScalarDB.

**Pros:** Fail-closed and directly testable; keeps conditional ScalarDB requirements.

**Cons:** Adds one required JSON field to non-ScalarDB surfaces.

**Effort:** Small

**Risk:** Low

### Option 2: Require ScalarDB fields on every surface

Remove the conditional and use `not-applicable` values for non-ScalarDB surfaces.

**Pros:** No security-sensitive discriminator.

**Cons:** Noisier documents and more irrelevant fields.

**Effort:** Small

**Risk:** Low

## Recommended Action

Use Option 1, document the discriminator in the schema, and add negative fixtures for omission,
wrong types, false/native contradictions, and empty documents.

## Technical Details

Affected components: `rules/api-style-selection.md`, `skills/design-api/SKILL.md`,
`tools/lib/api_style_decisions.py`, and `tools/graphql_skills.test.py`.

## Acceptance Criteria

- [x] Every surface declares a typed backend/ScalarDB discriminator.
- [x] Missing, null, and string discriminator values fail validation.
- [x] A native provider cannot pass while declaring a non-ScalarDB backend.
- [x] Existing Spring facade and approved-native fixtures still pass.
- [x] Security review treats a discriminator bypass as critical.

## Work Log

### 2026-08-10 - Review finding recorded

**By:** Codex

**Actions:** Traced the validator's conditional branch and constructed an omission-based bypass.

**Learnings:** A security control must validate its own applicability discriminator or it remains
caller-controlled.

### 2026-08-10 - Resolved

**By:** Codex

**Actions:** Made `scalardb_backed` a required boolean, continued security validation when the
discriminator is invalid, rejected false/native contradictions and empty surface lists, and added
negative fixtures.

**Verification:** `python3 tools/graphql_skills.test.py` passed.

## Resources

- Review target: `24a3325`
- `tools/lib/api_style_decisions.py:33`
