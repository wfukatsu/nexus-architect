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
│   ├── domain-event-catalog.json  # design-aggregate writes; design-microservices completes consumers
│   ├── domain-event-catalog.md    # Projection of the .json — the context map's Published Language
│   ├── aggregates/                # design-aggregate (optional)
│   │   ├── aggregate-{aggregate}.md       # One file per modeled aggregate
│   │   └── aggregate-manifest.json        # Canonical machine-readable model
│   ├── state-machines/            # design-state-machine (optional)
│   │   ├── state-machine-{aggregate}.md   # One file per modeled aggregate
│   │   └── state-machine-manifest.json    # Canonical machine-readable model
│   ├── adr/                       # redesign opens; design-microservices, design-scalardb /
│   │   │                          # design-data-layer, design-api append
│   │   ├── adr-NNN-{slug}.md              # One Architecture Decision Record per decision (ADR-)
│   │   └── index.md                       # View regenerated from the records' frontmatter
│   └── api-specifications/
│       ├── openapi/
│       ├── graphql/
│       ├── grpc/
│       └── asyncapi/
├── 04_stories/                    # create-domain-story (optional)
│   └── domain-story-{domain}.md  # One file per domain
├── 08_infrastructure/             # design-infrastructure, design-security,
│   │                              # design-observability, design-disaster-recovery, /infra:*
│   ├── infrastructure-design.md
│   ├── security-design.md
│   ├── observability-design.md
│   ├── disaster-recovery-design.md
│   ├── infra-design-{system}.md   # /infra:design
│   ├── env-matrix-{system}.md     # /infra:design
│   ├── adr/adr-{NNN}-{slug}.md    # /infra:design
│   └── reviews/                   # /infra:review
│       └── review-{target}-r{n}.md
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

`reports/`, `generated/` and `work/` are all **regenerable pipeline output** and are typically
git-ignored. `generated/` therefore holds only scaffolding that a codegen skill can overwrite on
re-run (`generate-scalardb-code`, `generate-infra-code`, `generate-frontend`).

**Merge-bound code does not go here.** `/architect:implement-backlog` produces deliverables that are
committed, reviewed in a PR/MR and merged, so it writes into the target project's real source tree
(resolved and verified per its Output Location section) — writing it under `generated/` would leave
it git-ignored and break the implement → review → merge chain.

## Dependency Flow

```
define-requirements (optional; greenfield entry point)
        ↓  (referenced by map-domains, design-scalardb, design-data-layer)
investigate → analyze → analyze-data-model
                            ↓
              [evaluate-mmi, evaluate-ddd] → integrate-evaluations
                                                    ↓
              map-domains → redesign → design-microservices
                                ↓                   ↓
              [design-aggregate (optional)] ────────┤
                                ↓                   │
              [design-state-machine (optional)] ────┤
                                                    ↓
                            [design-scalardb | design-data-layer, design-api]
                                                    ↓
              [review-consistency, review-scalardb|data-integrity,
               review-operations, review-risk, review-business]
                                                    ↓
                            review-synthesizer → report
```
