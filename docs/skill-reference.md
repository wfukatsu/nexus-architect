# Nexus Architect スキルリファレンス

## Orchestration

| スキル | モデル | 説明 |
|-------|--------|------|
| `/workflow` | sonnet | 対話的ワークフロー選択・実行 |
| `/full-pipeline` | sonnet | 自動パイプライン実行（--resume, --skip対応） |

## Investigation

| スキル | モデル | 説明 |
|-------|--------|------|
| `/investigate-system` | sonnet | 技術スタック、構造、負債、DDD準備度調査 |
| `/security-analysis` | sonnet | OWASP Top 10、アクセス制御評価 |

## Analysis

| スキル | モデル | 説明 |
|-------|--------|------|
| `/analyze-system` | opus | ユビキタス言語、アクター、ドメインマッピング |
| `/analyze-data-model` | sonnet | データモデル、DB設計、ER図 |

## Evaluation

| スキル | モデル | 説明 |
|-------|--------|------|
| `/evaluate-mmi` | sonnet | MMI 4軸定性評価 |
| `/evaluate-ddd` | sonnet | DDD 12基準3レイヤー評価 |
| `/integrate-evaluations` | sonnet | MMI+DDD統合、改善計画 |

## Design

| スキル | モデル | 条件 | 説明 |
|-------|--------|------|------|
| `/map-domains` | opus | - | ドメイン分類、BC マッピング |
| `/ddd-redesign` | opus | - | 境界コンテキスト再設計 |
| `/design-microservices` | opus | - | ターゲットアーキテクチャ |
| `/select-scalardb-edition` | sonnet | ScalarDB | エディション選定 |
| `/design-scalardb` | opus | ScalarDB | スキーマ、トランザクション設計 |
| `/design-scalardb-analytics` | sonnet | Premium | HTAP分析基盤設計 |
| `/design-data-layer` | opus | 非ScalarDB | 汎用DB設計 |
| `/design-api` | opus | - | REST/GraphQL/gRPC/AsyncAPI |

## Implementation

| スキル | モデル | 説明 |
|-------|--------|------|
| `/design-implementation` | opus | 実装仕様（サービス、リポジトリ、VO） |
| `/generate-test-specs` | sonnet | BDD/ユニット/統合テスト仕様 |
| `/generate-scalardb-code` | opus | Spring Boot + ScalarDB コード生成 |
| `/generate-infra-code` | sonnet | K8s/Terraform/Helm コード生成 |

## Review

| スキル | モデル | IDプレフィックス | 説明 |
|-------|--------|----------------|------|
| `/review-consistency` | sonnet | CON- | 構造的一貫性 |
| `/review-scalardb` | sonnet | SDB- | ScalarDB制約 |
| `/review-data-integrity` | sonnet | DIN- | データ整合性（非ScalarDB） |
| `/review-operations` | sonnet | OPS- | 運用準備 |
| `/review-risk` | opus | RSK- | 分散システムリスク |
| `/review-business` | sonnet | BIZ- | ビジネス要件 |
| `/review-synthesizer` | sonnet | SYN- | 統合・品質ゲート判定 |

## Infrastructure

| スキル | モデル | 説明 |
|-------|--------|------|
| `/design-infrastructure` | opus | K8s、IaC、マルチ環境 |
| `/design-security` | sonnet | 認証・認可、シークレット管理 |
| `/design-observability` | sonnet | 監視、トレーシング、アラート |
| `/design-disaster-recovery` | sonnet | RTO/RPO、バックアップ、DR |

## Reporting

| スキル | モデル | 説明 |
|-------|--------|------|
| `/compile-report` | haiku | Markdown → HTML統合レポート |
| `/render-mermaid` | haiku | Mermaid → PNG/SVG + 構文修正 |
| `/estimate-cost` | sonnet | インフラ・ライセンス・運用コスト |

## Utility

| スキル | モデル | 説明 |
|-------|--------|------|
| `/init-output` | haiku | 出力ディレクトリ初期化 |
