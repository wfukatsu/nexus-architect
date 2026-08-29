# DDD 手法カバレッジ

このツールキットがどの DDD 手法を、どこで、どこまで実装しているかの一覧。外部レビューのたびに
再導出するのではなく、リポジトリ側で答えを保守するためにあります — 最初の外部レビュー
（2026 年 8 月）は成果物を見つけられずに 2 行を誤評価しており、この表はその再発を防ぐものです。

`tools/docs_consistency.test.py` は、この表が挙げるスキルがすべて登録済みコマンドであること、
引用する成果物パスがいずれかのスキル（SKILL.md・manifest・出力ツリー）で宣言されていることを検証します — rule ファイルがパスに言及しているだけでは宣言と見なしません。**状況**列は判断であり、
行のスキルが変わったときに手で見直します。

これらのスキルが `ec-monolith` サンプルに対して生成したドキュメント一式を
`samples/ec-monolith/expected-reports/` にコミットしています（本来の `reports/` ツリーは git-ignore 対象）。
`samples/ec-monolith/reference-set.test.py` がその妥当性とこの表との整合を保ちます。

凡例: ◎ 専用スキルまたは手順の定義された成果物あり · ○ 他スキルに組み込み · △ 参照・評価・
一部生成のみで独立した手法ではない · × なし。

## ドメイン探索

| 手法 | 状況 | 場所 | 成果物 |
|------|------|------|--------|
| Domain Storytelling | ◎ | `/architect:create-domain-story`, `/product:create-domain-story` | `reports/04_stories/domain-story-{domain}.md`, `reports/01_ux/domain-stories/` |
| EventStorming — Big Picture | ◎ | `/product:map-domains --mode=event-storming` | `reports/03_domain/event-timeline.md`（セッション記録。`CTX-` は `bounded-contexts.md` のみ） |
| EventStorming — Process Modeling | ◎ | `/product:create-domain-story --mode=event-storming`, `/architect:create-domain-story --mode=event-storming` | ストーリーの Process Model 節 |
| EventStorming — Software Design | ○ | `/architect:design-aggregate` | 集約ごとのコマンドとイベント |
| Event Modeling | × | 意図的に実装しない — 下記参照 | — |
| Knowledge crunching | ○ | 探索系スキルの対話ステージ、ユビキタス言語 | — |
| CRC カード | × | — | — |

## 戦略設計

| 手法 | 状況 | 場所 | 成果物 |
|------|------|------|--------|
| ユビキタス言語 | ◎ | `/architect:analyze`, `/product:map-domains` | `reports/01_analysis/ubiquitous-language.md`, `reports/03_domain/ubiquitous-language.md` |
| サブドメイン分類（Core / Supporting / Generic） | ◎ | `/product:map-domains`, `/architect:map-domains` | `reports/03_domain/domain-map.md`, `reports/03_design/domain-analysis.md` |
| 境界づけられたコンテキスト | ◎ | `/product:map-domains`, `/architect:redesign` | `reports/03_domain/bounded-contexts.md`, `reports/03_design/bounded-contexts-redesign.md` |
| Bounded Context Canvas | ◎ | `/architect:redesign`, `/product:map-domains` | 両成果物のコンテキストごとの Canvas 節 |
| コンテキストマッピング | ◎ | `/architect:redesign`, `/product:map-domains` | `reports/03_design/context-map.md`、`bounded-contexts.md` の Context Map |
| アーキテクチャ決定記録（ADR） | ◎ | `/architect:redesign` がログを開始し、`/architect:design-microservices`, `/architect:design-scalardb`, `/architect:design-data-layer`, `/architect:design-api` が追記 | `reports/03_design/adr/adr-NNN-<slug>.md`（`ADR-`）、`reports/03_design/adr/index.md`、`tools/lib/adr_records.py` で検証 |
| Domain Vision Statement | ◎ | `/product:define-vision` | `reports/00_core/vision-mission-value.md` の Domain Vision Statement 節 |
| Core Domain への投資方針 | ◎ | `/product:map-domains` | `reports/03_domain/domain-map.md` |
| 公開ホスト言語（Published Language）/ コンテキスト間イベント契約 | ◎ | `/architect:design-aggregate` が書き、`/architect:design-microservices` が消費側を完成させ、`/architect:design-api` がそこから AsyncAPI を生成 | `reports/03_design/domain-event-catalog.json` + `.md`（発行者・コンテキストマップ関係ごとの消費者・配信契約）、`tools/lib/domain_event_catalog.py` で検証。`reports/03_design/api-specifications/asyncapi/` |
| チームトポロジー / Conway 整合 | ○ | `/architect:design-microservices` | `reports/03_design/target-architecture.md` |

## 戦術設計

