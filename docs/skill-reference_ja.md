# Nexus Architect スキルリファレンス

スキルはプラグインの名前空間で呼び出します：`/product:skill-name`（プロダクトの方向性）、
`/architect:skill-name`（システムアーキテクチャ）、`/scalardb:skill-name`（ScalarDB 開発）、
`/infra:skill-name`（マルチクラウド インフラ）。
本書では architect スキルを最初にまとめ、続いて ScalarDB 開発、データベース移行、
マルチクラウド インフラ、プロダクトの方向性の順に掲載します。

各パイプラインの実行前に用意すべきインプットは、
[product インプット要件ガイド](product-input-requirements_ja.md) と
[architect インプット要件ガイド](architect-input-requirements_ja.md) を参照してください。

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
| `/architect:redesign` | opus | - | 境界づけられたコンテキストの再設計・コンテキストマップ・後続の設計スキルが追記する ADR ログ（`reports/03_design/adr/`） |
| `/architect:create-domain-story` | opus | オプション | ドメインストーリーテリング: ドメインごとの業務プロセスを可視化。`--mode=event-storming` でフローを Process Modeling EventStorming として進行 |
| `/architect:design-aggregate` | opus | オプション | 境界づけられたコンテキストごとの戦術モデル: 集約ルート・内部エンティティ・値オブジェクト・具体例付き不変条件・コマンド/イベント/ファクトリ/仕様・ルートごとのリポジトリを、トランザクションが書き込む単位として設計。加えてイベントから導出するドメインイベントカタログ（`reports/03_design/domain-event-catalog.json`） |
| `/architect:design-state-machine` | opus | オプション | アグリゲートごとの状態遷移モデル: 状態・ガード付き遷移・空欄のない状態×イベント行列・各遷移の整合性クラスを対話的に構築 |
| `/architect:design-microservices` | opus | - | ターゲットアーキテクチャ |
| `/architect:select-scalardb-edition` | sonnet | ScalarDB | エディション選択 |
| `/architect:design-scalardb` | opus | ScalarDB | スキーマとトランザクション設計 |
| `/architect:design-scalardb-analytics` | sonnet | Analytics Option | HTAP分析プラットフォーム設計 |
| `/architect:design-data-layer` | opus | ScalarDB以外 | 汎用DB設計 |
| `/architect:design-api` | opus | - | surface ごとに REST/GraphQL/hybrid/gRPC/AsyncAPI を選択し、共通の検証可能な契約を生成 |
| `/architect:design-graphql` | opus | GraphQL/hybrid | Spring GraphQL SDL、field coordinate resolver 契約、認可、batch、query governance、transport 設計 |

## 実装

手動拡張ティア — `/architect:pipeline` では実行**されません**。設計フェーズ完了後に、下記の順で
個別に呼び出します。出力先は `generated/` 配下（git-ignore、再実行で上書き）。

| コマンド | モデル | 前提 | 説明 |
|---------|-------|------|------|
| `/architect:design-implementation` | opus | `reports/03_design/` | 実装仕様 — API レイヤー（Controller/DTO/バリデーション/マッパー、トランザクション境界、認可の実施点）＋サービス、リポジトリ、VO |
| `/architect:generate-test-specs` | sonnet | `reports/06_implementation/` | BDD/契約/ユニット/プロパティ/統合/性能テスト仕様 — `aggregate-manifest.json` があれば不変条件ごとに 1 プロパティ |
| `/architect:generate-characterization-tests` | sonnet | `reports/before/{project}/`（レガシーパス） | 稼働中のレガシーシステムから記録したゴールデンマスターテスト — モジュール・シームごと、非決定的フィールドはマスク、`@KnownDefect` マーカー付き。移行計画の各ステップをゲートする安全網 |
| `/architect:generate-scalardb-code` | opus | `reports/06_implementation/` + `scalardb-schema.md` | Spring Boot + ScalarDB コード生成 — `domain/` と `infrastructure/` に加え、不変条件ごとの具体例テストと jqwik プロパティテストを担当 |
| `/architect:generate-api-code` | opus | `api-specifications/` + `api-layer-spec.md` | OpenAPI 契約から API レイヤーを生成 — `operationId` と 1:1 の Controller、スキーマ制約から導出した Bean Validation 付き DTO、マッパー、RFC 9457 ハンドラ、`api-contract-map.json` |
| `/architect:generate-graphql-code` | opus | GraphQL 仕様 + `api-layer-spec.md` | Spring GraphQL API レイヤー — resolver binding、DTO/mapper、security/context、DataLoader、error、query limit、統合 contract map |
| `/architect:generate-contract-tests` | sonnet | `api-contract-map.json` + `contract-test-specs.md` | 実行可能な契約テスト（既定は swagger-request-validator + `@WebMvcTest`、Schemathesis / Pact / ArchUnit はオプトイン） |
| `/architect:generate-acceptance-tests` | sonnet | `bdd-scenarios/` + `api-layer-spec.md` または `repository-interfaces-spec.md` | Gherkin シナリオ（`RULE-`/`EX-` タグ付き）の Cucumber-JVM ステップ定義 — API 経由または Fake 上のアプリケーションサービス経由で駆動し、アイテムが着地するまで `@wip`。ATDD の外側ループとステージ 4 の `acceptanceTest` |
| `/architect:generate-infra-code` | sonnet | `reports/08_infrastructure/` | K8s/Terraform/Helm コード生成 |
| `/architect:generate-docs` | sonnet | 生成・実装済みコード | 生成・実装済みコードの README と `docs/`（コード生成の後、および implement-backlog の Step 5b で実行） |
| `/architect:verify-implementation` | opus | 生成・実装済みコード＋設計 | 設計 ↕ コードの適合性検証（契約・トランザクション・セキュリティ・要件の4軸）。`--gate` で8段階の AI コード品質ゲートを実行（implement-backlog の Step 5c） |

