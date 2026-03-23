---
name: investigate-security
description: |
  Evaluate security posture including OWASP Top 10, access control, and zero-trust readiness.
  /architect:investigate-security [target_path] to invoke.
model: sonnet
user_invocable: true
---

# Security Analysis

## Outcome

Evaluate the security posture of the target system and report vulnerabilities and areas for improvement:
- OWASP Top 10 compliance status for each item
- Authentication and authorization mechanism assessment
- Access control matrix (from a zero-trust perspective)
- Status of secret management, encryption, and audit logging

## Judgment Criteria

- For each OWASP Top 10 item, identify specific compliant/non-compliant locations in the code
- Classify security risks as CRITICAL/HIGH/MEDIUM/LOW
- Distinguish between vulnerabilities requiring immediate action and issues requiring design improvements

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/before/{project}/ | Recommended | /architect:investigate |

## Output

| File | Content |
|------|---------|
| `reports/before/{project}/architect:investigate-security.md` | OWASP assessment, access control, vulnerability list |

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Completion

1. Output file has been written
2. Report a summary of findings and any unresolved concerns

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:investigate | Related (can be run in parallel) |
| /architect:review-operations | Referenced during review |