| 手法 | 状況 | 場所 | 成果物 |
|------|------|------|--------|
| 集約 / 集約ルート | ◎ | `/architect:design-aggregate` | `reports/03_design/aggregates/aggregate-manifest.json`（`AGG-`） |
| エンティティ | ◎ | `/product:define-data-model`, `/architect:design-aggregate` | `reports/02_spec/data-model.md`（`ENT-`）、集約メンバー |
| 値オブジェクト | ◎ | `/architect:design-aggregate` | `kind: value` のメンバーと検証規則 |
| 不変条件 | ◎ | `/architect:design-aggregate` | positive / negative の例付き不変条件。`tools/lib/aggregate_manifest.py` が検証 |
| ドメインイベント | ◎ | `/architect:design-aggregate`, `/architect:design-state-machine` | 集約イベント、状態遷移イベント。`reports/03_design/domain-event-catalog.json` に集約 |
| ファクトリ | ○ | `/architect:design-aggregate` | 生成コマンドと生成時に成り立つべき条件 |
| 仕様（Specification） | ○ | `/architect:design-aggregate` | 集約ごとの `specifications` |
| リポジトリ | ◎ | `/architect:design-aggregate`, `/architect:design-implementation` | ルートごとに 1 つ。`reports/06_implementation/repository-interfaces-spec.md` |
| ドメインサービス / アプリケーションサービス | ○ | `/architect:design-implementation` | `reports/06_implementation/domain-services-spec.md`, `api-layer-spec.md` |
| レイヤード / ヘキサゴナル | ◎ | `/architect:evaluate-ddd`（評価）, `/architect:design-implementation`, `/architect:generate-contract-tests`（ArchUnit） | `reports/02_evaluation/ddd-tactical-architecture-evaluation.md` |
| クリーンアーキテクチャ命名（Use Case / Interactor / Presenter） | ◎ | `/architect:design-implementation --layering=clean`; `generate-api-code`, `generate-graphql-code`, `generate-scalardb-code`, `generate-contract-tests`, `generate-acceptance-tests`, `verify-implementation` が読む | `reports/06_implementation/api-layer-spec.md` frontmatter の `layering_style` |
| 既存システムの DDD 成熟度評価 | ◎ | `/architect:evaluate-ddd` | `reports/02_evaluation/ddd-strategic-evaluation.md`, `ddd-tactical-architecture-evaluation.md` |

## 振る舞い・整合性・トランザクション

| 手法 | 状況 | 場所 | 成果物 |
|------|------|------|--------|
| 状態遷移モデリング | ◎ | `/architect:design-state-machine` | `reports/03_design/state-machines/state-machine-manifest.json`（`STM-`） |
| 状態 × イベント行列 | ◎ | `/architect:design-state-machine` | 全セル決定済み。`tools/lib/state_machine_manifest.py` が検証 |
| 並行・競合設計 | ◎ | `/architect:design-state-machine` | 競合表 |
| Local / Distributed / Saga 分類 | ◎ | `/architect:design-aggregate`, `/architect:design-state-machine`, `/architect:design-scalardb` | コマンド / 遷移ごと。`reports/03_design/scalardb-transaction.md` |
| Saga / 補償 | ◎ | `/architect:design-scalardb` | `scalardb-transaction.md` の Saga 設計チェックリスト |
| CQRS / リードモデル | ◎ | `/architect:design-scalardb`, `/architect:design-data-layer` | Read Model, CQRS and Event Sourcing Decisions 節 |
| イベントソーシング | ◎ | `/architect:design-scalardb`, `/architect:design-data-layer` | 同節。`rules/scalardb-schema-design.md` の Event Store パターン |

## 要件と具体例

| 手法 | 状況 | 場所 | 成果物 |
|------|------|------|--------|
| Example Mapping | ◎ | `/product:example-map` | `reports/02_spec/examples/example-map-{feat}.md`（`RULE-`, `EX-`） |
| Specification by Example / BDD | ◎ | `/architect:generate-test-specs`（シナリオ）、`/architect:generate-acceptance-tests`（実行可能化） | `reports/07_test-specs/bdd-scenarios/` — `RULE-` / `EX-` からの `Rule:` / `Scenario:`。Cucumber ステップ定義と `reports/07_test-specs/acceptance-test-coverage.md` |
| 受入基準 | ◎ | `/architect:export-backlog`, `/architect:define-requirements` | `RULE-` からの Issue 受入基準・FR 受入基準 |
| 契約テスト | ◎ | `/architect:generate-contract-tests` | `generated/{service}/src/test/java/**/contract/` |
| プロパティベーステスト | ◎ | `/architect:generate-test-specs`, `/architect:generate-scalardb-code` | `reports/07_test-specs/property-test-specs.md`。不変条件ごとの jqwik プロパティ |
| Three Amigos | × | 人間の会議体。Example Mapping セッションがその成果物側 | — |
| ユーザーストーリーマッピング | ○ | `/product:define-features` | `reports/02_spec/feature-list.md` のユーザーストーリーマップ節 — ジャーニー段階をバックボーン、`FEAT-` をストーリー、MoSCoW 帯をリリーススライス、Must を walking skeleton とする |
| インパクトマッピング | × | 意図的に実装しない — 下記参照 | — |

## テスト駆動開発

DDD モデルを実行可能にするプラクティスについて、ツールキットがどこまで対応しているか。上の手法群は
オラクル（不変条件、行列、具体例）を生み出す側であり、ここではコードがそれらに駆動されているかを扱う。

