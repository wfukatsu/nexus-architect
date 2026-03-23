---
name: review-business
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

## Output Format

JSON (same schema as review-consistency). Finding ID prefix: **BIZ-**
