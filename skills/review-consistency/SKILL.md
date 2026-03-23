---
name: review-consistency
description: |
  Review design documents for structural coherence, traceability, and terminology consistency.
  Used as one perspective within the parallel review system.
model: sonnet
user_invocable: true
---

# Consistency Review

## Expected Outcome

Verify the structural consistency of design documents and output findings in JSON format.

## Review Dimensions

### 1. Structural Coherence (weight: 0.35)
- Consistency of structure and heading levels across documents
- Detection of orphaned sections and broken references
- Logical soundness of the hierarchical structure

### 2. Traceability (weight: 0.35)
- Ability to trace from requirements to design to implementation
- Presence of forward and backward references
- Whether gaps are documented

### 3. Terminology Consistency (weight: 0.30)
- Consistent use of ubiquitous language
- Detection of different names for the same concept
- Abbreviations defined at first occurrence and used consistently

## Scoring

Each dimension scored 1-5 (5: Exemplary, 4: Good, 3: Acceptable, 2: Concerning, 1: Critical)

## Output Format

```json
{
  "perspective": "consistency",
  "reviewer": "review-consistency",
  "timestamp": "ISO-8601",
  "dimensions": [
    {
      "name": "Structural Coherence",
      "weight": 0.35,
      "score": 4,
      "findings": [
        {
          "id": "CON-001",
          "severity": "critical|major|minor|info",
          "location": "file:section",
          "title": "Finding title",
          "description": "Description of the issue and its impact",
          "recommendation": "Specific remediation proposal"
        }
      ]
    }
  ],
  "weighted_score": 3.8,
  "summary": "Review summary"
}
```

Finding ID prefix: **CON-**
