# Nexus Architect スキルリファレンス

全スキルは `/architect:skill-name` で呼び出し可能。

## Orchestration

| コマンド | モデル | 説明 |
|---------|--------|------|
| `/architect:start` | sonnet | 対話的にシステム分析・設計を開始 |
| `/architect:pipeline` | sonnet | 自動パイプライン実行（--resume, --skip対応） |

## Investigation

| コマンド | モデル | 説明 |
|---------|--------|------|
| `/architect:investigate` | sonnet | 技術スタック、構造、負債、DDD準備度調査 |
| `/architect:investigate-security` | sonnet | OWASP Top 10、アクセス制御評価 |

## Analysis

| コマンド | モデル | 説明 |
|---------|--------|------|
| `/architect:analyze` | opus | ユビキタス言語、アクター、ドメインマッピング |
| `/architect:analyze-data-model` | sonnet | データモデル、DB設計、ER図 |

## Evaluation

| コマンド | モデル | 説明 |
|---------|--------|------|
| `/architect:evaluate-mmi` | sonnet | MMI 4軸定性評価 |
| `/architect:evaluate-ddd` | sonnet | DDD 12基準3レイヤー評価 |
| `/architect:integrate-evaluations` | sonnet | MMI+DDD統合、改善計画 |

## Design

| コマンド | モデル | 条件 | 説明 |
|---------|--------|------|------|
| `/architect:map-domains` | opus | - | ドメイン分類、BCマッピング |
| `/architect:redesign` | opus | - | 境界コンテキスト再設計 |
| `/architect:design-microservices` | opus | - | ターゲットアーキテクチャ |
| `/architect:select-scalardb-edition` | sonnet | ScalarDB | エディション選定 |
| `/architect:design-scalardb` | opus | ScalarDB | スキーマ、トランザクション設計 |
| `/architect:design-scalardb-analytics` | sonnet | Premium | HTAP分析基盤設計 |
| `/architect:design-data-layer` | opus | 非ScalarDB | 汎用DB設計 |
| `/architect:design-api` | opus | - | REST/GraphQL/gRPC/AsyncAPI |

## Implementation

| コマンド | モデル | 説明 |
|---------|--------|------|
| `/architect:design-implementation` | opus | 実装仕様（サービス、リポジトリ、VO） |
| `/architect:generate-test-specs` | sonnet | BDD/ユニット/統合テスト仕様 |
| `/architect:generate-scalardb-code` | opus | Spring Boot + ScalarDB コード生成 |
| `/architect:generate-infra-code` | sonnet | K8s/Terraform/Helm コード生成 |

## Review

| コマンド | モデル | IDプレフィックス | 説明 |
|---------|--------|----------------|------|
| `/architect:review-consistency` | sonnet | CON- | 構造的一貫性 |
| `/architect:review-scalardb` | sonnet | SDB- | ScalarDB制約 |
| `/architect:review-data-integrity` | sonnet | DIN- | データ整合性（非ScalarDB） |
| `/architect:review-operations` | sonnet | OPS- | 運用準備 |
| `/architect:review-risk` | opus | RSK- | 分散システムリスク |
| `/architect:review-business` | sonnet | BIZ- | ビジネス要件 |
| `/architect:review-synthesizer` | sonnet | SYN- | 統合・品質ゲート判定 |

## Infrastructure

| コマンド | モデル | 説明 |
|---------|--------|------|
| `/architect:design-infrastructure` | opus | K8s、IaC、マルチ環境 |
| `/architect:design-security` | sonnet | 認証・認可、シークレット管理 |
| `/architect:design-observability` | sonnet | 監視、トレーシング、アラート |
| `/architect:design-disaster-recovery` | sonnet | RTO/RPO、バックアップ、DR |

## Reporting

| コマンド | モデル | 説明 |
|---------|--------|------|
| `/architect:report` | haiku | Markdown → HTML統合レポート |
| `/architect:render-mermaid` | haiku | Mermaid → PNG/SVG + 構文修正 |
| `/architect:estimate-cost` | sonnet | インフラ・ライセンス・運用コスト |

## Utility

| コマンド | モデル | 説明 |
|---------|--------|------|
| `/architect:init-output` | haiku | 出力ディレクトリ初期化 |
