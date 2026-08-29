# DDD 手法カバレッジ

このツールキットがどの DDD 手法を、どこで、どこまで実装しているかの一覧。外部レビューのたびに
再導出するのではなく、リポジトリ側で答えを保守するためにあります — 最初の外部レビュー
（2026 年 8 月）は成果物を見つけられずに 2 行を誤評価しており、この表はその再発を防ぐものです。

`tools/docs_consistency.test.py` は、この表が挙げるスキルがすべて登録済みコマンドであること、
引用する成果物パスがいずれかのスキル（SKILL.md・manifest・出力ツリー）で宣言されていることを検証します — rule ファイルがパスに言及しているだけでは宣言と見なしません。**状況**列は判断であり、
行のスキルが変わったときに手で見直します。

凡例: ◎ 専用スキルまたは手順の定義された成果物あり · ○ 他スキルに組み込み · △ 参照・評価・
一部生成のみで独立した手法ではない · × なし。

## ドメイン探索

| 手法 | 状況 | 場所 | 成果物 |
|------|------|------|--------|
| Domain Storytelling | ◎ | `/architect:create-domain-story`, `/product:create-domain-story` | `reports/04_stories/domain-story-{domain}.md`, `reports/01_ux/domain-stories/` |
| EventStorming — Big Picture | ◎ | `/product:map-domains --mode=event-storming` | `reports/03_domain/event-timeline.md`（セッション記録。`CTX-` は `bounded-contexts.md` のみ） |
| EventStorming — Process Modeling | ◎ | `/product:create-domain-story --mode=event-storming`, `/architect:create-domain-story --mode=event-storming` | ストーリーの Process Model 節 |
| EventStorming — Software Design | ○ | `/architect:design-aggregate` | 集約ごとのコマンドとイベント |
| Event Modeling | △ | 状態遷移と集約がイベント・コマンド・リードモデルを持つが、時系列起点の成果物はない | — |
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
| チームトポロジー / Conway 整合 | ○ | `/architect:design-microservices` | `reports/03_design/target-architecture.md` |

## 戦術設計

| 手法 | 状況 | 場所 | 成果物 |
|------|------|------|--------|
| 集約 / 集約ルート | ◎ | `/architect:design-aggregate` | `reports/03_design/aggregates/aggregate-manifest.json`（`AGG-`） |
| エンティティ | ◎ | `/product:define-data-model`, `/architect:design-aggregate` | `reports/02_spec/data-model.md`（`ENT-`）、集約メンバー |
| 値オブジェクト | ◎ | `/architect:design-aggregate` | `kind: value` のメンバーと検証規則 |
| 不変条件 | ◎ | `/architect:design-aggregate` | positive / negative の例付き不変条件。`tools/lib/aggregate_manifest.py` が検証 |
| ドメインイベント | ◎ | `/architect:design-aggregate`, `/architect:design-state-machine` | 集約イベント、状態遷移イベント |
| ファクトリ | ○ | `/architect:design-aggregate` | 生成コマンドと生成時に成り立つべき条件 |
| 仕様（Specification） | ○ | `/architect:design-aggregate` | 集約ごとの `specifications` |
| リポジトリ | ◎ | `/architect:design-aggregate`, `/architect:design-implementation` | ルートごとに 1 つ。`reports/06_implementation/repository-interfaces-spec.md` |
| ドメインサービス / アプリケーションサービス | ○ | `/architect:design-implementation` | `reports/06_implementation/domain-services-spec.md`, `api-layer-spec.md` |
| レイヤード / ヘキサゴナル | ◎ | `/architect:evaluate-ddd`（評価）, `/architect:design-implementation`, `/architect:generate-contract-tests`（ArchUnit） | `reports/02_evaluation/ddd-tactical-architecture-evaluation.md` |
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
| Specification by Example / BDD | ◎ | `/architect:generate-test-specs` | `reports/07_test-specs/bdd-scenarios/` — `RULE-` / `EX-` からの `Rule:` / `Scenario:` |
| 受入基準 | ◎ | `/architect:export-backlog`, `/architect:define-requirements` | `RULE-` からの Issue 受入基準・FR 受入基準 |
| 契約テスト | ◎ | `/architect:generate-contract-tests` | `generated/{service}/src/test/java/**/contract/` |
| プロパティベーステスト | ◎ | `/architect:generate-test-specs`, `/architect:generate-scalardb-code` | `reports/07_test-specs/property-test-specs.md`。不変条件ごとの jqwik プロパティ |
| Three Amigos | × | 人間の会議体。Example Mapping セッションがその成果物側 | — |
| ユーザーストーリーマッピング | △ | ジャーニー・ジョブ・フィーチャーが内容を持つが、backbone / walking skeleton の成果物はない | — |
| インパクトマッピング | △ | 成功指標 → フィーチャーの traceability が連鎖を担う。専用マップはない | — |

## 意図的に実装しないもの

| 手法 | 理由 |
|------|------|
| CRC カード | 責務と協調者を検証器付きで記録する集約マニフェストで代替 |
| Three Amigos | 会議形式であり成果物ではない。`/product:example-map` が会議の産物を生成する |
| インパクトマッピング | `NSM-` → `FEAT-` の traceability グラフが「どの成果物がどの目標に効くか」に答える |

## この表の更新

スキルを変えたら同じコミットで行を変える。新しい手法はスキルより先に `×` の行を追加し、
次の外部レビューに見つけられる前に、ギャップを自分たちで見えるようにする。