## バックログ配送

レポートをトラッカーの作業アイテムに変換し、マージ済みコードまで進めます。上記のコード生成スキルと
違い、この経路は**マージ対象のコードをプロジェクトの実ソースツリー**に書き込みます（`generated/`
ではありません）。`gh` / `glab` の認証が必要です。

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:export-backlog` | opus | レポート → GitLab / GitHub 上の Epic（What/Why）/ Sub-Epic（What/Key Results）/ Issue（How）。レビュー優先の計画 + 承認ゲートを経て冪等に作成 |
| `/architect:deliver-backlog` | sonnet | Epic 配下の Issue ごとに 実装 → レビュー → 承認 → マージ を統括。`backlog-manifest.json` から再開し、人間のゲートで必ず停止 |
| `/architect:implement-backlog` | sonnet | 1アイテムを Epic 整合的に作業ブランチ上で実装。Step 5b で `generate-docs` を実行し、ドキュメントを同じ PR/MR に載せる |
| `/architect:review-issue` | opus | Epic 全体の整合レビュー、ブロッカー自動修正ループ（回数上限あり）、PR/MR 作成と承認への引き継ぎ |
| `/architect:merge-issue` | opus | マージ前プリフライトと明示的な確認、マージ、Issue クローズ、Sub-Epic/Epic へのロールアップ |
| `/architect:capture-followup` | sonnet | デリバリー中に発見した後続タスクをキューに捕捉し、承認後に対応中の Sub-Epic/Epic へ紐付く Issue として起票(`F` 番台のマニフェストノード) |
| `/architect:report-backlog-status` | haiku | バックログデリバリーのターミナルダッシュボード: Epic/Sub-Epic/Issue ツリーにデリバリー状態と I/R/M ステージを表示、トラッカー同期と次コマンド生成のアクションメニュー付き(`tools/backlog-status.sh` をラップ) |

進捗はトラッカー上に `status::*` ラベル・進捗コメント・チェックボックスとして反映されます
（受入基準は実装・検証時、親のタスクリストのボックスは子のマージ時）。

## レビュー

| コマンド | モデル | IDプレフィックス | 説明 |
|---------|-------|----------------|------|
| `/architect:review-consistency` | sonnet | CON- | 構造的一貫性 |
| `/architect:review-scalardb` | sonnet | SDB- | ScalarDB制約 |
| `/architect:review-data-integrity` | sonnet | DIN- | データ整合性（ScalarDB以外） |
| `/architect:review-operations` | sonnet | OPS- | 運用準備状況 |
| `/architect:review-risk` | opus | RSK- | 分散システムリスク |
| `/architect:review-api-security` | opus | ASEC- | OWASP API Security Top 10、テナント分離、トランザクション境界のセキュリティ。`--mode=code` で実装済みソースに対して再実行 |
| `/architect:review-business` | sonnet | BIZ- | ビジネス要件 |
| `/architect:review-synthesizer` | sonnet | SYN- | 統合と品質ゲート |

## インフラストラクチャ

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:design-infrastructure` | opus | K8s、IaC、マルチ環境 |
| `/architect:design-security` | sonnet | 認証、オブジェクトレベル認可、テナント分離、シークレット管理、OWASP API Security Top 10 マッピング |
| `/architect:design-observability` | sonnet | モニタリング、トレーシング、アラート |
| `/architect:design-disaster-recovery` | sonnet | RTO/RPO、バックアップ、DR |

