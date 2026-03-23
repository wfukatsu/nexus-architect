# Nexus Architect スキルリファレンス

すべてのスキルは `/architect:skill-name` として呼び出します。

## オーケストレーション

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:start` | sonnet | インタラクティブにシステム分析と設計を開始 |
| `/architect:pipeline` | sonnet | 自動パイプライン実行（--resume、--skip をサポート） |

## 調査

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:investigate` | sonnet | 技術スタック、構造、技術的負債、DDD準備度調査 |
| `/architect:investigate-security` | sonnet | OWASP Top 10、アクセス制御評価 |

## 分析

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:analyze` | opus | ユビキタス言語、アクター、ドメインマッピング |
| `/architect:analyze-data-model` | sonnet | データモデル、DB設計、ER図 |

## 評価

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:evaluate-mmi` | sonnet | MMI 4軸定性評価 |
| `/architect:evaluate-ddd` | sonnet | DDD 12基準3層評価 |
| `/architect:integrate-evaluations` | sonnet | MMI+DDD統合、改善計画 |

## 設計

| コマンド | モデル | 条件 | 説明 |
|---------|-------|------|------|
| `/architect:map-domains` | opus | - | ドメイン分類、BC マッピング |
| `/architect:redesign` | opus | - | 境界づけられたコンテキストの再設計 |
| `/architect:design-microservices` | opus | - | ターゲットアーキテクチャ |
| `/architect:select-scalardb-edition` | sonnet | ScalarDB | エディション選択 |
| `/architect:design-scalardb` | opus | ScalarDB | スキーマとトランザクション設計 |
| `/architect:design-scalardb-analytics` | sonnet | Premium | HTAP分析プラットフォーム設計 |
| `/architect:design-data-layer` | opus | ScalarDB以外 | 汎用DB設計 |
| `/architect:design-api` | opus | - | REST/GraphQL/gRPC/AsyncAPI |

## 実装

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:design-implementation` | opus | 実装仕様（サービス、リポジトリ、VO） |
| `/architect:generate-test-specs` | sonnet | BDD/ユニット/統合テスト仕様 |
| `/architect:generate-scalardb-code` | opus | Spring Boot + ScalarDB コード生成 |
| `/architect:generate-infra-code` | sonnet | K8s/Terraform/Helm コード生成 |

## レビュー

| コマンド | モデル | IDプレフィックス | 説明 |
|---------|-------|----------------|------|
| `/architect:review-consistency` | sonnet | CON- | 構造的一貫性 |
| `/architect:review-scalardb` | sonnet | SDB- | ScalarDB制約 |
| `/architect:review-data-integrity` | sonnet | DIN- | データ整合性（ScalarDB以外） |
| `/architect:review-operations` | sonnet | OPS- | 運用準備状況 |
| `/architect:review-risk` | opus | RSK- | 分散システムリスク |
| `/architect:review-business` | sonnet | BIZ- | ビジネス要件 |
| `/architect:review-synthesizer` | sonnet | SYN- | 統合と品質ゲート |

## インフラストラクチャ

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:design-infrastructure` | opus | K8s、IaC、マルチ環境 |
| `/architect:design-security` | sonnet | 認証、認可、シークレット管理 |
| `/architect:design-observability` | sonnet | モニタリング、トレーシング、アラート |
| `/architect:design-disaster-recovery` | sonnet | RTO/RPO、バックアップ、DR |

## レポート

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:report` | haiku | Markdown から HTML への統合レポート |
| `/architect:render-mermaid` | haiku | Mermaid から PNG/SVG + 構文修正 |
| `/architect:estimate-cost` | sonnet | インフラ、ライセンス、運用コスト |

## ユーティリティ

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:init-output` | haiku | 出力ディレクトリの初期化 |

## ScalarDB開発

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:scalardb-model` | sonnet | インタラクティブスキーマ設計ウィザード（キー、インデックス、データ型） |
| `/architect:scalardb-config` | sonnet | 設定ファイルジェネレーター（6つのインターフェース組み合わせ） |
| `/architect:scalardb-scaffold` | sonnet | 完全なスタータープロジェクトジェネレーター |
| `/architect:scalardb-error-handler` | sonnet | 例外処理コードジェネレーターおよびコードレビューア |
| `/architect:scalardb-crud-ops` | sonnet | CRUD API操作パターンガイド |
| `/architect:scalardb-jdbc-ops` | sonnet | JDBC/SQL操作パターンガイド |
| `/architect:scalardb-local-env` | sonnet | Docker Composeローカル環境セットアップ |
| `/architect:scalardb-docs` | sonnet | ScalarDBドキュメント検索 |
| `/architect:scalardb-build-app` | opus | ドメイン要件から完全なアプリケーションを構築 |
| `/architect:scalardb-review-code` | sonnet | Javaコードレビュー（16のチェックカテゴリ） |
| `/architect:scalardb-migrate` | sonnet | 移行アドバイザー（Core/Cluster、CRUD/JDBC、1PC/2PC） |

詳細な使い方は [ScalarDB開発ガイド](scalardb-development.md) を参照してください。

## データベース移行

| コマンド | モデル | データベース | 説明 |
|---------|-------|------------|------|
| `/architect:migrate-database` | sonnet | すべて | 統合移行ルーター（DBタイプを自動検出） |
| `/architect:migrate-oracle` | sonnet | Oracle | フルパイプライン：スキーマ抽出、分析、AQ統合、SP/トリガー変換 |
| `/architect:migrate-mysql` | sonnet | MySQL | フルパイプライン：スキーマ抽出、分析、SP/トリガー変換 |
| `/architect:migrate-postgresql` | sonnet | PostgreSQL | フルパイプライン：スキーマ抽出、分析、PL/pgSQL変換 |

詳細な使い方は [データベース移行ガイド](database-migration.md) を参照してください。
