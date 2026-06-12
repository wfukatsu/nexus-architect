# Output Structure and File Dependencies

## Directory Structure

```
reports/
├── 00_requirements/               # define-requirements (greenfield entry; optional on legacy path)
│   ├── requirements-definition.md
│   ├── data-transaction-requirements.md
│   ├── scalardb-applicability.md  # Omitted with --no-scalardb
│   └── open-questions.md
├── before/{project}/              # investigate
│   ├── technology-stack.md
│   ├── codebase-structure.md
│   ├── issues-and-debt.md
│   └── ddd-readiness.md
├── 00_summary/                    # report
│   └── full-report.html
├── 01_analysis/                   # analyze, analyze-data-model
│   ├── system-overview.md
│   ├── ubiquitous-language.md
│   ├── actors-roles-permissions.md
│   ├── domain-code-mapping.md
│   ├── data-model-analysis.md
│   └── er-diagram-current.md
├── 02_evaluation/                 # evaluate-mmi, evaluate-ddd, integrate-evaluations
│   ├── mmi-overview.md
│   ├── mmi-by-module.md
│   ├── ddd-strategic-evaluation.md
│   ├── ddd-tactical-architecture-evaluation.md
│   ├── integrated-evaluation.md
│   └── unified-improvement-plan.md
├── 03_design/                     # redesign, design-*, map-domains
│   ├── domain-analysis.md
│   ├── bounded-contexts-redesign.md
│   ├── context-map.md
│   ├── target-architecture.md
│   ├── transformation-plan.md
│   ├── scalardb-schema.md         # Only when ScalarDB is enabled
│   ├── scalardb-transaction.md    # Only when ScalarDB is enabled
│   ├── scalardb-migration.md      # Only when ScalarDB is enabled
│   ├── data-layer-design.md       # Only when ScalarDB is disabled
│   ├── api-gateway-design.md
│   └── api-specifications/
│       ├── openapi/
│       ├── graphql/
│       ├── grpc/
│       └── asyncapi/
├── 04_stories/                    # create-domain-story (optional)
│   └── domain-story-{domain}.md  # One file per domain
└── review/                        # review-* agents
    ├── individual/
    │   ├── review-consistency.json
    │   ├── review-scalardb.json
    │   ├── review-operations.json
    │   ├── review-risk.json
    │   └── review-business.json
    ├── review-synthesis.json
    ├── review-synthesis.md
    └── report-quality-review.md   # review-report (runs after report)

generated/                         # codegen skills (Phase B)
└── {service}/
    ├── src/main/java/
    ├── build.gradle
    └── Dockerfile

work/                              # pipeline state
├── pipeline-progress.json
└── context.md
```

## Dependency Flow

```
define-requirements (optional; greenfield entry point)
        ↓  (referenced by map-domains, design-scalardb, design-data-layer)
investigate → analyze → analyze-data-model
                            ↓
              [evaluate-mmi, evaluate-ddd] → integrate-evaluations
                                                    ↓
              map-domains → redesign → design-microservices
                                                    ↓
                            [design-scalardb | design-data-layer, design-api]
                                                    ↓
              [review-consistency, review-scalardb|data-integrity,
               review-operations, review-risk, review-business]
                                                    ↓
                            review-synthesizer → report
```
