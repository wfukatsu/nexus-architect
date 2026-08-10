---
status: complete
priority: p1
issue_id: "007"
tags: [code-review, tooling, portability, graphql, skills]
dependencies: []
---

# Invoke the API-style validator from the plugin root

## Problem Statement

The design and security-review skills invoke `tools/validate-api-style-decisions.py` relative to the
consumer project's working directory. That script belongs to this plugin, not the generated
project, so normal plugin use fails with “file not found” and blocks the API design phase.

## Findings

- `skills/design-api/SKILL.md:135` uses `python3 tools/validate-api-style-decisions.py`.
- `skills/review-api-security/SKILL.md:107` repeats the same relative command.
- Repository conventions use `${CLAUDE_PLUGIN_ROOT}/tools/...` for plugin-owned executables and
  AGENTS.md maps that token to the repository root in Codex.
- Tests import the Python module from this repository and therefore do not exercise invocation from
  a separate consumer project directory.

## Proposed Solutions

### Option 1: Use the plugin-root path

Invoke `python3 ${CLAUDE_PLUGIN_ROOT}/tools/validate-api-style-decisions.py <project-artifact>` in
both skills and add a test that runs it with a temporary external working directory.

**Pros:** Matches existing plugin conventions and works in Claude Code and Codex.

**Cons:** Requires careful quoting if the plugin path contains spaces.

**Effort:** Small

**Risk:** Low

### Option 2: Copy the validator into each project

Make the design skill generate a project-local validator.

**Pros:** Project is self-contained.

**Cons:** Duplicates plugin implementation and creates version drift.

**Effort:** Medium

**Risk:** Medium

## Recommended Action

Use Option 1 and follow the same root-resolution convention as `update-okf-bundle.sh` and the status
tools.

## Technical Details

Affected files: `skills/design-api/SKILL.md`, `skills/review-api-security/SKILL.md`, and the GraphQL
skill tests.

## Acceptance Criteria

- [x] Both skills resolve the validator through `${CLAUDE_PLUGIN_ROOT}`.
- [x] The artifact path remains relative to the consumer project or is passed explicitly.
- [x] A subprocess fixture succeeds from a directory that has no local `tools/` directory.
- [x] Invalid input still returns exit code 1 and malformed/unreadable input returns exit code 2.

## Work Log

### 2026-08-10 - Review finding recorded

**By:** Codex

**Actions:** Compared the new invocation with established plugin-owned tool paths.

**Learnings:** Unit-import success does not prove a plugin executable is addressable from a
consumer workspace.

### 2026-08-10 - Resolved

**By:** Codex

**Actions:** Changed both skill invocations to the quoted plugin-root path and added an external-CWD
subprocess fixture covering success, invalid input, and missing input exit codes.

**Verification:** `python3 tools/graphql_skills.test.py` passed.

## Resources

- Review target: `24a3325`
- `rules/okf-knowledge-bundle.md:20`
