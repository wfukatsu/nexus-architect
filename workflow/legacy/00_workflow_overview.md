# Legacy Refactoring Workflow

## Overview

Analyze and evaluate an existing system, then formulate a migration design toward a microservices architecture.

## Phases

```
Phase 0: Investigation
  /architect:investigate → Tech stack, structure, debt, DDD readiness
  /architect:investigate-security → Security posture assessment (optional)

Phase 1: Analysis
  /architect:analyze → Ubiquitous language, actors, domain mapping
  /architect:analyze-data-model → Data model, ER diagrams (optional)

Phase 2: Evaluation
  /architect:evaluate-mmi + /architect:evaluate-ddd → Run in parallel
  /architect:integrate-evaluations → Integrated evaluation, improvement plan

Phase 3: Design
  /architect:map-domains → Domain classification
  /architect:redesign → Bounded context redesign
  /architect:design-microservices → Target architecture
  /architect:select-scalardb-edition → Edition selection (when using ScalarDB)
  /architect:design-scalardb | /architect:design-data-layer → Data layer design
  /architect:design-api → API specifications

Phase 4: Implementation Design
  /architect:design-implementation → Implementation specifications
  /architect:generate-test-specs → Test specifications
  /architect:generate-scalardb-code → Code generation (when using ScalarDB)

Phase 5: Infrastructure
  /architect:design-infrastructure → Infrastructure configuration
  /architect:design-security → Security design
  /architect:design-observability → Observability design
  /architect:design-disaster-recovery → DR design

Phase 6: Review
  5-perspective parallel review → /architect:review-synthesizer → Quality gate

Phase 7: Report
  /architect:report → Consolidated HTML report
  /architect:estimate-cost → Cost estimation
```

## Dependencies

Each phase assumes completion of the previous phase, although some skills are optional (can be skipped).
See `skill-dependencies.yaml` for details.