| 手法 | 状況 | 場所 | 成果物 |
|------|------|------|--------|
| Red → Green → Refactor（テストファースト、履歴から検証可能） | ◎ | `/architect:implement-backlog` Step 5、`rules/tdd-workflow.md` §2 | 作業ブランチ上のユニットごとの `test:` → `feat:` → `refactor:` コミット列。順序は `reports/09_verification/quality-gate.json`（`test_first`）に記録 |
| 二重ループ（外側 ATDD、内側 TDD） | ◎ | `/architect:generate-acceptance-tests`（外側ループのテスト）、`/architect:implement-backlog` Step 5、`rules/tdd-workflow.md` §3 | 外側ループを担った受入レベルのテストを Issue の進捗コメントに明記。`@wip` シナリオは通したアイテムが外す |
| Walking skeleton | ◎ | `/product:define-features`（Must 行）、`/architect:export-backlog`（新サービスごとに `walking-skeleton` Issue を 1 件、順序の先頭に）、`/architect:implement-backlog`（最初に実装する） | ユーザーストーリーマップの Must 行。`walking-skeleton` Issue |
| テストダブル — リポジトリポートごとの Fake、注入される Clock / ID 生成器 | ◎ | `/architect:design-implementation`（仕様化）、`/architect:generate-scalardb-code`（生成）、`/architect:generate-contract-tests`（ArchUnit で強制） | `generated/{service}/src/test/java/**/fakes/`、`reports/06_implementation/repository-interfaces-spec.md` |
| 変更範囲に対するカバレッジ閾値 | ◎ | `/architect:verify-implementation --gate` ステージ 2、`rules/ai-code-quality-gate.md` §Test quality | `reports/09_verification/quality-gate.json`（`coverage`）、`generated/{service}/build.gradle` の JaCoCo 検証 |
| ドメイン層のミューテーションテスト | ◎ | `/architect:verify-implementation --gate` ステージ 2 | `reports/09_verification/quality-gate.json`（`mutation`、生存ミュータントを行単位、不変条件行の生存を名前で） |
| レガシーコードの特性テスト / ゴールデンマスター | ◎ | `/architect:generate-characterization-tests`。ベースラインは `/architect:implement-backlog` Step 5、ゲートのステージ 4 | `reports/07_test-specs/characterization-test-coverage.md`。移行計画の各ステップをゲートする `characterizationTest` タスク |
| 実エンジン上のトランザクションシナリオ統合テスト | ◎ | `/architect:generate-scalardb-code`（`TX-` ごとの `*IT`、SQLite バックエンドのインプロセス ScalarDB）、`/scalardb:scaffold` / `/scalardb:build-app` | `generated/{service}/src/test/java/**/integration/`。ゲートのステージ 4 |
| バグ修正は再現テストから | ◎ | `/architect:review-issue` Step 4 | 作業ブランチ上で `fix:` の前に `test: reproduce <blocker>` コミット |
| フロントエンドのコンポーネント / ルーティング / e2e テスト | ◎ | `/product:generate-frontend` | composed stories 上のコンポーネント・ページごとの `*.test.tsx`、`e2e/` の Playwright ストーリーフロー、`vitest.config.ts` の閾値 |
| スイート実行時間予算 / 構成 | ◎ | `rules/tdd-workflow.md` §6、`rules/ai-code-quality-gate.md` §Test quality | `reports/09_verification/quality-gate.json` にタスクごとの実時間（層別予算に対して）と層別テスト数 |
| フレーキーテストのポリシー | ◎ | `rules/tdd-workflow.md` §6 — タグで隔離し、計数・経過日数を記録、再試行はしない。シード付きプロパティ、マスク済み特性フィクスチャ | `reports/09_verification/quality-gate.json` に隔離テストと経過日数。`/architect:capture-followup` で follow-up Issue |
| ユビキタス言語に基づくテスト命名 | ◎ | `rules/tdd-workflow.md` §6、`/architect:review-consistency` の用語一貫性ディメンション | 用語集の語で `should_<outcome>_when_<condition>`。テスト名・シナリオ名に対する CON-3xx 指摘 |

## 意図的に実装しないもの

| 手法 | 理由 |
|------|------|
| CRC カード | 責務と協調者を検証器付きで記録する集約マニフェストで代替 |
| Three Amigos | 会議形式であり成果物ではない。`/product:example-map` が会議の産物を生成する |
| インパクトマッピング | `NSM-` → `FEAT-` の traceability グラフが「どの成果物がどの目標に効くか」に答える |
| Event Modeling | 3 つのレーンはすでに成果物になっている: コマンドとイベントは集約 manifest、状態遷移と状態×イベント行列は状態遷移 manifest、コンテキスト横断の流れはドメインイベントカタログ、リードモデルは CQRS 節。時系列起点の描画は同じ manifest の 4 つ目のビューにすぎず固有のバリデータを持たない。カタログの発行者 → 消費者図がスイムレーン相当のビュー |

## この表の更新

スキルを変えたら同じコミットで行を変える。新しい手法はスキルより先に `×` の行を追加し、
次の外部レビューに見つけられる前に、ギャップを自分たちで見えるようにする。
