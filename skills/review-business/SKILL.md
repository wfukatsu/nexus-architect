---
description: |
  Review business requirements traceability, NFR quantification, and stakeholder alignment.
  Used as one perspective within the parallel review system.
model: sonnet
user_invocable: true
---

# Business Requirements Review

## Review Dimensions

### 1. Requirements Traceability (weight: 0.35)
- Ability to trace design components back to business requirements
- Detection of design without corresponding requirements (over-engineering)
- Requirements not reflected in the design (gaps)

### 2. NFR Quantification (weight: 0.30)
- Whether non-functional requirements are described with measurable targets
- Whether performance targets are linked to business scenarios
- Whether capacity projections are based on business growth forecasts

### 3. Stakeholder Alignment (weight: 0.20)
- Addressing the concerns of different stakeholders
- Documentation of tradeoff decisions
- Migration plan from a business continuity perspective

### 4. ROI and Feasibility (weight: 0.15)
- Realism of implementation timelines
- Phasing aligned with business priorities
- Identification of quick wins

## Execution

### Step 1: Collect Input File Paths

Glob for all available design and analysis documents:
- `reports/03_design/**/*.md`
- `reports/01_analysis/**/*.md`

Record the full list of found file paths — these will be passed to sub-agents.

### Step 2: Spawn Four Parallel Dimension Reviewers

In a **single message**, issue all four Task() calls simultaneously so they run in parallel:

**Task A — Requirements Traceability (BIZ-1xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Requirements traceability dimension review",
  prompt: """
You are a business analyst reviewing design documents for REQUIREMENTS TRACEABILITY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Requirements Traceability dimension:
- Can each design component be traced back to a stated business requirement?
- Are there design elements with no corresponding requirement (over-engineering)?
- Are there stated requirements not reflected anywhere in the design (gaps)?

Score 1-5: 5=Exemplary (full bidirectional traceability), 4=Good, 3=Acceptable, 2=Concerning, 1=Critical (major untraceable elements)

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Requirements Traceability",
  "weight": 0.35,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "BIZ-1<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<traceability gap and its business risk>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task B — NFR Quantification (BIZ-2xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "NFR quantification dimension review",
  prompt: """
You are a business analyst reviewing design documents for NFR QUANTIFICATION.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the NFR Quantification dimension:
- Are non-functional requirements stated with measurable, testable targets (e.g., p99 latency < 200ms)?
- Are performance targets linked to specific business scenarios (e.g., peak Black Friday load)?
- Are capacity projections grounded in business growth forecasts?

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "NFR Quantification",
  "weight": 0.30,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "BIZ-2<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<unquantified NFR and its validation risk>",
      "recommendation": "<specific measurable target to add>"
    }
  ]
}
"""
)
```

**Task C — Stakeholder Alignment (BIZ-3xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "Stakeholder alignment dimension review",
  prompt: """
You are a business analyst reviewing design documents for STAKEHOLDER ALIGNMENT.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the Stakeholder Alignment dimension:
- Are concerns of different stakeholders (business, ops, security, end-users) addressed?
- Are tradeoff decisions documented with rationale?
- Does the migration plan account for business continuity requirements?

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "Stakeholder Alignment",
  "weight": 0.20,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "BIZ-3<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<alignment gap and its impact>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

**Task D — ROI and Feasibility (BIZ-4xx)**
```
Task(
  subagent_type: "general-purpose",
  description: "ROI and feasibility dimension review",
  prompt: """
You are a business analyst reviewing design documents for ROI AND FEASIBILITY.

Read all of the following files using the Read tool:
<FILE_LIST>
[Insert the full list of file paths found in Step 1, one per line]
</FILE_LIST>

Evaluate ONLY the ROI and Feasibility dimension:
- Are implementation timelines realistic given the scope and team size implied by the design?
- Is the phasing aligned with business priorities (high-value items delivered first)?
- Are quick wins identified that can demonstrate value early?

Score 1-5: 5=Exemplary, 4=Good, 3=Acceptable, 2=Concerning, 1=Critical

Return ONLY this JSON (no markdown fences, no explanation):
{
  "name": "ROI and Feasibility",
  "weight": 0.15,
  "score": <integer 1-5>,
  "findings": [
    {
      "id": "BIZ-4<NN>",
      "severity": "critical|major|minor|info",
      "location": "<file:section>",
      "title": "<finding title>",
      "description": "<feasibility concern and its delivery risk>",
      "recommendation": "<specific remediation>"
    }
  ]
}
"""
)
```

### Step 3: Merge and Write Output

After all four Tasks complete, compute the weighted score and write output:

```
weighted_score = round(0.35 × scoreA + 0.30 × scoreB + 0.20 × scoreC + 0.15 × scoreD, 2)
```

Write `reports/review/individual/review-business.json`:
```json
{
  "perspective": "business",
  "reviewer": "review-business",
  "timestamp": "<ISO-8601 now>",
  "dimensions": [<Task A result>, <Task B result>, <Task C result>, <Task D result>],
  "weighted_score": <computed>,
  "summary": "<2-3 sentences synthesizing business alignment quality and key gaps>"
}
```

## Output Format

Finding ID prefix: **BIZ-**
- BIZ-1xx: Requirements Traceability
- BIZ-2xx: NFR Quantification
- BIZ-3xx: Stakeholder Alignment
- BIZ-4xx: ROI and Feasibility