## レポート

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:report` | haiku | Markdown から HTML への統合レポート(モデルが書き起こすのではなく `tools/build-report.py` が生成) |
| `/architect:review-report` | sonnet | 生成された HTML レポートの品質レビュー（完全性、スコア精度、Mermaid 構文） |
| `/architect:render-mermaid` | haiku | Mermaid から PNG/SVG + 構文修正 |
| `/architect:estimate-cost` | sonnet | インフラ、ライセンス、運用コスト |
| `/architect:estimate-token-cost` | sonnet | エージェント実行のトークン使用量と USD コスト（事前見積り、実績で校正） |
| `/architect:report-token-cost` | haiku | 記録済み実績コストのターミナルレポート（既定は対話型2ペインダッシュボード/10秒間隔・上ペインで選択、下ペインに詳細やセッションログ、`--once` 単発、`--follow` ストリーム、`--session=ID` 単一セッション+ログ、`--since`、`--breakdown=tokens\|cost`（ダッシュボードは内訳列を既定で `$` 表示、`b` で切替）、`--ascii`（グリフ欠落で文字化けする端末向けの ASCII 描画）、`--ambiguous-width=2`（East Asian Ambiguous 文字を2桁で描画する端末向けの幅補正）、`--debug`、`--md`、`--json`） |
| `/architect:report-status` | haiku | パイプライン進捗のターミナルダッシュボード: フェーズツリーに状態(完了後に上流が更新されたフェーズは `stale`)・宣言出力の充足度・稼働中ハートビート・未充足の依存・フェーズ別コストを表示、次コマンド生成のアクションメニュー、Claude への質問キー、`Tab` で4つのビュー（Product / Architect / Code Generation / Backlog Delivery）を巡回(`tools/nexus-status.sh` をラップ) |

## ユーティリティ

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/architect:init-output` | haiku | 出力ディレクトリの初期化 |
| `/architect:update-knowledge` | haiku | OKF ナレッジバンドルの取得・更新（`tools/update-okf-bundle.sh` をラップ。フラグなし=存在保証、`--latest`=最新を取得、`--status`=解決パス・コミット・収録バージョンを表示、`--bundle=scalardb\|k8s-tf`=対象バンドルの選択。`scalardb` はバージョン固定の ScalarDB/ScalarDL/ScalarDB Saga バンドル、`k8s-tf` はリモートを持たない同梱の Kubernetes/Terraform 基盤バンドル） |

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

## マルチクラウド インフラ

すべてのスキルは `/infra:skill-name` として呼び出します。architect パイプラインとは別の
プラグインです。`/architect:design-infrastructure` が設計パイプラインの1フェーズとして
論理的なインフラを決めるのに対し、これらのスキルは AWS / Azure / GCP の具体構成を
4環境（local / test / staging / production）にわたって決定・構築します。すべての主張は
モデルの記憶ではなく同梱の OKF `okf-k8s-tf` バンドル（@rules/okf-k8s-tf-bundle.md）に
根拠を置きます。

| コマンド | モデル | 説明 |
|---------|-------|------|
| `/infra:start` | sonnet | トリアージとルーティング：バンドル解決、`stale_after` 鮮度チェック、対象環境とクラウドの確定、設計 / 実装 / レビューへの委譲 |
| `/infra:design` | opus | 要件からの構成設計 — 責任分界（1リソース1オーナー）、L1〜L4 の層別設計、環境マトリクス、digest 単位の昇格経路、ADR。コードは書かない |
| `/infra:implement` | sonnet | Terraform / Kubernetes マニフェスト / Helm values / Kustomize overlay / GitLab CI を、バージョン固定・秘密情報非露出のうえ実在のインフラリポジトリへ書き込む |
| `/infra:review` | opus | IaC・設計書レビュー — 所有権の重複、image digest の断絶、秘密情報の露出を最優先で確認し、マルチクラウド観点と環境パリティ観点を必ず含める |

