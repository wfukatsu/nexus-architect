---
description: |
  Assess an existing system's security posture: OWASP Top 10, access control and zero-trust
  readiness.
argument-hint: '[target_path]'
model: sonnet
---

# Security Analysis

**Usage:** `/architect:investigate-security [target_path]`

Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.

## Desired Outcome

Evaluate the security posture of the target system and report vulnerabilities and areas for improvement:
- OWASP Top 10 compliance status for each item
- Authentication and authorization mechanism assessment
- Access control matrix (from a zero-trust perspective)
- Status of secret management, encryption, and audit logging

## Decision Criteria

- For each OWASP Top 10 item, identify specific compliant/non-compliant locations in the code
- Classify security risks as CRITICAL/HIGH/MEDIUM/LOW
- Distinguish between vulnerabilities requiring immediate action and issues requiring design improvements

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/before/{project}/ | Recommended | /architect:investigate |

## Progress Registry

Before the first step, record `investigate-security` in the project's `work/pipeline-progress.json` as
`in_progress` (`plugin: architect`, `started_at`); at the end, `completed` (or `failed`) with
`outputs` and a one-line `summary` (@skills/common/progress-registry.md § The `in_progress`
Contract). The status dashboard, the token-usage ledger and the audit log read nothing else: a
phase that skips the first write has its spend recorded as `_unassigned` and never shows as
running. A project without the registry (`/architect:init-output` never ran) gets none from this
skill; the hooks are inert there.

## Output

| File | Content |
|------|---------|
| `reports/before/{project}/security-assessment.md` | OWASP assessment, access control, vulnerability list |

Output language and frontmatter: @rules/output-conventions.md.

## Completion

1. Output file has been written
2. Report a summary of findings and any unresolved concerns

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:investigate | Related (can be run in parallel) |
| /architect:review-operations | Referenced during review |
