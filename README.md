# Nexus Architect

Unified system architecture agent for Claude Code. Covers legacy system refactoring, greenfield ScalarDB design, and consulting deliverable generation.

## Quick Start

```bash
# Interactive workflow (recommended)
/architect:start ./path/to/target

# Automated full pipeline
/architect:pipeline ./path/to/target

# Individual skills
/architect:investigate ./path/to/target
/architect:analyze ./path/to/target
/architect:evaluate-mmi ./path/to/target
```

## Commands

All 36 skills are invoked as `/architect:skill-name`.

| Command | Description |
|---------|-------------|
| **Orchestration** | |
| `/architect:start` | 対話的にシステム分析・設計を開始 |
| `/architect:pipeline` | 自動パイプライン実行（--resume, --skip対応） |
| `/architect:init-output` | 出力ディレクトリ初期化 |
| **Investigation & Analysis** | |
| `/architect:investigate` | 技術スタック、構造、負債、DDD準備度調査 |
| `/architect:investigate-security` | OWASP Top 10、アクセス制御評価 |
| `/architect:analyze` | ユビキタス言語、アクター、ドメインマッピング |
| `/architect:analyze-data-model` | データモデル、DB設計、ER図 |
| **Evaluation** | |
| `/architect:evaluate-mmi` | MMI 4軸定性評価 |
| `/architect:evaluate-ddd` | DDD 12基準3レイヤー評価 |
| `/architect:integrate-evaluations` | MMI+DDD統合、改善計画 |
| **Design** | |
| `/architect:map-domains` | ドメイン分類、BCマッピング |
| `/architect:redesign` | 境界コンテキスト再設計 |
| `/architect:design-microservices` | ターゲットアーキテクチャ |
| `/architect:select-scalardb-edition` | ScalarDBエディション選定 |
| `/architect:design-scalardb` | ScalarDBスキーマ・トランザクション設計 |
| `/architect:design-scalardb-analytics` | HTAP分析基盤設計 |
| `/architect:design-data-layer` | 汎用DB設計（非ScalarDB） |
| `/architect:design-api` | REST/GraphQL/gRPC/AsyncAPI仕様 |
| **Implementation** | |
| `/architect:design-implementation` | 実装仕様 |
| `/architect:generate-test-specs` | BDD/ユニット/統合テスト仕様 |
| `/architect:generate-scalardb-code` | Spring Boot + ScalarDBコード生成 |
| `/architect:generate-infra-code` | K8s/Terraform/Helmコード生成 |
| **Infrastructure** | |
| `/architect:design-infrastructure` | K8s、IaC、マルチ環境 |
| `/architect:design-security` | 認証・認可、シークレット管理 |
| `/architect:design-observability` | 監視、トレーシング、アラート |
| `/architect:design-disaster-recovery` | RTO/RPO、バックアップ、DR |
| **Review** | |
| `/architect:review-consistency` | 構造的一貫性 |
| `/architect:review-scalardb` | ScalarDB制約 |
| `/architect:review-data-integrity` | データ整合性（非ScalarDB） |
| `/architect:review-operations` | 運用準備 |
| `/architect:review-risk` | 分散システムリスク |
| `/architect:review-business` | ビジネス要件 |
| `/architect:review-synthesizer` | 統合・品質ゲート判定 |
| **Reporting** | |
| `/architect:report` | Markdown → HTML統合レポート |
| `/architect:render-mermaid` | Mermaid → PNG/SVG + 構文修正 |
| `/architect:estimate-cost` | インフラ・ライセンス・運用コスト |

## Workflows

### Legacy Refactoring

```
investigate -> analyze -> evaluate -> redesign -> implement -> review -> report
```

### Greenfield Design

```
requirements -> domain modeling -> ScalarDB design -> infra -> deploy
```

## Requirements

- Claude Code CLI (latest)
- Python 3.9+
- Node.js 18+ (optional, for Mermaid rendering)

## Optional MCP Servers

- **Serena**: Advanced code analysis with AST-level understanding
- **Context7**: Latest ScalarDB documentation

## Output Structure

All outputs are written to git-ignored directories:

```
reports/          # Analysis and design documents
generated/        # Generated code per service
work/             # Pipeline state and intermediate files
```

## License

MIT