`/architect:generate-infra-code` が `generate` フェーズとして `generated/` に雛形を出力するのに
対し、`/infra:implement` はプロジェクト実体のインフラリポジトリへマージ対象のコードを書きます。

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
| `/product:create-domain-story` | opus | 2. UX 基盤 | ペルソナ起点のドメインストーリーテリング（アクター=ペルソナ、活動=ジャーニー順のジョブストーリー）。UI モックが描画する軸（オプション）。`--mode=event-storming` で Process Modeling EventStorming として進行 |
| `/product:design-system` | opus | 2. UX 基盤 | 独立管理のデザインシステムを構築または `--import`（DTCG トークン + コンポーネント + ガイドライン）。UI モックのスタイルを規定（オプション、単独実行可） |
| `/product:generate-ui-mock` | sonnet | 3. UX → 仕様 | ドメインストーリーに駆動され、デザインシステムでスタイルされた主要画面のナビゲート可能な UI モック（各活動 → 1 画面、ストーリー順のクリック可能なフローとして連結） |
| `/product:define-features` | sonnet | 3. UX → 仕様 | UI モックからフィーチャーを抽出（各画面アクション → Command/フィーチャー）。ジャーニー段階をバックボーン、MoSCoW 帯をリリーススライスとするユーザーストーリーマップとして配置 |
| `/product:example-map` | opus | 3. UX → 仕様 | フィーチャーごとの Example Mapping — 業務ルール（`RULE-`）、境界の両側を示す具体例（`EX-`）、未決の問いを `OQ-` として記録し、Gherkin・集約の不変条件・バックログの受入基準へ流す（オプション） |
| `/product:define-data-model` | opus | 3. UX → 仕様 | UI モックとフィーチャーからデータモデルを 2 パスで導出（明示 → 暗黙） |
| `/product:generate-frontend` | sonnet | 3. UX → 仕様 | UI モック + デザインシステムから実行可能な React + Storybook フロントエンドを生成（Atomic Design、トークンスタイリング、react-router）— 選択式、spec フェーズ末尾 |
| `/product:map-domains` | opus | 4. ドメイン & API | フィーチャー/エンティティを境界づけられたコンテキストへ抽象化（DDD 戦略的設計）。`--mode=event-storming` で境界を Big Picture EventStorming の対話から発見し `reports/03_domain/event-timeline.md` に記録 |
| `/product:design-api` | opus | 4. ドメイン & API | 論理 API を 3 つの API-Led レイヤーで設計（System/Process/Experience） |
| `/product:design-sla` | sonnet | 5. 品質 & 非機能 | サービスごとの SLI/SLO/SLA とエラーバジェット |
| `/product:define-nfr` | sonnet | 5. 品質 & 非機能 | SLO を測定可能な非機能要件へ変換（可用性、レイテンシ p95/p99 など） |
| `/product:design-architecture` | opus | 4/5. 統合 | 全体アーキテクチャ図（構成/クリティカルパス/デプロイ）＋ 技術適合度評価（Kong / ScalarDB / ScalarDB Analytics / ScalarDL）と採用/条件付/不採用の根拠 |
| `/product:review` | opus | R. レビュー & レポート | プロダクト成果物をレビュー（整合性、トレーサビリティ、拡張性、戦略） |
| `/product:report` | sonnet | R. レビュー & レポート | 成果物を 1 つの自己完結型 HTML レポートに統合（冒頭に検証ステータス） |
| `/product:report-status` | haiku | R. レビュー & レポート | プロダクトパイプライン進捗のターミナルダッシュボード: フェーズツリーに状態(完了後に上流が更新されたフェーズは `stale`)・宣言出力の充足度・ゲート判定と未検証の前提・フェーズ別コストを表示、次コマンド生成のアクションメニュー付き(`tools/nexus-status.sh` をラップ) |
| `/product:adapt-change` | opus | 6. 適応 | 再伝播エンジン：変化から影響範囲を算定し、影響を受けるスキルのみ再実行 |

## 呼び出しシグネチャ

各コマンド自身のフラグ一覧。出典は各 `SKILL.md`（正本）で、シェルツールをラップするコマンドについては
そのツールの引数パーサと `tools/docs_consistency.test.py` が突き合わせています。記載がないコマンドは
引数を取りません。

