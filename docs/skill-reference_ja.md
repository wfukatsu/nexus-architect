# Nexus Architect スキルリファレンス

スキルはプラグインの名前空間で呼び出します：`/product:skill-name`（プロダクトの方向性）、
`/architect:skill-name`（システムアーキテクチャ）、`/scalardb:skill-name`（ScalarDB 開発）。
本書では architect スキルを最初にまとめ、続いて ScalarDB 開発、データベース移行、
プロダクトの方向性の順に掲載します。

## オーケストレーション

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:start` | sonnet | インタラクティブにシステム分析と設計を開始 |
| `/architect:pipeline` | sonnet | 自動パイプライン実行（--resume-from、--rerun-from、--skip-{phase}、--no-scalardb、--lang） |

## 要件定義

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:define-requirements` | opus | 要件定義: FR/NFR 分類、データ・トランザクション要件、ScalarDB 適用判定（greenfield パスの起点。--input、--auto、--no-scalardb をサポート） |

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
| `/architect:create-domain-story` | opus | オプション | ドメインストーリーテリング: ドメインごとの業務プロセスを可視化 |
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
| `/architect:review-report` | sonnet | 生成された HTML レポートの品質レビュー（完全性、スコア精度、Mermaid 構文） |
| `/architect:render-mermaid` | haiku | Mermaid から PNG/SVG + 構文修正 |
| `/architect:estimate-cost` | sonnet | インフラ、ライセンス、運用コスト |

## ユーティリティ

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:init-output` | haiku | 出力ディレクトリの初期化 |

## ScalarDB開発

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/scalardb:model` | sonnet | インタラクティブスキーマ設計ウィザード（キー、インデックス、データ型） |
| `/scalardb:config` | sonnet | 設定ファイルジェネレーター（6つのインターフェース組み合わせ） |
| `/scalardb:scaffold` | sonnet | 完全なスタータープロジェクトジェネレーター |
| `/scalardb:error-handler` | sonnet | 例外処理コードジェネレーターおよびコードレビューア |
| `/scalardb:crud-ops` | sonnet | CRUD API操作パターンガイド |
| `/scalardb:jdbc-ops` | sonnet | JDBC/SQL操作パターンガイド |
| `/scalardb:local-env` | sonnet | Docker Composeローカル環境セットアップ |
| `/scalardb:docs` | sonnet | ScalarDBドキュメント検索 |
| `/scalardb:build-app` | opus | ドメイン要件から完全なアプリケーションを構築 |
| `/scalardb:review-code` | sonnet | Javaコードレビュー（16のチェックカテゴリ） |
| `/scalardb:migrate` | sonnet | 移行アドバイザー（Core/Cluster、CRUD/JDBC、1PC/2PC） |

詳細な使い方は [ScalarDB開発ガイド](scalardb-development.md) を参照してください。

## データベース移行

| コマンド | モデル | データベース | 説明 |
|---------|-------|------------|------|
| `/architect:migrate-database` | sonnet | すべて | 統合移行ルーター（DBタイプを自動検出） |
| `/architect:migrate-oracle` | sonnet | Oracle | フルパイプライン：スキーマ抽出、分析、AQ統合、SP/トリガー変換 |
| `/architect:migrate-mysql` | sonnet | MySQL | フルパイプライン：スキーマ抽出、分析、SP/トリガー変換 |
| `/architect:migrate-postgresql` | sonnet | PostgreSQL | フルパイプライン：スキーマ抽出、分析、PL/pgSQL変換 |

詳細な使い方は [データベース移行ガイド](database-migration.md) を参照してください。

## プロダクトの方向性

すべてのスキルは `/product:skill-name` として呼び出します。プロダクトのビジョンから
SLA/非機能要件までを導出する検証駆動パイプラインで、システム実装設計へは
`/architect:define-requirements` へ handoff します。フェーズ順と
`mvp`/`core-only`/`ux-to-spec`/`full` プロファイルは
`skills/product/common/skill-dependencies.yaml` に定義されています。

