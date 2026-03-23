# 出力構造とファイル依存関係

## ディレクトリ構造

```
reports/
├── before/{project}/              # investigate-system
│   ├── technology-stack.md
│   ├── codebase-structure.md
│   ├── issues-and-debt.md
│   └── ddd-readiness.md
├── 00_summary/                    # compile-report
│   └── full-report.html
├── 01_analysis/                   # analyze-system, analyze-data-model
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
│   ├── ddd-tactical-evaluation.md
│   ├── integrated-evaluation.md
│   └── unified-improvement-plan.md
├── 03_design/                     # ddd-redesign, design-*, map-domains
│   ├── domain-analysis.md
│   ├── bounded-contexts-redesign.md
│   ├── context-map.md
│   ├── target-architecture.md
│   ├── transformation-plan.md
│   ├── scalardb-schema.md         # ScalarDB有効時のみ
│   ├── scalardb-transaction.md    # ScalarDB有効時のみ
│   ├── scalardb-migration.md      # ScalarDB有効時のみ
│   ├── data-layer-design.md       # ScalarDB無効時のみ
│   ├── api-gateway-design.md
│   └── api-specifications/
│       ├── openapi/
│       ├── graphql/
│       ├── grpc/
│       └── asyncapi/
└── review/                        # review-* agents
    ├── individual/
    │   ├── review-consistency.json
    │   ├── review-scalardb.json
    │   ├── review-operations.json
    │   ├── review-risk.json
    │   └── review-business.json
    ├── review-synthesis.json
    └── review-synthesis.md

generated/                         # codegen skills (Phase B)
└── {service}/
    ├── src/main/java/
    ├── build.gradle
    └── Dockerfile

work/                              # pipeline state
├── pipeline-progress.json
└── context.md
```

## 依存関係フロー

```
investigate-system → analyze-system → analyze-data-model
                            ↓
              [evaluate-mmi, evaluate-ddd] → integrate-evaluations
                                                    ↓
              map-domains → ddd-redesign → design-microservices
                                                    ↓
                            [design-scalardb | design-data-layer, design-api]
                                                    ↓
              [review-consistency, review-scalardb|data-integrity,
               review-operations, review-risk, review-business]
                                                    ↓
                            review-synthesizer → compile-report
```
