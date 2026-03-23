---
name: design-security
description: |
  Design authentication, authorization, secrets management, and network security.
  Invoked via /design-security.
model: sonnet
user_invocable: true
---

# Security Design

## Desired Outcome

- Authentication infrastructure design (OAuth2/OIDC, inter-service mTLS)
- Authorization model (RBAC/ABAC, policy engine)
- Secrets management (Vault/KMS, rotation strategy)
- Network security (zero trust, segmentation)
- Audit log design (who, what, when)
- Compliance checklist

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `reports/08_infrastructure/security-design.md` | Overall security design |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:investigate-security | Input source (vulnerability information from existing systems) |
| /architect:design-infrastructure | Related |