| コマンド | モデル | フェーズ | 説明 |
|---------|-------|---------|------|
| `/product:start` | sonnet | オーケストレーション | プロダクト方向性設計を対話的に開始。依存順でパイプラインを実行し、最もリスクの高い前提でゲートする。UI モックの後に選択式の `generate-frontend` ステップ（React + Storybook 生成）を提示する（`--auto`、`--profile`、`--frontend`/`--no-frontend`、`--lang`） |
| `/product:init-output` | sonnet | オーケストレーション | プロダクト出力ツリー、`work/pipeline-progress.json`、`work/traceability.json` を初期化 |
| `/product:define-vision` | opus | 1. プロダクトコア | プロダクトコア（Vision/Mission/Values）を Product Vision Board と PR-FAQ として定義 |
| `/product:name-product` | opus | 1. プロダクトコア | プロダクトをアクロニムとして命名 — 各文字が英単語の頭文字になる短く発音可能なアルファベット名を作り、名前自体が Vision/ポジショニングに根ざした価値フレーズに展開される。候補を絞り込み 1 案を推奨（任意・`full` に含む） |
| `/product:define-success-metrics` | opus | 1. プロダクトコア | 1 つの North Star Metric と 3〜5 個の入力指標 |
| `/product:research-landscape` | opus | 1. プロダクトコア | 市場・競合リサーチ：市場規模（TAM/SAM/SOM）、トレンド、Kano 分類 |
| `/product:design-revenue` | opus | 1. プロダクトコア | 収益・ビジネスモデルと再計算可能な便益評価テンプレート |
| `/product:define-scope` | sonnet | 1. プロダクトコア | 制約を正規化しプロダクトスコープ（対象/対象外）を決定 |
| `/product:validate-assumptions` | opus | ゲート | 最もリスクの高い前提を抽出し、最も安価な検証と Go/No-Go を付与（再実行可能） |
| `/product:generate-persona` | opus | 2. UX 基盤 | Jobs-to-be-Done に紐づくペルソナ（ジョブストーリー + ペルソナカード） |
| `/product:map-journey` | sonnet | 2. UX 基盤 | カスタマージャーニーをステージ × レイヤーのグリッドで作成（接点、行動、感情） |
| `/product:design-positioning` | opus | 2. UX 基盤 | ポジショニング（Dunford 5 要素キャンバス）、接点 × デバイス × タイミングのマトリクス |
| `/product:create-domain-story` | opus | 2. UX 基盤 | ペルソナ起点のドメインストーリーテリング（アクター=ペルソナ、活動=ジャーニー順のジョブストーリー）。UI モックが描画する軸（オプション） |
| `/product:design-system` | opus | 2. UX 基盤 | 独立管理のデザインシステムを構築または `--import`（DTCG トークン + コンポーネント + ガイドライン）。UI モックのスタイルを規定（オプション、単独実行可） |
| `/product:generate-ui-mock` | sonnet | 3. UX → 仕様 | ドメインストーリーに駆動され、デザインシステムでスタイルされた主要画面のナビゲート可能な UI モック（各活動 → 1 画面、ストーリー順のクリック可能なフローとして連結） |
| `/product:define-features` | sonnet | 3. UX → 仕様 | UI モックからフィーチャーを抽出（各画面アクション → Command/フィーチャー） |
| `/product:define-data-model` | opus | 3. UX → 仕様 | UI モックとフィーチャーからデータモデルを 2 パスで導出（明示 → 暗黙） |
| `/product:generate-frontend` | sonnet | 3. UX → 仕様 | UI モック + デザインシステムから実行可能な React + Storybook フロントエンドを生成（Atomic Design、トークンスタイリング、react-router）— 選択式、spec フェーズ末尾 |
| `/product:map-domains` | opus | 4. ドメイン & API | フィーチャー/エンティティを境界づけられたコンテキストへ抽象化（DDD 戦略的設計） |
| `/product:design-api` | opus | 4. ドメイン & API | 論理 API を 3 つの API-Led レイヤーで設計（System/Process/Experience） |
| `/product:design-sla` | sonnet | 5. 品質 & 非機能 | サービスごとの SLI/SLO/SLA とエラーバジェット |
| `/product:define-nfr` | sonnet | 5. 品質 & 非機能 | SLO を測定可能な非機能要件へ変換（可用性、レイテンシ p95/p99 など） |
| `/product:design-architecture` | opus | 4/5. 統合 | 全体アーキテクチャ図（構成/クリティカルパス/デプロイ）＋ 技術適合度評価（Kong / ScalarDB / ScalarDB Analytics / ScalarDL）と採用/条件付/不採用の根拠 |
| `/product:review` | opus | R. レビュー & レポート | プロダクト成果物をレビュー（整合性、トレーサビリティ、拡張性、戦略） |
| `/product:report` | sonnet | R. レビュー & レポート | 成果物を 1 つの自己完結型 HTML レポートに統合（冒頭に検証ステータス） |
| `/product:adapt-change` | opus | 6. 適応 | 再伝播エンジン：変化から影響範囲を算定し、影響を受けるスキルのみ再実行 |
