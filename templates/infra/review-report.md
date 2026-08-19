# Infrastructure Review Report — Template

Used by `/infra:review`. Write the content in the project's `options.output_language`.
The Good → findings → environment parity → multi-cloud → conclusion order is deliberate:
a review that is only findings gets read as an attack rather than as an assessment.

```yaml
---
title: "<target> Infrastructure Review (round <n>)"
schema_version: 1
phase: "Infrastructure"
skill: infra-review
generated_at: "<ISO8601>"
input_files:
  - <the files reviewed>
---
```

---

# <target> Infrastructure Review

- Reviewed: (repository / MR / design document, with revision)
- Target clouds:
- Target environments: local / test / staging / production (as applicable)
- Review date:
- Standard: OKF `okf-k8s-tf` (all items of `architecture/design-build-checklist.md`, plus the
  multi-cloud lens)

<!-- Round 2 and later: open with a reconciliation against the previous round's findings —
     resolved / still open / new — before anything else. -->

## Overall assessment

(Three to five lines. What is good, and what is most at risk. Verdict: pass / pass with
conditions / changes required.)

| Severity | Count |
|----------|------:|
| Critical | |
| High | |
| Medium | |
| Low | |
| Info | |

## Good

- (Design decisions worth keeping, with their grounds. A report that is only findings is not a
  review.)

## Findings

### [Critical] <title>

- **Location**: `path/to/file:12`
- **What**:
- **Impact**:
- **Environment**: (note it here when the severity depends on the environment)
- **Fix**:
- **Source**: `foundation/terraform.md`

(Continue in severity order, same shape.)

## Environment parity

| Check | Result | Note |
|-------|--------|------|
| Base / chart / image digest identical across environments | OK / NG / not verified | |
| Differences confined to overlay and values | | |
| Staging ↔ production differences enumerated with reasons | | |
| Re-creation procedure for test's drift | | |
| Promotion per digest, with traceable evidence | | |
| Production apply path, approval and rollback | | |
| Any path by which production data reaches lower environments | | |
| Kyverno failure action per environment | | |
| `environment` label consistency | | |
| What is not reproduced locally, documented | | |
| Failure boundaries per environment (namespace / account / state) | | |

## Multi-cloud

| Check | Result | Note |
|-------|--------|------|
| Cloud branching leaking into L2/L3 | OK / NG / not verified | |
| L1 module output names aligned | | |
| Implicit dependency on AWS-only pieces | | |
| State separated per cloud | | |
| Image digest identity | | |
| Label / attribute names aligned | | |
| Backend as a single point of failure | | |
| Kyverno policy consistency across clouds | | |
| Version skew / EOL verified for all three clouds | | |

## Open questions (cannot be judged from outside)

| # | Item | Who to ask |
|---|------|------------|

## Conclusion

(Priority order for the response, and the next action to take.)