このブロックが**列挙しないもの**が2つあります。ターミナル系コマンド（`report-status`、
`report-backlog-status`、`report-token-cost`）は表示系フラグを `tools/nexus-status.sh` /
`tools/token-cost-report.sh` にそのまま渡します — `--live`/`--watch[=SEC]`、`--plugin`、`--width`、
`--color`/`--no-color`、`--glyphs`、`--debug`、コストレポートではさらに `--currency`、`--fx`、
`--top`、`--log-tail`。定義元はツール側なので、最新の一覧は `--help` で確認してください。もう1つは
移行ルーター配下のネストされたスキル（`skills/migrate-oracle/…`）で、ルーターがパス参照で読むため
スラッシュコマンドではなく、ここにシグネチャはありません。

```text
# Orchestration & setup
/architect:start [target_path]
/architect:pipeline [target_path] [--skip-{phase}] [--resume-from=phase-N] [--rerun-from=phase-N] [--analyze-only] [--no-scalardb] [--lang=en|ja]
/architect:init-output [project_name] [--reset]
/product:start [target] [--auto] [--profile=mvp|core-only|ux-to-spec|full] [--frontend|--no-frontend] [--lang=ja|en]
/product:init-output [project_name] [--reset]

# Requirements, investigation, analysis, evaluation
/architect:define-requirements [target_path] [--input=<file|dir>] [--auto] [--no-scalardb]
/architect:investigate [target_path]
/architect:investigate-security [target_path]
/architect:analyze [target_path]
/architect:analyze-data-model [target_path]
/architect:evaluate-mmi [target_path]
/architect:evaluate-ddd [target_path]
/architect:integrate-evaluations

# Design
/architect:map-domains
/architect:redesign
/architect:create-domain-story [--domain=<name>] [--mode=story|event-storming] [--auto]
/architect:design-aggregate [--aggregate=<name>] [--context=<name>] [--auto] [--lang=en|ja]
/architect:design-state-machine [--aggregate=<name>] [--auto] [--lang=en|ja]
/architect:design-microservices
/architect:select-scalardb-edition
/architect:design-scalardb
/architect:design-scalardb-analytics
/architect:design-data-layer
/architect:design-api
/architect:design-graphql [--service=<name>] [--lang=en|ja]
/architect:design-implementation
/architect:design-infrastructure
/architect:design-security
/architect:design-observability
/architect:design-disaster-recovery

# Code generation & verification
/architect:generate-test-specs
/architect:generate-characterization-tests [target_path] [--scope=module|service|repo] [--module=<name>] [--out=<path>] [--seam=http|cli|function|db] [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja]
/architect:generate-scalardb-code
/architect:generate-api-code [--service=<name>] [--out=<path>] [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja]
/architect:generate-graphql-code [--service=<name>] [--out=<path>] [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja]
/architect:generate-contract-tests [--service=<name>] [--out=<path>] [--stack=default|schemathesis|pact|archunit] [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja]
/architect:generate-acceptance-tests [--service=<name>] [--feature=<id>] [--driver=api|application] [--out=<path>] [--confirm-versions|--no-confirm-versions] [--dry-run] [--auto] [--lang=en|ja]
/architect:generate-infra-code
/architect:generate-docs [target] [--scope=changed|service|repo] [--source-root=<path>] [--readme-only] [--issue=<id>] [--dry-run] [--auto] [--lang=en|ja]
/architect:verify-implementation [target_path] [--service=<name>] [--scope=changed|service|repo] [--source-root=<path>] [--gate] [--item=<backlog-id>] [--auto] [--lang=en|ja]

# Review
/architect:review-consistency
/architect:review-scalardb
/architect:review-data-integrity
/architect:review-operations
/architect:review-risk
/architect:review-business
/architect:review-api-security [--mode=design|code] [--source-root=<path>] [--scope=changed|service|repo]
/architect:review-synthesizer
/architect:review-report

# Backlog delivery
/architect:export-backlog [--target=gitlab|github] [--project=<path>|--repo=<owner/name>] [--group=<gitlab-group>] [--dry-run] [--update] [--lang=en|ja]
/architect:deliver-backlog [--epic=<id>] [--issue=<id>] [--from=implement|review|merge] [--auto] [--yes-merge] [--max-fix-rounds=N] [--export] [--dry-run] [--lang=en|ja]
/architect:implement-backlog [item] [--epic=<id>] [--build-context] [--review-epic[=<id>]] [--out=<path>] [--confirm-versions|--no-confirm-versions] [--refresh-versions] [--dry-run] [--auto] [--lang=en|ja]
/architect:review-issue [item] [--epic=<id>] [--max-fix-rounds=N] [--base=<branch>] [--no-fix] [--dry-run] [--auto] [--lang=en|ja]
/architect:merge-issue [item|mr|pr] [--strategy=merge|squash|rebase] [--delete-branch] [--yes-merge] [--dry-run] [--auto] [--lang=en|ja]
/architect:capture-followup [title] [--parent=<local_id|#iid>] [--from=<file|issue-ref>] [--queue-only] [--flush] [--dry-run] [--auto] [--lang=en|ja]
/architect:report-backlog-status [--once] [--no-sync] [--exec] [--epic=<id>] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en]

# Reporting, cost & status
/architect:report
/architect:render-mermaid [target_path]
/architect:estimate-cost
/architect:estimate-token-cost [target_path]
/architect:report-token-cost [--once] [--follow] [--session=ID] [--since=7d] [--breakdown=tokens|cost] [--ascii] [--ambiguous-width=2] [--md] [--json] [--lang=ja|en]
/architect:report-status [--once] [--view=product|architect|codegen|backlog] [--group=core|extension] [--phase=<name>] [--exec] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en]
/architect:update-knowledge [--latest] [--status] [--bundle=<name>]
/product:report [--auto] [--lang=ja|en]
/product:report-status [--once] [--phase=<name>] [--exec] [--json] [--md] [--ascii] [--ambiguous-width=2] [--lang=ja|en]

# Multi-cloud infrastructure
/infra:start [target] [--env=<env>] [--cloud=<cloud>]
/infra:design [target] [--env=<env>] [--cloud=<cloud>] [--auto]
/infra:implement [target] [--env=<env>] [--cloud=<cloud>] [--auto]
/infra:review [target] [--env=<env>] [--cloud=<cloud>] [--round=<n>]

# Database migration
/architect:migrate-database
/architect:migrate-oracle
/architect:migrate-mysql
/architect:migrate-postgresql

# ScalarDB development
/scalardb:model
/scalardb:config
/scalardb:scaffold
/scalardb:error-handler
/scalardb:crud-ops
/scalardb:jdbc-ops
/scalardb:local-env
/scalardb:docs
/scalardb:build-app
/scalardb:review-code
/scalardb:migrate

# Product direction
/product:define-vision [target] [--input=<file|dir>] [--auto] [--lang=ja|en] [--no-research]
/product:name-product [target] [--input=<file|dir>] [--count=N] [--style=acronym|initialism|hybrid] [--seed=<letters|word>] [--auto] [--lang=ja|en]
/product:define-success-metrics [--auto] [--lang=ja|en]
/product:research-landscape [target] [--input=<file|dir>] [--auto] [--lang=ja|en] [--no-research]
/product:design-revenue [--input=<file|dir>] [--auto] [--lang=ja|en]
/product:define-scope [--constraints=<file|text>] [--input=<file|dir>] [--auto] [--lang=ja|en]
/product:validate-assumptions [--auto] [--lang=ja|en]
/product:generate-persona [--input=<file|dir>] [--auto] [--lang=ja|en]
/product:map-journey [--auto] [--lang=ja|en]
/product:design-positioning [--auto] [--lang=ja|en]
/product:create-domain-story [--persona=<PER>] [--job=<JOB>] [--domain=<CTX>] [--mode=story|event-storming] [--auto] [--lang=ja|en]
/product:design-system [--name=<id>] [--import=<path>] [--fidelity=lo|mid] [--auto] [--lang=ja|en]
/product:generate-ui-mock [--fidelity=lo|mid] [--auto] [--lang=ja|en]
/product:define-features [--auto] [--lang=ja|en]
/product:example-map [--feature=<FEAT>] [--auto] [--lang=ja|en]
/product:define-data-model [--auto] [--lang=ja|en]
/product:generate-frontend [--design-system=<name>] [--out=<path>] [--confirm-versions|--no-confirm-versions] [--refresh-versions] [--auto] [--lang=ja|en]
/product:map-domains [--mode=derive|event-storming] [--auto] [--lang=ja|en]
/product:design-api [--auto] [--lang=ja|en]
/product:design-sla [--auto] [--lang=ja|en]
/product:define-nfr [--auto] [--lang=ja|en]
/product:design-architecture [--auto] [--lang=ja|en]
/product:review [--auto] [--lang=ja|en]
/product:adapt-change --change="<text>" [--type=constraint|market|competitor|tech|regulation] [--auto] [--lang=ja|en]
```
