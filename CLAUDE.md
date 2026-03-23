# CLAUDE.md

Guidance for Claude Code in the **nexus-architect** repository.

## What This Is

Unified system architecture agent (36 skills). Covers three workflows:
- **Legacy refactoring**: investigate -> analyze -> evaluate -> redesign -> implement
- **Greenfield design**: requirements -> domain modeling -> ScalarDB design -> infra -> deploy
- **Consulting deliverables**: reports, cost estimates, domain stories

All skills are invoked as `/architect:skill-name`.
Use `/architect:start` for interactive selection or `/architect:pipeline` for automated execution.

## Command Reference

### Orchestration
- `/architect:start [target_path]` — 対話的にシステム分析・設計を開始
- `/architect:pipeline [target_path]` — 自動パイプライン実行（--resume, --skip対応）
- `/architect:init-output [project]` — 出力ディレクトリ初期化

### Investigation & Analysis
- `/architect:investigate [target_path]` — 技術スタック、構造、負債、DDD準備度調査
- `/architect:investigate-security [target_path]` — OWASP Top 10、アクセス制御
- `/architect:analyze [target_path]` — ユビキタス言語、アクター、ドメインマッピング
- `/architect:analyze-data-model [target_path]` — データモデル、DB設計、ER図

### Evaluation
- `/architect:evaluate-mmi [target_path]` — MMI 4軸定性評価
- `/architect:evaluate-ddd [target_path]` — DDD 12基準3レイヤー評価
- `/architect:integrate-evaluations` — MMI+DDD統合、改善計画

### Design
- `/architect:map-domains` — ドメイン分類、BCマッピング
- `/architect:redesign` — 境界コンテキスト再設計
- `/architect:design-microservices` — ターゲットアーキテクチャ
- `/architect:select-scalardb-edition` — ScalarDBエディション選定
- `/architect:design-scalardb` — ScalarDBスキーマ・トランザクション設計
- `/architect:design-scalardb-analytics` — HTAP分析基盤設計
- `/architect:design-data-layer` — 汎用DB設計（非ScalarDB）
- `/architect:design-api` — REST/GraphQL/gRPC/AsyncAPI仕様

### Implementation & Codegen
- `/architect:design-implementation` — 実装仕様
- `/architect:generate-test-specs` — BDD/ユニット/統合テスト仕様
- `/architect:generate-scalardb-code` — Spring Boot + ScalarDBコード生成
- `/architect:generate-infra-code` — K8s/Terraform/Helmコード生成

### Infrastructure
- `/architect:design-infrastructure` — K8s、IaC、マルチ環境
- `/architect:design-security` — 認証・認可、シークレット管理
- `/architect:design-observability` — 監視、トレーシング、アラート
- `/architect:design-disaster-recovery` — RTO/RPO、バックアップ、DR

### Review (5-perspective parallel)
- `/architect:review-consistency` — 構造的一貫性 (CON-)
- `/architect:review-scalardb` — ScalarDB制約 (SDB-)
- `/architect:review-data-integrity` — データ整合性 (DIN-, 非ScalarDB)
- `/architect:review-operations` — 運用準備 (OPS-)
- `/architect:review-risk` — 分散システムリスク (RSK-)
- `/architect:review-business` — ビジネス要件 (BIZ-)
- `/architect:review-synthesizer` — 統合・品質ゲート判定

### Reporting
- `/architect:report` — Markdown → HTML統合レポート
- `/architect:render-mermaid [target_path]` — Mermaid → PNG/SVG + 構文修正
- `/architect:estimate-cost` — インフラ・ライセンス・運用コスト

## Pipeline Dependencies

```
investigate -> analyze -> [evaluate-mmi, evaluate-ddd] -> integrate-evaluations
  -> redesign -> design-microservices -> [design-scalardb, design-api]
  -> implementation -> review -> report
```

Dependency manifest: @.claude/skills/common/skill-dependencies.yaml

## Output Conventions

All outputs are git-ignored:

```
reports/                    # Analysis and design documents
generated/                  # Generated code per service
work/                       # Pipeline state, intermediate files
```

Naming and frontmatter rules: @.claude/rules/output-conventions.md

## Model Assignment

| Model | Use For | Examples |
|-------|---------|----------|
| **opus** | Architecture decisions, tradeoff analysis, risk | review-risk, redesign, design-microservices |
| **sonnet** | Standard analysis, document generation, reviews | analyze, review-consistency, report |
| **haiku** | Template generation, status checks, simple transforms | init-output, render-mermaid |

## Tool Priority

1. **Serena MCP** (get_symbols_overview, find_symbol) -- structural understanding
2. **Glob/Grep** -- file discovery and pattern search
3. **Read** -- targeted file reading
4. **Task (sub-agent)** -- large-scale exploration across many files

## Rules & References

| Resource | Location | When to Read |
|----------|----------|--------------|
| ScalarDB coding patterns | @.claude/rules/scalardb-coding-patterns.md | Generating ScalarDB code |
| ScalarDB edition profiles | @.claude/rules/scalardb-edition-profiles.md | Edition selection |
| Evaluation frameworks | @.claude/rules/evaluation-frameworks.md | MMI/DDD scoring |
| Mermaid best practices | @.claude/rules/mermaid-best-practices.md | Creating diagrams |
| Spring Boot integration | @.claude/rules/spring-boot-integration.md | Java code generation |
| Output structure contract | @.claude/templates/output-structure.md | File dependencies |
| Sub-agent patterns | @.claude/skills/common/sub-agent-patterns.md | Spawning sub-agents |

## Conventions

- **Language**: All output documents in Japanese
- **File naming**: kebab-case for all generated files
- **Frontmatter**: Every output file must include YAML frontmatter with `schema_version`
- **Diagrams**: All diagrams use Mermaid syntax (validated by hook)
- **Immediate output**: Each skill step writes its output file upon completion
- **ScalarDB-optional**: When ScalarDB is not used, ScalarDB-specific skills are skipped and review-data-integrity replaces review-scalardb
