# 変更履歴

Nexus Architect の主な変更点を記録します。

書式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に基づき、
バージョニングは [セマンティック バージョニング](https://semver.org/lang/ja/) に従います。
バージョン番号は `.claude-plugin/marketplace.json` のプラグインごとのバージョンを指し、
4 つのプラグイン（`product`・`architect`・`scalardb`・`infra`）は同一の番号で一括リリースされます。

## [0.33.2] - 2026-08-29

`/architect:design-api`（カタログからの AsyncAPI）と `/architect:redesign`（ADR ログをゼロから開く）の初回 end-to-end
実行で見つかったギャップ。

### Fixed
- **`design-api` とカタログ。** 既にチャネルを持つ孤児イベントは削除せず維持して報告（削除は §8 の破壊的変更）。制約は
  契約自身のもので、カタログはフィールド名を与える。カタログに無いフィールドは `deprecated` のまま残し contract-fidelity §8
  に従って削除する。冪等キーの所有は一方向 — 値はカタログ、重複排除ルールは契約。他スキルのファイルにある相互参照の指摘は
  報告のみでブロックしない。`grpc/` は採用時のみ生成。正規のバリデータを明記。
- **ADR ルール、再び。** `decided_at` は決定した日。回答済み `OQ-` は根拠として有効。アンカーは自由文で解決されない。
  index は標準フロントマターを持ち `skill` は最後に再生成したスキル。記録のフロントマターはルールの形であり、
  `rules/output-conventions.md` に唯一の例外として明記。番号は再採番しない。追記する 4 スキルは `upstream` の指示を
  誤って言い換えず、ルールに委ねる。
- **`redesign`。** Canvas の `Name` はレガシー経路で `BC-n` にフォールバック。集約境界は `design-aggregate` の決定であり
  `redesign` は ADR を書かない。

## [0.33.1] - 2026-08-29

ドメインイベントカタログ付きの `/architect:design-aggregate --auto` を `ec-monolith` サンプルで初めて end-to-end
実行して見つかった、スキル自身のギャップ。

### Fixed
- **カタログが自分の関係パターンを名乗れるようになった。** 消費者の `relationship` 語彙に `published-language` を追加 —
  カタログは「コンテキストマップの Published Language」と定義されているのに、マップの「OHS/PL」辺を `open-host-service`
  としてしか記録できなかった。
- **同期応答は消費者ではない。** スコープ規則で消費者を非同期の購読者と定義。自分のコマンドの応答としてイベントを読む
  コンテキストは消費者ではなくイベントは `internal` のまま。設計文書の散文と `api-style-decisions.json` / `asyncapi/` が
  食い違えば後者が勝つ。候補コンテキスト（`CTX-` に未解決 `OQ-`）は `candidate: true` を付けて消費者になれる。
- **孤児イベントは捨てずに列挙する。** モデル化された集約が宣言しないイベントは `orphan_events`（名前 + 言及元文書）に
  入れる。集約が宣言しているものを孤児にするとバリデータが拒否する。
- **auto モードは `scalardb-transaction.md` があればそこから一貫性クラスを取る。** 全コマンドを `local` に倒して集約ごとに
  `OQ-` を開く指示と矛盾していた。
- **`design-microservices` 初回実行で見つかった ADR のギャップ。** レガシー経路で根拠がすべてレポートの記録は、グラフ
  ノードに `sources` として持つ（`upstream` は空。物理専用ノードと同じ形）。`upstream` のパスはレビュー `.json` でもよく、
  日本語見出しへの `#anchor` も可。「典型的な記録」表は例示であり、先に決めたスキルが記録を書く。他スキルの設計文書との
  矛盾は Consequences と `review-consistency` の指摘であって編集ではない。`asyncapi/` が既に固定した衝突する冪等キーは
  維持して Open Item に記録。カタログ `.md` は完成させたスキルを `completed_by` に持つ。`design-microservices` に ADR の
  出力行と完了基準を追加。
- `also_writes` は `local` ケース専用と明記。再実行時は既存 `AGG-` ノードを更新。冪等キーはイベント種別ごとに一意
  （`review-risk` の指摘をスキルがそのまま写していた）。カタログ `.md` のフロントマター雛形を追加。完了基準の採番を修正。

## [0.33.0] - 2026-08-29

2026-08-29 の DDD ドキュメント一式チェック（Issue #32〜#35）で見つかった、「全 DDD 手法をカバーしている」と
「読者が完全なドキュメント一式を見られる」の間の 4 つのギャップ。

### Added
- **アーキテクチャ決定記録（ADR）**（#32）。`reports/03_design/adr/adr-NNN-<slug>.md` + `index.md`、
  機械可読なフロントマター付きの MADR 形式。`redesign` がログを開き `ADR-` プレフィックスを登録し、
  `design-microservices`・`design-scalardb` / `design-data-layer`・`design-api` が `NFR-` と同じ追記型契約で
  追記する — グラフ全体の `max + 1` で採番、他スキルの記録は書き換えず supersede する。すべての記録は
  空でない `upstream` を引用する（何も引用しない決定は好みであって記録ではない）。契約は
  `rules/architecture-decision-records.md`、バリデータは `tools/lib/adr_records.py`（24 チェックのスイート）、
  `review-consistency` が実行する。`ADR-` ノードは `work/traceability.json` に `type: decision` で追加される。
  レガシー経路でまだノードが無い場合、`upstream` は所見を述べたレポートを `reports/` パスで引用する。
- **architect manifest の `shared_outputs`。** あるフェーズが書き、後続フェーズが追記する成果物（ADR ログ、
  ドメインイベントカタログ）は、書き手すべてに `shared_outputs` として宣言する: ドキュメントとダッシュボードは
  書き手を知るが、フェーズの進捗バーには数えず `last_write` にも読まない — 後からの追記が最初の書き手の依存先を
  stale にすることはなく、成果物が存在する前に完了したプロジェクトが未完了に落ちることもない。
- **ドメインイベントカタログ — コンテキストマップの Published Language**（#33）。
  `reports/03_design/domain-event-catalog.json` + `.md`: 集約が宣言する全イベント、その発行者、どのコンテキストマップ関係で
  どのコンテキストが消費するか、消費側が依拠できる配信契約（保証・冪等キー・バージョン・進化ルール）。
  集約 manifest と `context-map.md` から導出し、新たな対話は不要。`design-aggregate` が書き、サービス分割が
  決まった時点で `design-microservices` が消費側を完成させる（`STM-` リンクと同じく後に走った方が完成させる）。
  `design-api` の `asyncapi/` は再導出ではなくこのカタログから生成する。`tools/lib/domain_event_catalog.py` が
  検証する（35 チェックのスイート）: イベントごとに宣言している発行者が 1 つ、宣言済みイベントは全て掲載、
  消費者は発行者以外の宣言済みコンテキスト、published イベントには配信契約。`review-consistency` が実行する。
- **`define-features` のユーザーストーリーマップ**（#34）。`feature-list.md` にマップを持つ — ジャーニー段階を
  バックボーン、`FEAT-` をストーリー、MoSCoW 帯をリリーススライス、Must を walking skeleton とする、統合済み
  フィーチャーの第 2 のビューであり、新たな決定はしない。

- **コミット済みの参照 DDD ドキュメント一式**（#35）。`samples/ec-monolith/expected-reports/` に、DDD 関連スキルが
  サンプルに対して生成する成果物 — ユビキタス言語、Bounded Context Canvas、コンテキストマップ、ADR 4 件、
  manifest 付きの集約 4 件、ドメインイベントカタログ、全行列付きの Order 状態遷移、ScalarDB トランザクション設計、
  ドメインストーリー、Example Map — を git-ignore 対象の `reports/` の外に置き、ドキュメント一式を推測ではなく
  目で確認できるようにした。`samples/ec-monolith/reference-set.test.py` がプロジェクトとしてステージし、
  4 つの manifest バリデータと 2 つの出力フックを実行し、`docs/ddd-coverage.md` との双方向の整合を保つ。

### Changed
- **`docs/ddd-coverage.md` が △ の 3 行に態度を決めた**（#34）。ユーザーストーリーマッピングは ○（上記）。
  Event Modeling とインパクトマッピングは理由付きで「意図的に実装しないもの」へ移動: 内容はすでに manifest・
  カタログ・traceability グラフにあり、時系列や影響の描画は固有のバリデータを持たない別ビューにすぎない。
  表から △ は消えた。

## [0.32.2] - 2026-08-28

`/architect:design-aggregate --auto` を初めて通しで走らせて（`ec-monolith` サンプル — `Order` /
`StockItem` / `Reservation` / `Payment`、不変条件 15 件）見つかった、スキル側の 3 つの穴。

### 修正
- **同一サービス内の 2 集約書き込みは `local` であり、そう宣言する。** `rules/aggregate-design.md`
  §4 は 2 集約を書くコマンドをすべて `distributed` か `saga` に分類していましたが、カウンタとそれが
  集計する明細行（`StockItem` + `Reservation`）は同一ストア上の 1 ACID トランザクションです。§4 は
  3 つのケースを定め、コマンドは `also_writes` に 2 つ目の集約を宣言し、validator はそれが manifest
  内の別集約であること（自分自身ではない）を検査、文書テンプレートは所有者と再照合を持ちます。
- **1 イベント 1 発行集約。** 2 つの集約が同名イベントを宣言すると違反 — 非所有者のコマンドは
  `none` を発行します。サンプルでは `InventoryReserved` が Inventory の両集約にありました。
- **`STM-` リンクは後に走ったスキルが記録する。** ルートの状態機械が既に存在するとき、
  `design-aggregate --auto` は `state_machine` を自分で埋め、`design-state-machine` が後続する
  場合にしか走らない書き戻しに任せません。

## [0.32.1] - 2026-08-28

0.32.0 のレビューで見つかった 6 件 — いずれも契約の片側にだけ書かれた約束でした。

### 修正
- `review-data-integrity` が Read Model / CQRS / Event Sourcing 表を読み、表にない集約を「未決」
  として指摘するように（`design-data-layer` が既にそう主張していた）。
- `map-domains` が `Core` の全 `CTX-` の `upstream` に Domain Vision Statement の `VIS-` を書き、
  `adapt-change` と `/product:review` が頼る辺がグラフに実在するように。`/product:review` は
  `VIS-` upstream のない `Core` を指摘。
- `/product:review` が Bounded Context Canvas を検査（9 部すべて、再実行で描き直した `CTX-` は
  記録された決定であること）— Canvas 節が主張していたとおりに。
- `design-scalardb` / `design-data-layer` が `reports/04_quality/nfr.md` を任意の前提として列挙し、
  純 architect 経路のフォールバックを明記（本文だけで名指ししていた）。
- DDD カバレッジの成果物チェックは SKILL.md・manifest・出力ツリーのみを宣言と数える — rule が
  パスに言及しているだけでは「宣言済み」にならない。
- `generate-test-specs` の Related Skills から `generate-scalardb-code` の重複行を削除。

## [0.32.0] - 2026-08-28

### 追加
- **集約ごとの Read Model / CQRS / Event Sourcing 採否**（#27）。`design-scalardb` と
  `design-data-layer` が集約ごとに 1 行 — リードモデル、CQRS、イベントソーシング、理由、コスト — を
  記録し、既定は「どちらも採用しない」。`review-scalardb` は行が無い集約を「未決」と読みます。
  `rules/scalardb-schema-design.md` に Event Store パターン（集約 id + sequence を OCC スコープとする
  イベント表、N 件ごとのスナップショット、冪等なプロジェクション）を追加。
- **Bounded Context Canvas**（#28）。product の `bounded-contexts.md` と architect の
  `bounded-contexts-redesign.md` の全コンテキストを同じ 9 部構成の Canvas で記述し、`CTX-` を
  handoff をまたいで部位ごとに比較可能に。`review-consistency` が完全性と id の継続を検査。
- **Domain Vision Statement**（#30）。`define-vision` がコアドメインを名指しする 1 段落を独自の
  `VIS-` 付きで書き、`map-domains` は全 `Core` 分類の upstream としてそれを引用、名指しされていない
  Core は指摘として挙げます。
- **`docs/ddd-coverage.md`**（+ `_ja`）（#31）。DDD 手法カバレッジ表をリポジトリで保守。
  `tools/docs_consistency.test.py` が、登録済みコマンドと宣言済み成果物パスのみを挙げていること、
  両言語のコマンド集合と行数が一致することを検証。
- **集約の不変条件からのプロパティベーステスト**（#29）。`generate-test-specs` は
  `aggregate-manifest.json` の不変条件ごとに、positive / negative の具体例テストと 1 つのプロパティ
  テスト — 値オブジェクトごとに検証規則を守る arbitrary、それらから合成した集約ジェネレータ、
  `violated_by` の各コマンドの適用、「不変条件が成り立つか、コマンドが拒否されるか」の 2 択のみ —
  を `reports/07_test-specs/property-test-specs.md` に仕様化します。`generate-scalardb-code` はこれを
  jqwik のプロパティとして `src/test/java/**/domain/` にルート駆動で出力し、jqwik は他の依存と同じく
  lookup で pin します。品質ゲートの stage 2 は宣言された全不変条件にプロパティテストがあることを
  要求し、covered / declared とプロパティごとの試行数を記録。`verify-implementation --gate` は両者を
  突合し、未カバーの不変条件で stage を失敗させます。

## [0.31.0] - 2026-08-28

DDD 手法カバレッジのレビューで見つかった、パイプライン*前半*の 3 つの穴を埋めました。境界づけられた
コンテキストとスキーマの間にある戦術モデル、フィーチャーとテストの間にある具体例、そして成果物が
信頼できないときに境界を見つける協調的な探索です。

### 追加
- **`/architect:design-aggregate`**（#24）。`redesign` と `design-state-machine` の間の新しい任意
  設計フェーズ。集約ごとに、ルート・内部エンティティ・値オブジェクト・両分岐の具体例を伴う不変条件・
  アクター/整合性クラス/発行イベントを持つコマンド・ファクトリ・仕様・ルートごとのリポジトリを、
  `reports/03_design/aggregates/aggregate-manifest.json`（`AGG-` ID）として出力します。
  `rules/aggregate-design.md` が「何が集約に値するか」「7 つの整形規則」「1 コマンド = 1 集約 = 1
  トランザクション」を定め、`tools/lib/aggregate_manifest.py` が規則を機械検証し、
  `aggregate_manifest.test.py`（32 checks）が検証器を守ります。`design-state-machine` は Stage 1 の
  候補をこの集約一覧から取り、`design-scalardb` / `design-data-layer`・`design-api`・
  `design-implementation`・`generate-test-specs`・`review-consistency`・`report` がマニフェストを
  読みます。
- **`/product:example-map`**（#25）。`define-features` と Gherkin の間で行うフィーチャーごとの
  Example Mapping。業務ルール（`RULE-`）、境界の両側を示す具体例（`EX-`）、セッションで決められ
  なかった問いを共有ストアの `OQ-` として記録します。`rules/product/example-mapping.md` が 4 種の
  カード・収集元・セッションの規律を定めます。`generate-test-specs` は `RULE-`/`EX-` を
  `Rule:`/`Scenario:` に、`export-backlog` は受入基準に、`design-aggregate` は不変条件の候補に、
  `define-requirements` は FR の受入基準に変換します。`ux-to-spec` と `full` プロファイルに含まれます。
- **`--mode=event-storming`**（#26）を `/product:map-domains`（Big Picture: イベント時系列、
  境界候補としての pivotal event、`OQ-` としての hotspot、`event-timeline.md` へのセッション記録）と
  両 `create-domain-story`（Process Modeling: ステップごとの event / command / actor / read model /
  policy を Process Model 節として記述）に追加。モードが変えるのはモデルの見つけ方であって書かれる
  ものではありません — 同じ成果物、同じ `CTX-`/`STORY-` ID、二重の台帳なし。
  `rules/product/event-storming.md`。`--auto` では拒否されます。

### 変更
- 登録コマンド 106（従来 104）。architect コアパイプライン 27 フェーズ、product 28 スキル。
- **実行されなかった任意の依存はブロックしない。** `design-state-machine` は `design-aggregate` に
  依存する（順序と無効化のため）ようになりましたが、`tools/lib/pipeline_status_data.py` は
  `pending` のままの任意上流を「待機中」と報告しません — 実行中または失敗時のみブロックし、再実行
  時は下流を stale にします。`/architect:pipeline` にも同じ規則を明記。
- 2 つの設計マニフェスト検証器は `tools/lib/manifest_common.py`（文書検査・サイズ上限・整合性語彙・
  読み込み/報告の枠）を共有し、コピーを持ちません。

## [0.30.2] - 2026-08-28

`/architect:design-state-machine` を初めて実案件相当（`ec-monolith` サンプルの `Order` 集約、
7 ステージ通し）で走らせて見つかった、スキル側の 2 つの穴を埋めました。

### 追加
- **生成イベントをモデル化。** 集約を生み出すコマンド（`place` / `open` / `register`）は、ガードと
  アクターを持つが `from` 状態を持たないイベントです。ガードが偽なら「集約が生まれない」のであって
  「取消済みになる」のではなく、既存の集約に届く唯一の経路は同一リクエストの再配信です。したがって
  行列のその列は API の冪等性契約だけで決まります（操作が再送を返すなら `ignore`、`allow` は
  あり得ない）。`rules/state-modeling.md` §2 に明記し、Stage 3 は質問の前に契約を引き、
  文書テンプレートに `[*]` 行を置きました。
- **競合表。** Stage 5 は、異なるアクターが同一集約に対して発火し得る遷移の組ごとに 1 行 —
  オーケストレータ対回復ワーカー、リクエスト経路対掃除ワーカー、同一キーの 2 クライアント — を作り、
  勝者と敗者の振る舞いを記します。トランザクション設計から先に解決し、そこが沈黙している組だけを
  質問します。テンプレートに表を置き、規則（§5）は「行のない組は誰も設計していない競合」と述べます。

## [0.30.1] - 2026-08-27

0.30.0 を公開当日にレビューして見つかった4件の修正です。1件は実行時に必ず失敗するもので、
残り3件は散文の主張とバリデータの実装との矛盾でした。

### 修正
- **状態機械バリデータをプラグインルートから解決。** `design-state-machine` と `review-consistency`
  が `python3 tools/lib/state_machine_manifest.py` と呼んでいましたが、このパスは本リポジトリに
  しか存在せず、利用者がスキルを動かす場所にはありません。他のツール呼び出しスキルと同様に
  `${CLAUDE_PLUGIN_ROOT}/tools/lib/…` を使うようにしました。契約テストはリポジトリ相対で
  走るため、これを捕捉できませんでした。
- **規則5の「ガードの else 分岐は行列のセル」という主張を撤回。** 行列は `(state, event)`
  につき1セルで、そのセルは `allow` です — そこではイベント自体は合法で、ガードは合法/違法
  ではなく結果を選ぶものだからです。else 分岐は遷移側の `else` に置きます。バリデータは
  もともとそう実装されていました。
- **遷移の `idempotency` を `ignore` | `reject` に限定し、意味を一つに。** `allow` は受理されて
  いましたが意味がありませんでした。コミット済み遷移の再発火は `(to, event)` 行列セルの決定で
  あり、遷移の決定ではないからです。このフィールドは**同一リクエストの再配信**（同じキー、
  再送メッセージ）への判定です — 元の結果を返すか、キー再利用を報告するか。
  `rules/state-modeling.md` §4 に区別を明記し、バリデータは `allow` を拒否します。
- **`/architect:pipeline` が `analyze-data-model` を対話駆動と呼ばなくなりました。** 対話モードも
  `--auto` もありません。optional は「失敗にせず省略可能」の意味で、`--auto` を取るのは
  `create-domain-story` と `design-state-machine` だけです。

### 変更
- manifest のフィールド契約に、バリデータとテンプレートが既に使っていた `states[].kind` と
  `matrix[].response` を記載。

## [0.30.0] - 2026-08-27

スキル1本と、それを意味あるものにする配線です。設計パイプラインがこれまで暗黙に決めていた
ライフサイクルを、状態遷移モデリングとして明示的に扱えるようにしました。
**103 スラッシュコマンド → 104。**

### 追加
- **`/architect:design-state-machine`（opus）— 状態遷移モデリング。** 散文の設計書が決して精密には
  述べない事柄を、対話で構築する任意の設計フェーズです。ライフサイクルを持つアグリゲートごとに、
  状態とその不変条件、状態間のイベントとガード付き遷移、そして**空欄のない状態×イベント行列**を
  作ります。残りの組み合わせは実行時に決まるのに任せず、`reject` / `ignore` / `defer` のいずれかを
  設計時に決めます。各遷移はアクター・整合性クラス（`local` / `distributed` / `saga`）・冪等性の
  判定を必ず持ちます。遷移はトランザクションであり、その外側で評価したガードはコメント付きの
  競合状態でしかないからです。`--auto` は既存レポートから非対話でモデルを導出し、仮定した
  セルを明示します。manifest には `redesign` の後の任意フェーズとして登録し、`STM-`
  トレーサビリティノードを発行します。
- **`rules/state-modeling.md`** — スキルが進行させる作法です。何が状態機械に値し何が値しないか、
  5つの要素型、7つの整合性規則、4種類の行列判定、楽観的並行性制御下での並行性契約、巻き戻し
  ではなく実在の状態としての補償、スイーパが駆動する時間遷移、状態カラムと遷移履歴、そして
  下流の各スキルがモデルから何を受け取るか。
- **`tools/lib/state_machine_manifest.py` と契約テスト（29チェック）。**
  `reports/03_design/state-machines/state-machine-manifest.json` が正であり Markdown はその射影
  なので、7つの規則は散文任せにせず機械検査します。初期状態はちょうど1つ、全状態が到達可能、
  宣言なきデッドエンドの禁止、`(state, event)` を共有する遷移は明示された相異なるガードを必須、
  ガード付き遷移は else 分岐を宣言、全遷移にアクターと整合性クラス、行列に未決セルなし・遷移と
  矛盾するセルなし。各テストケースは「読む分には筋が通っているが誤っている」モデルです。

### 変更
- **これまで暗黙に決めていたフェーズへモデルを供給。** `design-scalardb` と `design-data-layer` は
  状態カラム・その OCC 範囲・履歴の保存先・遷移ごとの整合性クラスを受け取り、`design-api` は
  遷移を操作に、`reject` セルを登録済み problem type に、`ignore` セルを冪等性契約に変換します。
  `generate-test-specs` には State Transition Coverage 節が加わり、網羅を測定可能にします
  （全 `allow` の発火、全ガードの両分岐、全 `reject` が契約どおりのエラー、全 `ignore` の再送）。
  `review-consistency` はバリデータを実行し、設計文書がモデルと今も一致しているか、状態名・
  イベント名がユビキタス言語にあるかを検査します。
- **`/architect:start` が `redesign` 後に状態遷移モデリングを提案**します（ドメインストーリーの
  質問と同時）。ライフサイクルの根拠を持つアグリゲートが1つもない場合は、黙って省略せず理由を
  述べて省きます。`/architect:pipeline` には `optional: true` フェーズの扱いを初めて明記しました。
  非対話モードで実行するか、根拠がなければ理由を `summary` に入れて `skipped` と記録し、
  何もないところから文書を作らない。

## [0.29.0] - 2026-08-19

4つ目のプラグイン **infra** を追加しました。独立していた `infra-design` プラグインから
マルチクラウド インフラエージェントとその知識バンドルを本リポジトリへ取り込み、
本リポジトリの規約に合わせて英語化し、契約テストに接続しています。
コーパスは 99 スラッシュコマンドから 103 になりました。

### 追加
- **`infra` プラグイン（4コマンド）。** `/infra:start`（sonnet）はトリアージです。知識バンドルを
  解決し、文書の鮮度を確認し、対象環境と対象クラウドを確定したうえで、`/infra:design`（opus）、
  `/infra:implement`（sonnet）、`/infra:review`（opus）へ委譲します。委譲時にこの4点は確定済み
  なので、モード側が同じことを再確認することはありません。スキルは product と同様に
  `skills/infra/` 配下へ入れ子で配置しています。
- **`okf-k8s-tf` 知識バンドルを `knowledge/okf-k8s-tf/` に同梱。** Terraform / Kubernetes / Helm /
  Kustomize / Argo CD / GitLab CI/CD / Docker+Cosign / Vault / External Secrets /
  Prometheus・Grafana / Kyverno を扱う OKF v0.2 文書23本です。submodule ではなく実体を同梱して
  いるのは、取得元リポジトリが**削除された**ためです。リモートは存在せず、ここにあるコピーが
  正本です。取り込み経路と、バンドルの「対象実装」区分が対象としている2コミットは
  `knowledge/OKF-K8S-TF-PROVENANCE.md` に記録しています。
- **`rules/okf-k8s-tf-bundle.md`** — 利用手順です。解決順、話題→文書の対応表、出力で混ぜては
  ならない3区分（対象実装=事実、設計指針=出典付きの推奨、確認事項=未解決）、引用記法、
  `stale_after` による鮮度、情報源の優先順位。`security/kyverno.md` の期限が他より短いのは、
  Kyverno v1.20 が `kyverno.io/v1 ClusterPolicy` の削除を計画しているためです。
- **`rules/infra/environments.md` と `rules/infra/multi-cloud.md`** — スキルが助言ではなく
  強制する2つの前提です。環境ルールが持つ被覆の非対称性がこのプラグインの誠実さの核心で、
  `local` はバンドルに一切記載がなく、`production` には**実装事実がありません**。この2つを
  `test` / `staging` と同じ確信度で語らず、そう明記します。マルチクラウドルールは L1〜L4 の
  移植性境界、クラウド対応表、非対称性（Karpenter は AWS 専用、auto-unseal KMS は3クラウドで
  権限モデルが異なる）を持ちます。
- **`templates/infra/{design-doc,env-matrix,adr,review-report}.md`** — 成果物の型です。
  `reports/` 配下に書かれるものにフックが要求する `schema_version` フロントマターの
  ブロックを、それぞれが提供します。
- **`skills/infra/infra-contract.test.py`** — 新しい散文が述べるだけで他に担保のなかった契約を
  35 チェックで検証します。ルールの解決順が `update-okf-bundle.sh` の実装と一致すること、
  対応表が挙げる文書がすべて実在し**かつ**バンドルの全文書が対応表から到達可能であること、
  23本すべてで `stale_after` がパースでき Kyverno が最短のままであること、4スキルのモデルが
  ルーターのモデル方針表と一致すること、名前を挙げたテンプレートがフロントマターを持つこと。
- **`docs/infrastructure.md`**（+ `_ja`）— 使い方ガイド。セットアップ、強制される4つの前提、
  実行の流れ、architect のインフラスキルとの境界。

### 変更
- **`tools/update-okf-bundle.sh` が `--bundle=scalardb|k8s-tf` を受け取ります。** 既定は
  `scalardb` で挙動は変わりません。`k8s-tf` は同梱バンドルを解決し、`update` は失敗でも
  無言の no-op でもなく「リモートがない」ことを報告します。更新できないバンドルは、
  更新を求められたその場でそう言うべきです。
- **`/architect:update-knowledge` に `--bundle=<name>`** を追加し、どちらのバンドルにも
  到達できるようにしました。あわせて、`knowledge/` 配下はいずれも編集禁止であることを
  明記しています。特に同梱側は、上流のない情報源を編集すると、引用可能な文書が
  検証不能なローカルの散文に変わってしまいます。
- **`/infra:*` の出力先は `reports/08_infrastructure/`**（`work/pipeline-progress.json` が
  ある場合。ない場合は対象リポジトリの `docs/infra/`）。`reports/` 配下に置くことで、
  フロントマターと Mermaid の検証フックの対象に入ります。`templates/output-structure.md` に
  このディレクトリを追記しました（既に書き込んでいた architect スキルの分を含みます）。
- **`tools/docs_consistency.test.py` の分割は8グループから9グループへ。** プラグイン1つが
  1グループです。行を足さなければ、分割は4コマンドを黙って取りこぼしていました。
  `OTHER_TOOLS` にもスキル本文に登場するインフラ CLI を追加しています。
- **`tools/omnigent/load-skill.sh` が `infra:<name>` を解決**し、名前空間を独立して一覧します。
  `infra` は `design` / `implement` / `review` / `start` という一般語と同形の名前を使うため、
  プレフィックスなしの `<name>` が `skills/infra/` に解決されることはありません。
- CLAUDE.md、README.md、AGENTS.md、OMNIGENT.md、両言語のスキルカタログを4プラグイン・
  103コマンドに更新し、新プラグインが重複する architect 側3スキルとの境界を明記しました。
  `design-infrastructure`（論理と具体）、`generate-infra-code`（`generated/` と実在の
  インフラリポジトリ）、`review-operations`（設計書とコード）。

### 備考
- infra スキルはパイプライン**ではありません**。マニフェストを持たず、`/architect:pipeline` から
  実行されず、ステータスダッシュボードにも現れません。`work/pipeline-progress.json` に
  フェーズエントリを書きません。
- 取り込み元はすべて日本語でした。SKILL.md・ルール・テンプレートはリポジトリの規約に従い
  英語へ翻訳しています。バンドル自体は**翻訳していません**。外部から取り込んだ情報源であり、
  書き換えれば、それが引用している当の情報源ではなくなるためです。

## [0.28.1] - 2026-08-18

主題が 1 つの正確性リリースです。本ツールキットは「ScalarDB のアプリケーション主導 2PC API は 3.19
で非推奨である」と全プロジェクトに伝えていましたが、これは事実ではありませんでした。この誤りは、
`samples/ec-monolith` の設計に対してツールキット自身のレビュースキルを走らせた際に検出されたもので、
その時点で既に設計判断を 1 つ動かしていました。

### Fixed
- **ScalarDB 3.19 の 2PC 非推奨という主張を、伝播していた 5 箇所すべてから撤回。**
  `rules/scalardb-2pc-patterns.md` は `TwoPhaseCommitTransactionManager`・
  `TwoPhaseCommitTransaction`・`getTwoPhaseCommitTransactionManager()` が 3.19 以降 `@Deprecated`
  であると記載していました。ピン留めした OKF バンドルの記述は逆で、
  `products/scalardb/3.19/two-phase-commit-transactions.md` は Community / Enterprise Standard /
  Enterprise Premium の全エディションで `status: stable`、v3.19.0 のリリースノートに非推奨の記載は
  なく、`scalardb-samples/microservice-transaction-sample` は現在もこの API を使用しています。
  `rules/okf-knowledge-bundle.md` §5 の優先順位ではバージョン固定バンドルがローカル要約に優先する
  ため、誤っていたのは要約の側です。「アプリケーション主導 2PC はもはや *推奨既定ではない*（共有
  クラスタと Global Transaction API が先に来る）」という正しい記述は維持しています。
- **2PC コードに対する `@SuppressWarnings("deprecation")` の要求を撤廃。**
  `skills/generate-scalardb-code/SKILL.md` と 2 つの 2PC テンプレート
  （`skills/common/references/code-patterns/{core,cluster}-crud-2pc.md`）は、2PC API を使う際に
  逸脱記録と抑制アノテーションを必須としていました。この義務は偽の前提の上にのみ成立していたため、
  生成されたプロジェクトは存在しない非推奨に対する抑制を抱え込む状態でした。**非推奨チェック自体は
  必須のまま**残し（解決済み jar への `javap`、または実際に対象とするリリースのピン留めドキュメント
  で検証する）、決め打ちの答えだけを削除しています。
- **`rules/api-error-standard.md` がアクセサ選択の根拠に偽の主張を使わないよう修正。**
  推奨は `TransactionException#getTransactionId()` のまま変更ありません（3.19 バンドルの
  `scalardb-sql/sql-api-guide.md` が記載しているため）。撤回したのは「`getUnknownTransactionId()`
  は 2PC 面の非推奨に伴い `@Deprecated`」という根拠部分です。このアクセサの状態はバンドルからは
  **どちらとも判定できない**ため（javadoc はバンドルに含まれず、識別子が 3.19 の文書に一度も登場
  しない）、本ファイルは状態について何も主張せず、リリースごとの javadoc 検証を求める形に改めました。
  「非推奨ではない」と断定することは、符号を反転させて元の誤りを繰り返すことに等しいためです。

### Notes
- 下方の v0.27.0 エントリは当時出荷した内容の記録として残しており、書き換えていません。履歴は改変
  しない方針です。
- 検出元は `/architect:review-scalardb`（指摘 SDB-101）。`okf-knowledge-bundle` の優先順位規則が
  設計どおり機能した事例で、ピン留めバンドルに接地したスキルがローカル要約と矛盾し、バンドルが
  優先されました。

## [0.28.0] - 2026-08-17

ドキュメント整合性のリリースです。`CLAUDE.md` のレビューで v0.26.0 の GraphQL 対応が反映しきれて
いないことが判明し、それを手で直す過程で本質的な問題が露呈しました — コマンド一覧が 3 箇所に存在し
ながら整合を検査するものが何も無く、リポジトリの 10 本の契約スイートはどこでも自動実行されず、誰かが
思い出したときだけ走っていました。両方を塞ぎます。

### 追加
- **ようやく CI — `.github/workflows/contracts.yml`。** すべての契約スイートが push と pull request
  で実行されます。`rules/ai-code-quality-gate.md` は以前から「強制されるのは CI 側であり、チェック
  リストとしてしか存在しないゲートこそこの文書が排除しようとしている弱点だ」と述べており、リポジトリ
  は自身のルールに違反していました。初回実行がいきなり実在の欠陥を検出しています（修正の項を参照）。
- **`tools/run-tests.sh` — 全スイートを 1 コマンドで。** スイートを**探索**します（ツリー内の
  `*.test.py` / `*.test.sh`）。新しいスイートが CI からもローカル実行からも黙って漏れることがありま
  せん。`-v` で各スイートの出力をそのまま流し、部分一致の引数で 1 本だけ実行できます。macOS の
  システムシェルには `mapfile` が無いため bash 3.2 と 5.x の双方で動作します。
- **`tools/docs_consistency.test.py` — ドキュメント分割を守る 30 チェック。** 両カタログが登録済み
  99 コマンドすべてを記述していること、署名ブロックが各 `SKILL.md` と一致すること（散文が捏造した
  フラグ・欠落・表記揺れを拒否 — `--skip-{phase}` は `--skip-<phase>` ではない）、スキルが自身に
  ついて文書化したフラグがすべて提示されていること、シェルツールをラップするスキルではそのツールが
  拒否するフラグを載せていないこと、どこにも帰属不明のフラグ言及が無いこと、`CLAUDE.md` と
  `README.md` のグループ表がグループ単位でレジストリと一致すること、拡張ティアと codegen の記述が
  `EXTENSION_PHASES` / `CODEGEN_PHASES` と等しいこと、`AGENTS.md` が全スキルを把握していること、
  カタログへのポインタが `@` インポートされないこと、日本語カタログが行順と各行のモデル階層・
  フラグ・ツール参照を保っていること。各チェックは狙ったドリフトを注入して失敗することを確認済みで、
  失敗しなかった 2 件は「緑のゴム印」にせずチェック側を修正しました。
- **`docs/skill-reference.md` / `_ja` に「呼び出しシグネチャ」節**を追加し、99 コマンド全部を収録。
  各 `SKILL.md` から抽出し、ラップ先ツールの引数パーサと突き合わせています。

### 変更
- **`CLAUDE.md` はカタログではなく地図に。** 2,634 語の Command Reference（`README.md` と
  `docs/skill-reference.md` が既に持っていた一覧の 3 つ目の写し）を、99 コマンドを分割する 8 行の
  グループ表とカタログへのポインタに置換。テストスイートを説明していた 651 語の 1 文はテーブルに。
  ファイルは 5,324 語から 3,559 語に、`@` インポートを含む常時ロード量は 15,561 語から
  12,276 語に減少しました。ポインタに `@` を付けていないのは意図的です — `@` パスは毎セッション
  に取り込まれるため、付ければこの変更は差し引きマイナスになります。
- **`README.md` の Commands** も同じグループ表とリンクに。カタログは 1 ファイル＋その翻訳 1 本に
  一本化され、重複した 3 つの一覧はなくなりました。

### 修正
- **ナレッジバンドルの欠如を設計判断の誤りとして報告しなくなりました。**
  `tools/validate-api-style-decisions.py` は OKF 参照を `if okf_root:` で守っていましたが、これは
  submodule が取得済みかどうかに関係なくパス文字列が存在すれば真になります。`--recurse-submodules`
  なしでクローンした環境では、妥当な判断に対して `native.pinned_release: ScalarDB GraphQL is not
  resolved in pinned OKF line` を報告していました。バンドルが実在するときだけ検査し、無い場合は
  不在のパスと取得方法を注記します — スキップしたことは必ず報告し、黙って飛ばしません。
- **自身のフラグを申告しきれていなかった frontmatter。** `/architect:pipeline` は `--analyze-only`
  を本文に定義しながらどのサマリーにも載せておらず `--no-scalardb` も欠落、
  `/product:generate-frontend` は動作を説明済みの `--confirm-versions` / `--no-confirm-versions` /
  `--refresh-versions` を欠落、`/architect:report-status` は `--view` と `--exec` を、
  `/product:report-status` は `--exec` を欠落していました（いずれも `tools/nexus-status.sh` は受理）。
- **`AGENTS.md` に `generate-api-code`・`generate-contract-tests`・`verify-implementation`・
  `review-api-security`・`estimate-token-cost` が未記載**でした。`CLAUDE.md` がコマンド列挙を
  やめた結果、Codex 経路ではこの 5 つがどこにも記載されない状態になっていました。
- **v0.26.0 以前からの `CLAUDE.md` のドリフト**: Code Generation ビューが `CODEGEN_PHASES` の 7
  フェーズ中 3 つしか挙げていない、「残りの architect スキル」がマニフェスト外 36 個のうち 19 個
  しか列挙せずバックログ・移行・状態系までパイプラインが実行するかのように読める、依存グラフに
  必須フェーズ `map-domains` が無い、ルール索引に GraphQL 系 3 本と product ルール群が無い、
  スキル数（~90）と product のモデル内訳（`report-status` が未計上）が古い、「フラット な
  `skills/` ツリー」の記述が意図的に未登録の移行サブスキル 10 個を無視している。
- **`README.md` の見出し数値**（95 スキル / architect 57 → 99 / 61）と、4 つあるダッシュボード
  ビューを 2 つと説明していた記述。日本語カタログの `report-status` 行にも同じ 2 ビューの記述が
  残っていました。

## [0.27.1] - 2026-08-12

### 修正
- **GraphQL 設計の完了判定が、選択された全 surface を検証するようになりました。** 検証済みの設計
  manifest を唯一の完了証跡とし、GraphQL/hybrid の canonical surface との完全一致、surface ごとの
  一意で空でない SDL と必須設計成果物への参照、孤立スキーマがないことを要求します。複数サービスの
  うち 1 サービスだけを設計しても、GraphQL フェーズは完了になりません。
- **ScalarDB ネイティブ GraphQL の例外公開に、解決可能な証跡を必須化しました。** 人による承認は
  承認者と日時を持つ承認記録へ解決され、製品・リリース・エディションは検証済みプロジェクト決定と
  ピン留め OKF リリース系列に一致し、認証・認可・監査・クエリ制限・ネットワーク分離の証跡は
  プロジェクト内のファイルと任意 anchor へ解決されなければなりません。進捗再計算にも同じ検証を
  適用し、架空の識別子による設計完了の迂回を防ぎます。
- **API スタイルレポートの生成を有界かつ atomic にしました。** 入力バイト数、ネスト深度、surface
  数、collection サイズ、出力バイト数に上限を設けました。隣接一時ファイルへの生成完了後に atomic
  置換するため、検証・生成・書き込みの失敗時にも以前の有効なレポートを保持します。

## [0.27.0] - 2026-08-12

初のフルパイプライン参照実行（EC 注文システムで CRUD / アプリ駆動 2PC / Saga / TCC / GraphQL を
ScalarDB 3.19 上で一気通貫）から抽出したガードレールです。以下の各項目は、その実行で実際に発生した
欠陥クラス — critical レビュー指摘 4 件・サービスごとのコード生成の場当たり対応・契約ギャップ 3 件 —
を符号化したもので、次のプロジェクトではレビュー段階ではなく**設計段階で**止まります。

### 追加
- **`tools/validate-cross-references.py` — 成果物横断の機械リント**を新設し、`design-api` と
  `design-scalardb` の完了条件に組み込みました。検査は 5 種: スキーマ文書のテーブル数宣言 vs 実際の
  定義数 / 手書きの操作総数 vs OpenAPI 実測 / OpenAPI で使用されているのにレジストリにない
  problem-type slug（および example の status 不整合）/ 同一ファイル内に見出しが存在しない裸の
  §参照 / namespace 名の単複ゆれ（"order" vs "orders"）。参照プロジェクトで実証済み — 実残存 19 件を
  検出後クリーン、バグ再注入の回帰テストも実施。
- **`design-scalardb` に Saga / TCC 設計チェックリスト**（該当プロセスがある場合は必須）。Saga は
  「起点トランザクションと同一 Tx での永続的起動 / 非終了 Saga の列挙インデックス / リース付き回復
  ワーカー / ピボット定義 / EXECUTED のみ抑止するべき等ガード」の 5 点、TCC・期限つき状態は
  「スイーパーのリース排他 / チェックポイント追いつき / クロックスキュー猶予 / Tx 内期限競合」の
  4 点。いずれも暗黙のままにした一度目に blocker〜major 指摘になった項目です。
- **`design-api` の Contract Verifiability チェックリストにリプレイ認可項目を追加。** クライアント
  指定のべき等/リプレイキーを持つ全操作は、リプレイ分岐の所有権述語（他者キー → 404）と
  プリンシパルスコープの記録テーブル（スキーマ相互参照付き）を宣言し、ScalarDB へ書き込む全サービスの
  OpenAPI は `transaction-status-unknown` を宣言します。
- **`design-implementation` に「Repository Exception Strategy」節を新設** — 非チェックラッパ +
  リトライテンプレートでの一点分類というプロジェクト全体の伝播戦略を設計側で規定し、コード生成器ごとの
  個別発明を終わらせます。
- **`generate-scalardb-code` に必須の deprecation チェック** — 設計がコミットする全 ScalarDB API を
  解決済みアーティファクト（javap）またはピン留めリリースノートで照合。意図的な非推奨 API 使用には
  逸脱記録・最小スコープの `@SuppressWarnings`・移行注記を義務化。
- **`review-synthesizer` に Step 5「改訂伝播チェック」** — 文書改訂で解消された指摘は、撤回された
  主張を全成果物（OpenAPI YAML・`.graphqls` 含む）で grep して残骸ゼロを確認してはじめて解消扱い。

### 修正
- **`rules/scalardb-2pc-patterns.md` が 3.19 に対して陳腐化しており、実際に誤設計を一度生みました
  （SDB-101）。**「Validate Is Conditional」を「Validate Is Version-Dependent」に書き換え: 3.19+ では
  `serializable_strategy` キーが存在せず、SERIALIZABLE なら `validate()` が必須。省略にはバージョン
  ピン付き OKF 引用を要求します。方式 3 の行には、3.19+ でアプリ駆動 2PC API 一式が `@Deprecated` で
  ある事実と、意図的採用時に必要な記録も明記しました。
- **`rules/api-error-standard.md` §3.1** が `getUnknownTransactionId()` を無条件に指示しなくなりました
  — 3.19 では @Deprecated であり、継承された `getTransactionId()` が正。ピン留めリリースに応じて
  選択する規則に変更。
- **`code-patterns/{core,cluster}-crud-2pc.md`** に deprecation チェック必須の警告を追加し、core
  テンプレートの「validate() は SERIALIZABLE + EXTRA_READ のみ」をバージョン依存の記述に修正。

## [0.26.0] - 2026-08-11

### 追加
- **Spring for GraphQL を第一級の API スタイルとして追加 — `/architect:design-graphql` と
  `/architect:generate-graphql-code`。** これまでパイプラインは仕様書に GraphQL と書くことはできても、
  それを**検証可能な契約**にする仕組みを持っていませんでした。REST には `operationId` の束縛・契約マップ・
  実行可能テスト・適合性検査があるのに、GraphQL 面は散文に落ちていたということです。GraphQL も同じ機構に
  乗り、結合キーだけが固有になります — フィールド座標 `<parentType>.<fieldName>` が resolver に 1:1 で
  束縛され、`api-contract-map.json` は REST エントリと並べて `protocol: graphql` を持ち、
  `verify-implementation` はマップの主張を信用せず**ソースから** resolver インベントリを導出します。
- **API スタイルは「ラベル」ではなく「根拠を伴う決定」になりました。** `design-api` が
  `reports/03_design/api-style-decisions.json` を書きます — 利用者に面する surface ごとに 1 エントリで、
  選択したスタイル、却下した代替案、辿れる要件 ID、セキュリティ／トランザクション／実行モデルを
  **個別のフィールド**として記録します。`api-style-decisions.md` は生成される投影であり、生成元 JSON の
  `source_sha256` を持ちます。手で書くことも、決定の情報源として読むこともありません。
  `tools/validate-api-style-decisions.py` が検証とレンダリングを担い、検証エラーはフェーズを止めます。
- **データベースが API スタイルを決めることはなくなりました。** `rules/api-style-selection.md` により、
  選択は利用者側の多様性・操作の性質・キャッシュ・ガバナンス・運用準備で決まり、`access_surface`・
  `application_framework`・`data_access`・`transaction` を**別々に**記録することが必須になります。
  「ScalarDB を使っているから」は GraphQL を公開する理由にならず、この 2 つの判断が 1 つに潰れていたためです。
- **ScalarDB ネイティブ GraphQL と Spring for GraphQL アプリケーション API を、脅威面の異なる別製品として
  扱います。** ネイティブインタフェースの公開には `approved:<decision-id>`、OKF バンドルで確認した
  製品／リリース／エディションのピン留め、そして 5 つの統制（認証・認可・監査・クエリ制限・ネットワーク分離）
  すべての参照エビデンスが必要です。**散文による承認は承認ではありません** — 構造化フィールドを欠いた
  外部公開に対し、`review-api-security` は **critical** を上げます。
- `rules/graphql-contract-fidelity.md` と `rules/graphql-security-checks.md` を追加 — SDL の nullability と
  スキーマ進化のルール、`errors[].extensions.type` によるエラー伝達、および GraphQL 固有のセキュリティ検査
  （ネストフィールドの認可、テナント単位の DataLoader キャッシュ分離、depth／complexity／alias／batch の予算、
  Subscription の origin とライフサイクル統制）を既定 severity 付きで規定します。
- `rules/api-error-standard.md` §3.2 — `UnknownTransactionStatusException` の GraphQL 実行契約。これは
  トランスポートエラーではなく**フィールド実行エラー**です。HTTP 200 に登録済み problem type URI を載せ、
  extensions は相互排他の 2 パターン — 冪等キーで保護された mutation は同一キーでのリトライ、保護されて
  いない mutation は「リトライせず突合」。ScalarDB の生トランザクション ID は extensions に出しません。

### 修正
- **Code Generation ビューが、プロジェクトが選んでいない API スタイルの生成器を提示していました。**
  REST-only プロジェクトで `design-graphql` は正しくスキップされますが、**スキップされた依存は充足扱い**の
  ため `generate-graphql-code` が実行可能になり、次コマンドとして提示されていました。GraphQL-only
  プロジェクトにおける `generate-api-code` も同様です。両者を canonical 決定に条件付けし、読めない決定は
  REST 既定に倒れるのではなく**両方を fail-closed** にしました。
- **拡張ティアはそもそも条件を表現できませんでした。** `EXTENSION_PHASES` を manifest に畳み込む際に
  `conditions=[]` がハードコードされており、フェーズが宣言した条件を黙って捨てていました — ローダーを
  直すまで上記の修正は効きませんでした。現在はすべての拡張フェーズが条件付き可能です。
- canonical 決定から導出した条件が、ダッシュボードが「プロジェクト自身の設定」として表示する `options` に
  混入しなくなりました。また、非 dict の不正な `options` は `dict()` に渡して例外を投げるのではなく
  正規化されます。
- 生成される `api-style-decisions.md` のフロントマターが `rules/output-conventions.md` に準拠しました
  （`schema_version: 1`・`phase`・`input_files`）。`generated_at` は意図的に入れていません — この投影は
  バイト単位で安定であることを assert しており、`source_sha256` がタイムスタンプの近似する対象を
  厳密に同定しているためです。
- バックログダッシュボードが、manifest の初期 `labels` ではなく**トラッカー**から納品ステータスを読むように
  なりました。GitLab / GitHub 側で状態が動いた項目が、エクスポート時のステータスのまま表示されることは
  なくなります。

### 変更
- `design-implementation`・`generate-test-specs`・`generate-contract-tests`・`generate-docs`・
  `review-api-security`・`verify-implementation`・`implement-backlog` が、REST の `operationId` と
  GraphQL のフィールド座標を並列のケースとして記述するようになり、品質ゲートの契約ステージと
  API セキュリティステージも両方を対象にします。契約テストは OpenAPI バリデータではなく、承認された
  トランスポート設計から `GraphQlTester` の種別を選択します。
- `tools/graphql_skills.test.py` が新しい契約を 68 チェックで検証します — 決定スキーマとその fail-closed
  検証、Markdown 投影の決定性とメタ文字エスケープ、外部プロジェクトから実行したときのバリデータの終了コード、
  そして各 canonical 決定がどの生成器を提示／撤回するか。
- セッション作業成果物（`todos/`・`*.local.md`）を追跡対象から外しました。

## [0.25.0] - 2026-08-09

### 追加
- **`samples/scalardb-transaction-tests/` — ScalarDB トランザクションのルールを「実行できるテスト」として同梱。**
  本リポジトリのルール 4 件は、0.24.1〜0.24.3 にかけて**テストが落ちたから**書かれた／修正されたものです。
  そのテストはセッションと共に消える一時ディレクトリに置かれていました。ルールが ScalarDB の実挙動を
  正しく記述していることの**唯一の実行可能な証拠**なので、同梱します。`./gradlew integrationTest` で、
  実 ScalarDB **3.19.0** に対する 25 テストが約 10 秒で走ります。SQLite ストレージがインプロセスで動くため、
  起動するコンテナも外部サービスも後片付けもありません。fresh clone からの実行を確認済みです。
- README は各テストクラスを、それが裏付けるルールに対応付けています — `BlindWriteProbeIT` は
  `scalardb-crud-patterns.md` の blind `Put` 挙動に、`TwoPhaseCommitIT` は `scalardb-2pc-patterns.md` の
  「参加者ごとに manager」と「プロトコル違反は unchecked」に、`SagaCompensationIT` は複合クラスタリング
  キーのルールに、`OrderTransactionIT` は `api-error-standard.md` の冪等リプライ認可ルールに。将来の
  ScalarDB アップグレードで前提が崩れた場合、ルールが静かに陳腐化するのではなく**テストが落ちます**。
- 実装を 2 つ、意図的に同梱しています。`ConformingOrderService` は TX-001〜004 を設計どおりに実装し、
  `NonConformingOrderService` はレビューが捕捉すべき違反を含みます。欠陥が検出可能であることをテストが
  assert できるようにするためです。README では後者を**テンプレートではない**と明記し、その存在理由も
  記録しました — 独立レビュアーがこれを読み、認可欠陥とトランザクション欠陥を正しく報告し、
  **書き込みがそもそもコミットできないことには気づかなかった**、という経緯です。

### 変更
- 元になった一時プロジェクトより意図的にスコープを絞りました。Spring・HTTP レイヤー・OpenAPI 契約は
  外してあります。いずれもトランザクションの検証には不要であり、**その不在自体が論点**です — 契約テスト層は
  レスポンスの「形」を検証するもので、構造上ここの挙動には一切到達できません。品質ゲートの stage 3 は
  stage 4 の代わりになりません。
- `CLAUDE.md` に、本スイートが CLI テストセットの外にある理由（依存解決にネットワークが必要）と、
  実行すべきタイミング（ScalarDB のバージョン更新後）を明記しました。

## [0.24.3] - 2026-08-09

### 修正
- **ScalarDB の API の罠 4 件 — 読むのではなく「実行して」見つけたもの。** 品質ゲートは stage 4 として
  統合テストを挙げ、「設計が要求するトランザクションシナリオ（OCC 競合、2PC 障害、Saga 補償）を含む」と
  規定しています。本リポジトリはこれまで一度もそれを実行していませんでした。今回実行しました — 実 ScalarDB
  **3.19.0** に対する 25 テスト（SQLite ストレージ、インプロセス、コンテナ不要）で、参照トランザクション設計の
  TX-001〜TX-004 を実行しています。以下の欠陥はいずれも契約テストからも独立した静的レビューからも見えず、
  **コードを実行した瞬間に現れました**。
- **先行 `Get` の無い `Put` は INSERT です。** Consensus Commit は「そのトランザクションがレコードを
  読んだか」で insert/update を判別し、読んでいなければ暗黙の `PutIfNotExists` を付けます。したがって
  既存レコードへの blind `Put` は `put()` ではなく **`commit()`** で
  `DB-CORE-20013: The record being prepared already exists` として失敗します。これは**競合エラー**として
  出るため輻輳のように読め、しかもリトライでは決して解消しません。既存の「Put は非推奨」節は代替手段を
  書いていましたが、**何が壊れるか**を書いていませんでした。`scalardb-crud-patterns.md` に挙動表と
  read-before-write ルールを追加し、`verify-implementation` 軸 2 が検査するようにしました。
- **`join(txId)` は呼び出した manager 内で解決されます。** トランザクションを開始した manager 自身に
  対して呼ぶと**同じトランザクション**が返るため、2 回目の `prepare()` が
  `The transaction is not active. Status: PREPARED` で失敗します。本番では各サービスが自前の manager を
  持つため見えません。刺さるのはテストと単一プロセスのプロトタイプで、manager 1 つに変数 2 つ、が自然な
  書き方だからです。その書き方の 2PC テストは **2PC を全く検証していません**。
- **2PC のプロトコル違反は unchecked です。** `prepare()` 前の `commit()` は `IllegalStateException` で
  あって `TransactionException` ではありません。`catch (TransactionException e)` と書いたハンドラは
  これを一切見ないため、未処理の 500 とフレームワークのエラーページとして漏れます — マッピングの穴で
  あると同時に §4 の detail 漏洩問題でもあります。トランザクションの結果ではなくサーバ側の欠陥なので、
  `transaction-failed` ではなく汎用の内部エラーに割り当てます。
- **`clusteringKey(...)` は追加ではなく上書きです。** カラムごとに連鎖させると最後の呼び出しだけが残り、
  実行時に `DB-CORE-10021: The clustering key is not properly specified` で失敗します。複合クラスタリング
  キーは、宣言順に全カラムを載せた**1 つの `Key`** です。

### 変更
- `rules/ai-code-quality-gate.md` に、**stage 4 は stage 3 と 8 では代替できない**理由を明記しました。
  契約テストはレスポンスの「形」を証明し、適合レビューは「コードが設計どおりを述べているか」を証明します。
  どちらも実エンジンに対してトランザクションを実行しません。blind `Put` の欠陥がその実例です — 合法な
  Java で、レビューは通り、コミットできません。
- `generate-test-specs` は、トランザクションシナリオを契約仕様ではなく**統合仕様**に配置するようになり、
  参加者ごとに manager が必要である旨も明記しました。生成される 2PC シナリオが空振りしないためです。

### 確認できたこと
通過したシナリオは、主張ではなく**実証**になりました。先に読んで後にコミットしたトランザクションが敗北し
勝者の書き込みが残ること。並行 confirm がシリアライズされ、ちょうど 1 つだけ成功し、敗者は静かに二重適用
せず綺麗に失敗すること。サービス側リトライが解消可能な競合を吸収すること。参加者の `prepare()` が競合すると
全参加者がロールバックし、在庫未確保のまま注文が commit されないこと。部分 prepare が何も残さないこと。
後続ステップ失敗時に Saga が逆順で補償すること。再配送された補償が在庫を水増ししないこと。そして補償を
持たないステップが効果を残すこと — 設計レビューが捕捉すべき欠陥そのものです。

Saga のテストは ScalarDB のローカルトランザクション上で Saga の**パターン**を実行しています。
ScalarDB Saga（製品、3.19.0-alpha.1）そのものではありません。本プロジェクトの依存には含まれていません。

## [0.24.2] - 2026-08-09

### 修正
- **独立レビュアーが検証層に見つけた 4 件の欠陥。** 0.24.1 の e2e 実行には構造的な弱点が 1 つありました。
  コードを生成したのと同じエージェントがそれを検証していたため、**判断を要する検査**（BOLA 検出、
  トランザクション適合）は実際には一度も試されていませんでした。実 Java 17 / Spring Boot サービスに対する
  2 回の Codex 実行でこれを埋めました。1 回目は `rules/api-security-checks.md` に基づく API セキュリティ
  レビュー、2 回目は 2 つの候補実装（設計どおりのものと、違反を仕込んだもの）に対する**盲検**の
  トランザクション適合レビューです。盲検では仕込んだ違反をすべて検出し、設計に近い方の候補を正しく選び、
  7 つの検査項目のうち「判定不能」は 0 件でした — これが不足していた証拠です。同時に、**設計どおりに
  書いた方**の候補にも 4 件の欠陥を見つけ、うち 2 件はコーディングミスではなく**ルールの穴**でした。
- **冪等リプライ経路は認可経路であり、それをどこにも書いていませんでした。**
  @rules/api-error-standard.md §5 は記録を「どこに書くか」だけを規定し、「誰が読み返せるか」を規定して
  いませんでした。素直に実装すると、まず保存済み記録を確認して早期 return するため、リプライが所有権読み取り
  より**前**に来ます。結果、その早期 return だけが認可のない経路になります。記録が `(tenant_id, key)` キーだと
  さらに悪化し、テナント内の全呼び出し元が読めるため、他人の key と order ID を持つ呼び出し元がその注文の
  結果を読み出せます。本リポジトリ自身の参照実装がまさにこれで、隣には正しい非リプライ経路がありました。
  §5 に明記し、`api-security-checks.md` で **critical** な API1 findings として検査します。あわせて
  「非リプライ経路が正しいことは、リプライ経路について何も証明しない」と警告を追加しました。
- **`verify-implementation` は「分割されたトランザクション」を見て「欠落したトランザクション」を
  見ていませんでした。** 設計は TX-003 が order + inventory + payment に跨ると述べ、実装は order しか
  書いていませんでした。そのコードは綺麗に見えます（1 トランザクション、正しいリトライ、正しい catch 順）。
  そして欠落は、それを起こしたコード自身に何の痕跡も残しません。軸 2 は設計のトランザクションごとの参加者
  リストを読み、各参加者が実際に書かれているかを検査するようになりました。critical 扱いです — システムの
  他の部分と矛盾する状態をコミットするため（在庫を確保しないまま確定した注文）。
- **生成されるインベントリ検証が数え落としていました。** 独立実行は未宣言 operation を 10 件と数え、
  検証は 6 件と報告しました。原因は 2 つで、いずれも `generate-contract-tests` に明記しました。パス変数は
  **位置ベース**で正規化すること（`{id}` と `{orderId}` は同じ「形」であって同じ「パス」ではない）、および
  比較キーは `(method, path)` であること（パスのみで重複排除すると、同一ルートの `GET` と `POST` が 1 件に
  畳まれます）。
- **`UnknownTransactionStatusException` には専用のアクセサがあります。** この例外が定義しているのは
  `getUnknownTransactionId()` です。ScalarDB 3.19 では継承した `getTransactionId()` も同じ値を返すため、
  誤った方でもコンパイルが通りテストも通ります。習慣で使い回さず、pin したリリースに対して解決するようにしました。

### 確認できたこと
独立実行は、0.24.1 で修正済みの 2 件（実ルートが到達可能なのに unmapped を空と主張する契約マップ、
メソッドセキュリティ未有効化で無効化された `@PreAuthorize`）を**再発見**しました。あれらがエージェントの
自己採点による産物ではなかったことの裏付けです。違反を仕込んだ候補についても、仕込んだ内容を項目単位で
言い当てました。もっとも重要なのは居心地の悪い方の結果です — **設計と一致していると作者が信じていた実装に
critical 3 件が残っていました。** それこそが `verify-implementation` の存在理由です。

## [0.24.1] - 2026-08-09

### 修正
- **0.24.0 のパイプラインを初めて実際に通した結果、判明した 6 件の欠陥。** 0.24.0 は契約整合性チェーンを
  一度も実行しないまま出荷していました。Java 17 / Spring Boot 3.2.5 の実サービスに対し
  `design-api` → `design-implementation` → `generate-api-code` → `generate-contract-tests` →
  `verify-implementation --gate` を実行し、ScalarDB 3.19.0 と実際の validator ライブラリでコンパイル・
  テストしたところ、4 箇所が即座に破綻しました。
- **契約マップに scope の概念が無く、自分自身のチェックを通しながらエンドポイントを隠せてしまいました。**
  brownfield ツリー（本ツールキットが対象とするレガシー刷新のケース）では Controller が契約より先に存在し、
  生成パッケージだけを走査した生成器は実ルートが未宣言のまま `handlers_without_spec_operation: []` を
  出力します。実行結果はまさにそれで、**`/api/admin/users` を含む 6 本の到達可能なルート**が契約にも
  マップにも現れませんでした。マップは `scope` と、ツリーから導出した `out_of_scope_handlers` を宣言する
  ようになり、到達可能な全ルートがいずれかのリストで説明されることを必須とします。スコープ外エントリも
  finding として報告されます — この欄は「見落としが許容された」ではなく「見落としが名指しされた」ことの記録です。
- **生成されたインベントリ検証がコードではなく契約マップを読んでいました。** マップが誤っているときにこそ
  通ってしまう — 落ちるべきまさにその場面で。現在はソースツリーから導出して仕様と突き合わせます。
  ルール側にも「マップ単体からカバレッジを結論してはならない」と明記しました。
- **既定の契約テスト座標が存在しませんでした。** Atlassian は同ライブラリを
  `com.atlassian.oai:swagger-request-validator-*` と `com.atlassian.oai:openapi-request-validator-*` の
  両系統で公開しており、MockMvc 連携は `-mockmvc` モジュールです。どちらの系統にも `-spring-mvc` という
  artifact は存在せず、記載どおりに pin すると解決不能な依存になります。
- **同ライブラリの現行 major は Java 21 ビルドで、Java 17 サービスにコンパイルできません**
  （`bad class file … version 65.0 … should be 61.0`）。`2.x` 系が Java 8 baseline で正しい pin です。
  座標解決時にグループディレクトリを列挙し、artifact の JDK baseline をプロジェクトのターゲットリリースと
  照合することを必須にしました — @rules/dependency-versions.md §2 の文字どおりの適用です。
- **契約テストが git-ignore 配下の `reports/` から仕様を読んでいました。** 作者の手元では緑、fresh checkout
  の CI では赤になり、契約ステージが作者以外の全員で失敗します。仕様は
  `src/test/resources/contract/openapi/` に固定してクラスパスから読み込むようになり、
  `verify-implementation` がそのコピーと設計側の原本を比較するため、コピーの陳腐化が不可視のドリフトに
  なりません。
- **`gitleaks detect` が非 git ツリーで「0 commits scanned … no leaks found」と報告し exit 0 を返しました** —
  何も検査していないクリーンスキャンで、ゲートはこれを証跡として記録してしまいます。同じツリーを dir モードで
  走査すると 239 KB を検査して leak を 1 件検出しました。ゲートはステージごとに**カバレッジ**の証跡を要求し、
  カバレッジ 0 は `passed` ではなく `not-configured` として扱います。1 クラスもマッチしないテストフィルタ
  （緑のタスクでありゲートされていないビルド）にも同じ規則が適用されます。
- **`generate-api-code` がコンパイルできないコードを「完了」と報告していました。**
  `@AuthenticationPrincipal Jwt` を使う Controller を出力しながら
  `spring-boot-starter-oauth2-resource-server` を追加していませんでした。現在は自身の出力が要求する依存を
  追加し、コンパイルを実行してからコマンドと exit code を実行サマリに記載します。
- **`verify-implementation` が、宣言された認可制御が「存在する」だけでなく「実際に効いている」かを
  検査するようになりました。** `@PreAuthorize` はコンパイルが通り、制御のように読め、メソッドセキュリティが
  有効化されるまで何もしません。アノテーションとしてしか存在しない認可は finding として報告されます。

### 確認できたこと
同じ実行が、正しかった部分も裏づけています。RFC 9457 ハンドラは実 ScalarDB 3.19.0 に対してコンパイルが通り、
`UnknownTransactionStatusException` 分岐は冪等キー保護 operation で 503 + `Retry-After` + `transaction_id`
+ `retry_after_ms` を返します（契約テストで assert・PASS）。非所有オーダーの 404（403 ではない）、レスポンス
からの機密フィールド非露出、スキーマ由来バリデーションの Problem Details + `errors[]` も同様に PASS。
ゲートは stage 1 でコンパイル失敗を、stage 3 でインベントリ欠落を捕捉しており、設計どおりに機能しています。

## [0.24.0] - 2026-08-09

### 追加
- **OpenAPI ドキュメントが「レポート」から「強制力のある契約」になりました。** 本ツールキットは API 設計は
  十分に行える一方、そのコードが設計どおりかを判定する手段を持っていませんでした。`design-api` が OpenAPI を
  出力し、`generate-scalardb-code` が Entity・Repository・ドメインサービスを出力する — その間のレイヤーを
  生成するものも検査するものも存在せず、Controller も DTO もバリデーションもエラーハンドラも生成されず、
  コードと設計を突き合わせる工程もありませんでした。AI が書いたコードではここが決定的です。モデルは
  「正しいコード」よりはるかに高い確率で「もっともらしいコード」を生成し、もっともらしいコードは
  レビューを通過してしまうからです。新規ルール 4 本と新規スキル 4 本でこれを塞ぎます。
- `rules/api-contract-fidelity.md` — 仕様ファイルが契約そのもの。コードは契約を超えてはならず、矛盾しても
  ならず、振る舞いを変えるときはまず仕様を変更します。`operationId` が結合キーとしてハンドラと 1:1 で束縛され、
  `reports/06_implementation/api-contract-map.json` に記録されます（`unmapped` 配列は決して省略しません）。
  コードと契約が食い違ったときは**報告し、勝手に整合させません** — `generate-docs` が既に守っている原則と同じです。
- `rules/api-error-standard.md` — RFC 9457 Problem Details を唯一のエラー表現とし、プロジェクトごとの
  problem type レジストリをトレーサビリティグラフや Open Questions ストアと同じ規律で割り当てます。ScalarDB
  例外のマッピングもここに含み、特に影響が大きいのが `UnknownTransactionStatusException` の扱いです。単純な
  500 でも一律の 503 でもありません。commit は成功しているかもしれないため、冪等キーで保護された operation の
  場合**のみ** 503 + `Retry-After`、そうでなければ retry ヒントなしの 500 と「retry せず突合せよ」を明示した
  `detail` を返します。
- `rules/api-security-checks.md` — OWASP API Security Top 10 (2023) を具体的なチェックに落とし、各項目を
  「設計の問い」と「コードの問い」に分割しました（両者は独立に失敗するため）。加えて、汎用スキャナには
  見えないマルチテナントおよびトランザクション境界のケースを含みます。
- `rules/ai-code-quality-gate.md` — 人間にレビューを依頼する前の 8 段ゲート。チェックリストではなくゲートたら
  しめているのは、**各段が必ず証跡を残す**点です（exit code 付きのコマンド、または findings を返した Skill）。
  未実行の段は理由付きで記録します。省略された段は「合格した段」に読めてしまい、ゲートが無いより悪いためです。
  FAIL は PR 上の注記ではなく、レビュー引き渡しそのものをブロックします。
- `/architect:verify-implementation` — 設計 ↕ コードの差分検出エンジン。4 軸で検査します。契約（ハンドラ束縛、
  DTO の形、ステータスコード、エラー表現、不定コミット分岐）、トランザクション（設計が 1 トランザクションと
  した処理が実際に 1 つか。retry、catch 順序、Saga 補償、2PC の完全性）、セキュリティ
  （`review-api-security --mode=code` に委譲）、要件（`FR-` → コード、受入基準 → テスト）。本スキルは何も
  編集しません。食い違いは双方を提示するだけで、どちらが誤りかの判断はユーザーのものだからです。`--gate` で
  8 段ゲートを実行します。
- `/architect:review-api-security` — OWASP API Top 10 の 3 次元レビュー。並列設計レビューの **6 本目**として、
  また `--mode=code` でゲートのセキュリティ段として動作します。2 つのモードは冗長ではありません。正しい
  ゼロトラスト設計を持ちながら、パスパラメータを信用する Controller を出荷することはあり得るからです。
- `/architect:generate-api-code` — 契約から API レイヤーを生成。`operationId` ごとに Controller メソッドを 1 本、
  DTO 名は `components/schemas` のキーから、Bean Validation はスキーマ制約から**導出**（選択ではなく）、
  DTO↔ドメインのマッパーは明示的に生成します（リクエストボディを Entity に直接バインドするのが mass assignment
  欠陥そのもののため）。RFC 9457 ハンドラは不定コミット分岐を含みます。仕様が宣言していないものは生成せず、
  契約に不足があれば「もっともらしい推測」で埋めずに停止して確認します。ScalarDB 非依存です。
- `/architect:generate-contract-tests` — 契約を実行可能なアサーションに変換。インプロセス OpenAPI 検証
  （既定は `swagger-request-validator` + `@WebMvcTest`、Schemathesis / Pact / ArchUnit は記録されたオプトイン）、
  Problem Details 適合、認可、冪等性、不定コミット契約、そして unmapped が 1 件でもあれば落ちるインベントリ
  アサーション。期待値は必ず仕様から取り、実装からは決して取りません。実装に合わせて書いたテストは実装が
  何をしても通ってしまうためです。

### 変更
- `design-api` を Contract Verifiability チェックリスト中心に全面改稿 — 名前付きスキーマ、全ステータスコードの
  宣言、制約はスキーマに記述、operation ごとの認可 / 冪等性 / タイムアウト。各項目は「それが無いと特定の下流
  チェックが不可能になる」から存在します。新規出力は `problem-types.md` と `operation-contracts.md`。
- `design-implementation` に `api-layer-spec.md` を追加 — `operationId` ごとのハンドラ、DTO、バリデーション、
  マッパー、トランザクション境界、認可の実施点。
- `generate-test-specs` は契約テストを独立カテゴリ化して `contract-test-specs.md` を出力し、選択したテスト
  スタックを記録します（`generate-contract-tests` が記録どおりに生成するため）。
- `design-security` にオブジェクトレベル認可、テナント分離モデル、OWASP API Security Top 10 マッピングを追加。
  コード時レビューが白紙ではなくベースラインを持って始められます。
- `generate-scalardb-code` にパッケージ境界を明記 — 本スキルは `domain/` と `infrastructure/`、`api/` は
  `generate-api-code`。ドメイン生成器から Controller を出すと、束縛されない 2 つ目の API 面が生まれます。
- `generate-infra-code` が品質ゲートの CI ワークフローを出力。セッション内ゲートは高速フィードバック、CI は
  実際に強制される側なので、生成ジョブに `continue-on-error` や `|| true` を付けることを禁止しています。
- `implement-backlog` に Step 5c、`review-issue` に Step 2b を追加。人間に見てもらう前にゲートを実行し、
  ブロッキングな `VER-` / `ASEC-` findings を `[B]` として既存の自動 fix ループに流します。
- コード生成の後続順序が **生成 → テスト → ドキュメント → 検証**に、並列設計レビューが 5 視点から 6 視点に
  なりました。README、`CLAUDE.md`、`AGENTS.md`、`OMNIGENT.md`、両言語のスキルリファレンスと
  getting-started ガイドを更新しています。

## [0.23.3] - 2026-08-09

### 変更
- **ユーザー向けドキュメントが、コードが強制している内容のハンドオフを記述するようになった。**
  0.23.0〜0.23.2 で product→architect 境界は実際の不変条件を持つ契約になったが、`README.md` と
  getting-started は依然としてそれを 1 本の矢印としてしか示しておらず、読み手には `NFR-` ID が
  そのまま再利用されること、`FEAT-`→`FR-` のリンクが記録されること、3 つの項目が**意図的に**
  引き継がれないこと、以降両パイプラインが `work/` 配下の 3 ファイルを共有することを知る手段が
  無かった。README に「引き継がれるもの / 意図的に引き継がれないもの」の表を、getting-started
  （英日）に「ハンドオフで実際に起きること」の節を、architect インプット要件ガイド（英日）に
  見落としやすい 3 点 — 部分実行でもハンドオフは成立する、Open Questions のストアは 1 つ、
  新しい ID はグラフから採番する — を追加した。契約そのものは `docs/design.md` のままで、
  これらはそこへの入口。

## [0.23.2] - 2026-08-09

### 修正
- **`NFR-` ID が 2 つのスキルによって別々の要件に二重採番され得た。** `docs/design.md` §1.5 は
  architect 由来の `NFR-` ノードを作れと言うだけで採番元を書いておらず、product が既に `define-nfr` を
  実行済みであることを暗黙に前提していた。しかし常にそうとは限らない — `--profile=mvp` で止まった
  product 実行が `define-requirements` にハンドオフすると、`NFR-` が 1 つも無いので `NFR-001` を採番し、
  その後 product パイプラインを再開すると `define-nfr` も `NFR-001` を採番する。full プロファイルの
  end-to-end 実行でまさにこれが発生した — 両プラグインが共有する単一グラフの中に、1 つの ID が 2 つの
  意味を持つものが 6 件。§1.5 に rule 4 を追加した: 新しい ID は接頭辞ごとにグラフ全体の `max + 1` から
  採番する（`OQ-` と同じ規則）。§1.5 の検証項目にも「同一 ID が 2 回現れないこと」を追加したので、
  再発は `review-consistency` と `/product:review` が検出する。

## [0.23.1] - 2026-08-09

### 変更
- **Open Questions ストアを 1 ファイルに統一し、architect の成果物はそのビューになった。** プロトコルは
  `work/context.md` § Open Questions と `reports/00_requirements/open-questions.md` の 2 つを
  ストアとして挙げていたが、どちらが正典かも、ID をどこから採番するかも書いていなかった。通常の
  ハンドオフ実行で到達し得る帰結が 2 つある — 次の ID をどこから採るかの規則が無いため product と
  architect が別々の質問に同じ `OQ-004` を割り当て得ること、そして片方で記録した回答がもう片方に
  届かず、architect が解決した質問が後の product 再実行では `unasked` のまま残ること。
  `work/context.md` をプロジェクト全体の**唯一の**ストアとし、
  `reports/00_requirements/open-questions.md` は 2 つ目の情報源ではなくそこから描画される成果物に、
  新しい ID はストア全体の `max(OQ-###) + 1` とした。`work/traceability.json` が既に従っていた
  「2 つ目のファイルを作らない」という規則を、境界を双方向に越える質問にも適用した形。

## [0.23.0] - 2026-08-09

### 追加
- **ID 接頭辞の名前空間が「記述」ではなく「宣言」になった。** 2 つの `skill-dependencies.yaml` の各
  phase に `id_prefix` を追加し、manifest を「どのスキルがどの接頭辞を発行するか」の正典にした。
  従来は各 SKILL.md の散文にしか存在せず、衝突も宣言漏れも検出できない状態で、実際に 3 つのスキルが
  接頭辞を一切宣言していなかった。`tools/lib/pipeline_status_data.test.py` が、
  `work/traceability.json` に追記する全スキルが接頭辞を宣言していること、その接頭辞を自身の SKILL.md
  で実際に使っていること、同一 manifest 内で重複がないことを assert する（`NFR-` だけが manifest を
  またぐ意図的な主張 — §1.5 のキャリーオーバー — であることも明示的に検査する）。
- **レジストリの phase エントリが自分のパイプラインを名乗るようになった。** `work/pipeline-progress.json`
  の各エントリが `"plugin": "product" | "architect"` を持つ。`init-output` と各オーケストレーターの
  `in_progress` スタンプ時に書き込まれる。1 つのレジストリを両パイプラインが共有し、phase を bare 名で
  キーにしているため、両 manifest が定義する 4 つの名前については、このフィールドだけが「誰のエントリか」
  を示す。`tools/nexus-status.sh` はこれを読んで一意に解決し（もう一方のパイプラインのラベルが付いた
  エントリは、何と書いてあってもこの phase の状態ではない）、フィールドが無い場合のみ output の裏付けに
  フォールバックする。

### 修正
- **ScalarDB を使わないプロジェクトが 3/4 出力のまま止まらなくなった。** architect manifest は
  `scalardb-applicability.md` を `define-requirements` の無条件 output に並べていたが、スキルは
  ScalarDB が関係する場合にのみこれを書く。そのため ScalarDB 不使用のプロジェクトでは出力バーが
  永久に埋まらず、「書くものが無かったフェーズ」ではなく「未完了のフェーズ」に見えていた。manifest に
  `conditional_outputs`（`"<条件>:<パス>"`）を追加し、ダッシュボードはプロジェクトのオプションが条件を
  満たす場合にのみカウントする。
- **バリデーションゲートが「誰のものか」を示すようになった。** ゲートは **product** パイプラインのもので、
  architect タブにも意図的に表示している（要件が未検証の前提の上にあることは architect が知るべき情報
  だから）。しかしラベルの無い `gate: no-go` が architect のツリー上に出ると、architect 自身の判定と
  読めてしまう。product ビュー以外では `Product gate: no-go` と表示するようにした。
- **ハンドオフ検知がディレクトリではなくファイルを見るようになった。** `/product:init-output` は
  `reports/01_ux/domain-stories/` と `reports/02_spec/ui-mocks/` を空で作るため、ディレクトリ存在
  テストは、フェーズが 1 つも実行されていない初期化済み product プロジェクトでもハンドオフを報告して
  いた。`/architect:start`・`/architect:pipeline`・`define-requirements`・`AGENTS.md`・`OMNIGENT.md`
  を修正。`define-requirements` はさらに、どの product 成果物が見つかり、どれが無かったかを出力に明記する
  （部分的な product 実行はキャリーオーバーできる内容を変えるため）。
- **`AGENTS.md` と `OMNIGENT.md` が、自分が駆動しているハンドオフを記述するようになった。** 本リポジトリは
  同じスキル群を 3 つのオーケストレーターで動かし、各エントリドキュメントの同期を要求しているが、
  product→architect ハンドオフに言及していたのは `CLAUDE.md` だけだった。Codex と omnigent ローダーには
  検知規則も成果物マッピングも与えられておらず、決定的に、`pipeline-progress.json` /
  `traceability.json` / `context.md` が両パイプラインの共有物であり加算的に書かねばならないことが
  書かれていなかった。両者に検知グロブ、`docs/design.md` §1 契約への参照、`plugin` スタンプと曖昧な
  4 つの phase 名を含むファイル別の加算規則、`adapt-change` の「報告して止まる」境界を追加した。
  `CLAUDE.md` にも同じ共有状態の段落を追加。
- **3 つのスキルが、下流から参照できないノードを書いていた。** `research-landscape` /
  `generate-ui-mock` / `generate-frontend` は、どの ID 接頭辞で書くかを述べないままトレースグラフに
  追記していた。これは 2 つの連鎖を実際に切っていた — `/product:adapt-change --type=market` は
  market-landscape ノードから影響範囲をシードするが、そのノードに ID が無くシードできない。
  journey → story → **画面** → feature の連鎖も、画面の ID が無いため画面のところで切れていた。
  それぞれ `MKT-` / `SCR-` / `PG-` を発行するようにし、`define-features` は各 `FEAT-` の由来である
  `SCR-` を引くようにした。これで下流で導出される `FR-` が最後まで遡れる。生成された React
  コンポーネントは独自のノードを作らない — それは design-system の `CMP-` の実装なので、2 つ目の ID で
  重複させず当該 `CMP-` ノードに記録する。
- **トークンコストがパイプライン境界を越えて合算されなくなった。** `work/token-usage.json` もレジストリと
  同様に bare 名キーだったため、`map-domains`（および `design-api` / `create-domain-story` / `report`）の
  product と architect の費用が、どちらのビューも主張できない 1 つのバケットに蓄積されていた。
  `hooks/record_token_usage.py` はこの 4 つをレジストリエントリの `plugin` フィールドから取って
  `<plugin>:<phase>` で記録するようになった。ダッシュボードはバケットを自分のパイプラインにのみ計上し、
  もう一方のものはそのタブに任せ、名前空間化されていない旧バケットは「開いているタブ」に付け替えるのでは
  なく未割当として報告する。その他の phase 名は従来どおり bare で記録される。
- **`/product:adapt-change` が architect 境界で「未定義」ではなく「停止」するようになった。**
  ハンドオフ後はトレースグラフに architect のノードが含まれるため、影響範囲の閉包は設計上そこに到達するが、
  スキルはその扱いを何も述べていなかった。確定した影響集合をノードの所有者で分割し、product 側のみを
  再実行し、影響を受ける `FR-` / `NFR-`・所有スキル・対処コマンドを列挙した `## Architect-Side Impact`
  セクションを書くようになった。architect 成果物は書き換えない — product 側の変更は product 仕様を
  改訂する根拠ではあっても、バックログ項目や出荷済みコードが依存する要件文書を書き換える権限ではない。
  `docs/design.md` §7.5 が新しい契約で、§7.2 は再実行が越境するかのような記述をやめた。
- **`/architect:pipeline` のハンドオフ検知が `define-requirements` の読む範囲と一致した** —
  `/architect:start` で既に修正したのと同じグロブ不一致。
- **`init-output` がもう一方のパイプラインの状態を破棄しなくなった。** `/architect:init-output`
  と `/product:init-output` の双方を明示的に加算的（additive）な動作に変更した。既存の
  `work/pipeline-progress.json` は全 phase を `pending` で再登録するのではなくマージし、設定済みの
  `options`（特に user が選んだ `output_language`）を保持し、`work/context.md` と
  `work/traceability.json` は存在しない場合にのみ作成する。product→architect のハンドオフでは
  `/architect:start` が `/architect:define-requirements` の直前に `init-output` を実行するが、
  従来の `init-output` は `work/context.md` を「空ファイルとして作成」していたため、直後の
  `define-requirements` が読む product 側の Open Questions 表を消去していた。
  `/product:init-output` も同様に `work/traceability.json` を切り詰めなくなった。これは architect が
  `FR-` / `NFR-` ノードを追記する唯一のプラグイン横断トレースグラフである（`docs/design.md` §1.5）。
- **両パイプラインが定義する phase 名を、片方の記録だけで「完了」と読まなくなった。**
  `map-domains`・`design-api`・`create-domain-story`・`report` は両方の manifest が定義しており、
  進捗レジストリは phase を bare 名でキーにしているため、**product** 側の `completed` が
  **architect** 側の完了として表示され、`/architect:pipeline --resume-from` ではスキップされる
  状態だった。`tools/nexus-status.sh` は、当該 phase 自身の宣言 output が実在して裏付けが取れる
  場合にのみそのエントリを信頼し、そうでなければ実ファイルから状態を導出して `shared-name`
  ドリフトとして報告するようになった（実行中の `in_progress`、およびプロジェクトが実際に指定した
  skip は対象外）。`skills/common/progress-registry.md` にオーケストレーター向けの同じ規則
  — 曖昧なエントリは満たされたと見なす前に実ファイルで確認する — と、共有レジストリが要求する
  加算的書き込み規則を明記した。`init-output` は該当エントリを `warnings[]` にも記録する。
- **`/architect:start` のハンドオフ検知が `define-requirements` の読む範囲と一致した。**
  検知は `reports/02_spec|03_domain|04_quality` しか見ていなかったため、早期に停止した product
  実行（`--profile=mvp` は `reports/00_core/` のみ出力）が、まさにそれを消費するスキルによって
  「product 成果物なし」と宣言され得た。両者の集合を一致させた。

### 変更
- **Open Question は「記録」ではなく「質問」するようになった。** `TBD` を書き得るすべての
  スキルが、新しい `rules/open-questions.md` の手順に従う。自身の入力で解決できない不明点は
  `AskUserQuestion` で利用者に問う — 文脈から導出した 2〜4 個の候補回答を、それぞれ「選ぶと
  下流が何が変わるか」とともに提示する — そのうえで、利用者が保留したもの・その場では答え
  られないもの・`--auto` で質問しなかったものだけが `TBD` になる。従来は不明点がそのまま
  「`TBD` として Open Questions に記録」へ直行しており、一度クリックすれば答えられた質問まで、
  誰も開き直さないレポートの中へ先送りされていた。
- **選択肢に収まらない部分はフリーテキストで答えられる。** スキルは「Other」選択肢を自作せず
  （ハーネスが必ず付与し、それが自由入力の経路）、自由入力の回答を近い選択肢へ丸めない —
  原文のまま、フリーテキストである旨を明示して記録し、単位や ID の正規化のみ行って、その
  正規化を利用者に確認する。本質的に自由記述となる回答は代表的なレンジ（`p95 < 100 ms` /
  `< 500 ms` / `< 1 s`）を選択肢にして正確な値を「Other」から受け取るか、レンジが無意味な
  場合は文章で質問する。「選択肢にできないから」という理由で `TBD` に飛ばすことはない。
- **未解決のまま残るものは、その理由を明示する。** Open Questions の各エントリは `OQ-` ID・
  状態（`answered` / `deferred` / `unasked` / `external`）・回答・提示した選択肢・担当者・
  下流への影響を持ち、成果物中の `TBD` は対応する ID を伴う（`TBD (OQ-012)`）。
  `/product:report` はヘッダを状態別にグループ化するため、「誰にも聞かれていない質問」と
  「利用者が意識的に保留した質問」が区別できる。`/product:review` は未質問の `TBD` を指摘
  として報告する。`--auto` 実行では、質問文に加えて*提示したはずの選択肢*も記録するので、
  後から導出し直さずに回答できる。
- **質問はフェーズをまたいで引き継がれる。** 各スキルはコンテキスト読み込み時に自ドメインの
  `deferred` / `unasked` エントリを拾い、自分の最初の質問バッチで再質問し、同じ `OQ-` ID の
  まま更新する — 重複は作らず、回答済みは再質問しない。`/product:init-output` は
  `work/context.md` に `## Open Questions` テーブルを作成し、product→architect のハンドオフは
  その ID を `reports/00_requirements/open-questions.md` へ引き継ぐ。
- `CLAUDE.md`・`AGENTS.md`・`OMNIGENT.md` にも反映した。Codex と omnigent ローダーには
  ハーネス付与の「Other」が無いため、番号付き選択肢の下に「番号以外を入力しても構わない」旨を
  明示し、番号に一致しない回答をフリーテキストとして記録する。
- **トークンコストダッシュボードの内訳列を金額表示にした。** ライブ表示
  （`/architect:report-token-cost`）のモデル別 `入力` / `出力` / `キャッシュ読取` /
  `キャッシュ書込` の各列が、トークン数ではなくコスト（`$`）を表示するようになった。
  ダッシュボードは「いくらかかったか」を見るためのものであり、トークン合計は既に別列に
  あるためである。`b` でトークン数表示に戻せ、現在の単位は最下行に常時表示される。
  静的レポートと `--md` 出力は従来どおりトークン数（そこでは同じ表のトークン合計の内訳
  として意味を持つ）。`--breakdown=` を明示すればどちらの既定も上書きできる。
- **0 ではない金額が `$0.0000` と表示されなくなった。** 1/100 セント未満の金額は
  `<$0.0001`（`--currency=jpy` では `<¥1`）と表示する。実際には課金されている額を
  「無料」に見える表示へ丸めないためで、内訳列の金額表示によって安価なモデルがこの
  範囲に入るようになったことで顕在化していた。

## [0.22.1] - 2026-08-08

### 修正
- **ステータスダッシュボードの `c` キーがコピーではなくブラウザを開いていた。** `c` は
  「選択行の既定コマンドをコピー」と説明されているが、完了行の既定アクションは open 系
  （マージ済み Issue なら `open URL`、完了フェーズなら `open output`）であり、シェルは
  ラベルだけで分岐していた。その結果 `c` はブラウザのタブやエディタを起動したうえで
  `command <url>` と表示し、実際には何もコピーしていなかった。`c` は open 系の既定値でも
  パス／URL を必ずコピーするようにした。開くのは従来どおり `o`、アクションメニューで
  `open output` を選んだ場合も従来どおり開く。
- **フィルタで空になったツリーが「パイプラインは未実行」と表示していた。** `f` を一致しない
  ステータスまで回した場合や、`--group`／`--epic` で絞り込んだ結果が空の場合に、直前に
  集計したフェーズ数・Issue 数を表示しているヘッダの真下で「このプロジェクトでは product
  パイプラインは実行されていません」「バックログマニフェストがありません」と表示していた。
  空になった原因のフィルタを明示し、`f` で解除できる場合にのみ `f` を案内するようにした。
- **`Esc` が不正なエスケープシーケンスでダッシュボードを終了させていた。** ncurses が解釈
  できないシーケンス（アプリケーションカーソルモード無効、マウスレポート、ブラケットペースト
  やフォーカス変化のマーカー、未知の `$TERM`）を送る端末では先頭の `27` が単独のキー入力
  として届き、それが終了に割り当てられていた。`Esc` はメニューとヘルプパネルを閉じるだけと
  し、終了は `q` のみとした。あわせて `? ヘルプ | q 終了` をボトムバーに固定し、キー凡例が
  端末幅に収まらない場合でも消えないようにした（日本語の凡例は 120 桁でも溢れる）。
- **`--exec` なしのときアクションメニューに閉じ方が表示されなかった。** 凡例を最初の区切り
  文字で切り出してヒントを組み立てていたため、実行キーと一緒に `Esc 閉じる` まで落ちていた。
  あわせて、`--exec` 有効時に `open output` 項目で `e` を押すと「`--exec` 付きで起動すると
  claude を実行できます」と表示していた点を修正し（その項目を開くようにした）、`--exec`
  なしで `e` を押してもメニューを閉じないようにした（選択位置が失われないため）。
- **ヘルプパネルが記号凡例をタブの数だけ重複表示し、画面下端からはみ出していた。** 3 つの
  パイプラインタブは同一クラスで同一の凡例を返すため 2〜3 回表示され、さらに高さの上限が
  なかったため 30 行未満の端末では下辺の枠線と「閉じ方」のヒントが切れ、スクロールする手段
  もなかった。凡例を重複排除し、収まらない場合はスクロール（`^v`／PgUp／PgDn／`g`／`G`）
  できるようにした（80x24 で確認）。
- **`failed` のフェーズが画面上どこにも出ないことがあった。** 進捗率は必須経路のみを対象に
  集計するため、手動拡張ティアで失敗したフェーズやマニフェスト外に記録されたフェーズは
  ヘッダのステータス集計に現れず、該当行も折り返しの下に隠れていた（一方 `--once` は
  `failed:` のフッタを明示していた）。ダッシュボードのヘッダでも失敗フェーズ名を表示する
  ようにした。
- **ライブダッシュボードが誤記の `--phase` / `--epic` を受け付けていた。** `--once` 系は
  不正な名前に対して exit 2 を返すが、ライブモードは `--phase` を完全に無視し、不正な
  `--epic` では空のバックログを描画していたため、タイプミスが「回答」に見えていた。curses
  が画面を取る前に、全モードで検証するようにした。
- **10 秒ごとのポーリングがパイプラインタブの数だけ出力ツリーを走査していた。** プロダクト／
  アーキテクト／コード生成は同じプロジェクトディレクトリを見ているのに、それぞれ独立に走査
  していた。同一の `stamp_key` を宣言するビューについては、1 ポーリングにつき 1 回だけ
  走査するようにした。

## [0.22.0] - 2026-08-07

### 変更
- **ステータスダッシュボードのビューを 2 つから 4 つに分割した (プロダクト / アーキテクト /
  コード生成 / バックログ)。** 従来の「パイプライン」タブは product と architect のどちらを
  実行中かを*推測*し、その一方だけを表示していた。そのため両方を実行したプロジェクトでは
  片方に到達できず、もう一方のマニフェストが持つフェーズは「マニフェスト外の記録」グループに
  異常であるかのように放り込まれていた。product と architect はマニフェストの異なる別々の
  パイプラインなので、それぞれ独立したタブになり、どちらを表示しているかを推測ではなく明示
  するようになった。`Tab` / `Shift-Tab` で 4 つを巡回し、そのプロジェクトに実体の無いタブは
  淡色表示のうえスキップされる。もう一方のプラグインのマニフェストが定義しているレジストリ
  エントリは、マニフェスト外としてではなく「隣のタブのもの」として扱われる。
- **コード生成を独立したビューにした。** `generate-scalardb-code`・`generate-infra-code`・
  `generate-docs`・`/product:generate-frontend` は、設計パイプラインの完了後に手動で実行し、
  `reports/` 配下のレポートではなく対象プロジェクトへコードを出力するものなので、本来ステップ
  ではないパイプラインツリーの中には置かれなくなった。コード生成ビューは**両プラグイン**の
  該当フェーズをプラグイン単位でグループ化して集約し、各行はビューではなくそのフェーズ自身の
  プラグインのスラッシュコマンド (`/product:generate-frontend`、
  `/architect:generate-infra-code`) を提示する。`generate-test-specs` は仕様書を書くもので
  コードではないため、architect パイプライン側に残る。ビューをまたぐ依存関係と stale 判定は
  従来どおり — `generate-scalardb-code` は引き続き `design-implementation` にブロックされ、
  その再実行で stale になる。ビューごとに分かれるのはグループ化と進捗率だけである。
- **`--view=` が新しい名前を受け付ける**: `product`・`architect`・`codegen`・`backlog` に加え、
  `pipeline` (そのプロジェクトが実行しているパイプライン。`--plugin=` または自動判定で決定) と
  `auto` (従来どおり、判定されたパイプライン、無ければバックログ)。`--group=core|extension` は
  従来どおり architect のパイプラインビュー専用で、グループがプラグインであるコード生成ビュー
  には適用されない。コード生成ビューの `--md` の既定は `reports/codegen-status.md`。`--json` に
  `view`・`section` と、フェーズごとの `plugin`・`section` が加わり、各フェーズの `group` は
  実際に描画されるグループヘッダーを指すようになった。

## [0.21.2] - 2026-08-07

### 修正
- **完了済みプロジェクトがパイプラインダッシュボード上で全て `pending` と表示されていた。**
  フェーズのステータスは進捗レジストリが無条件に優先していたが、そのレジストリは各 SKILL.md
  末尾の「`pipeline-progress.json` を更新する」という緩い手順で書かれるもので、実際には
  頻繁に飛ばされ、オーケストレータ経由でない単独実行では最初から実行されない。そのため未更新
  のフェーズは初期値の `pending` に留まり、23 フェーズ全ての成果物がディスク上に存在する
  プロジェクトが `2/23 完了` と表示され、各行が `[====] 4/4 ○ pending` と自己矛盾していた。
  `pending` は「何も主張していない初期値」として扱うようになり、実在する宣言済み出力に負ける。
  `in_progress` / `completed` / `failed` / `skipped` はスキルが実際に行った主張なので従来通り
  優先される。食い違い自体はドリフトとして引き続き表示するため、未更新のレジストリが黙って
  隠蔽されることはない。これにより該当フェーズの stale 判定も復活した (`pending` のフェーズは
  stale になり得ないため、レジストリ未更新の箇所では、編集された成果物の下流を un-complete
  する無効化の連鎖が働いていなかった)。
- **ステータスダッシュボードの 2 つのタブが矛盾しなくなった。** バックログビューのパイプライン
  行は進捗レジストリを直接数えていたため、合計が「レジストリに記載されたフェーズ数」になり
  stale も無視していた。結果として同じ画面で片方が `pipeline 2/5`、Tab 1 回で切り替わる
  もう片方が `フェーズ 2/24 完了` と表示されていた。この行はパイプラインビューと同じ状態
  レイヤーで導出するようになり、合計はマニフェスト由来、レジストリに記録の無いフェーズは
  ファイルシステムから補完、無効化されたフェーズは完了数から外れ、その件数も表示する (`↺ 2`)。
- **バックログビューのキー凡例と日本語ラベルが統合ダッシュボードに追いついた。** `Tab`
  (ビュー切替)・`a` (Claude に質問)・`?` (ヘルプ) は動作していたのに下部バーに無く、ヘッダの
  4 ラベルが `--lang=ja` でも英語のままだった (パイプラインタブが `フェーズ 1/24 完了` と
  表示する隣で `Issues 1/2 done`)。
- **`/architect:investigate-security` が書くべきでない出力ファイル名を宣言していた。**
  `reports/before/{project}/architect:investigate-security.md` — ファイル名にコロンを含み、
  kebab-case 規約から外れ、実際には照合できない。スキルとダッシュボードの出力表の両方で
  `security-assessment.md` に修正。
- **`--phase` / `--epic` のタイプミスは空のツリーではなく使用法エラー (終了コード 2) になった。**
  従来は中身の無いヘッダを表示して 0 で終了しており、「このフェーズは空」と読めてしまった。
  今は実在するフェーズ名 / Epic ID を標準エラーに提示する。正当に 0 件になるフィルタ
  (product プロジェクトへの `--group=extension`) は理由付きで「表示するものがありません」と
  表示し、終了コードは 0 のまま。

### 変更
- **`--group` / `--phase` / `--epic` が `--json` にもツリーと同じように適用される。** 従来は
  黙って無視されていた。JSON には適用済みフィルタを記録する `filters` オブジェクトが付く
  (`summary` は従来どおりプロジェクト全体)。フィルタ適用時のテキスト出力の脚注 (stale・
  ドリフト・失敗) も、意図的に絞り込んで除外したフェーズではなく画面上の行を対象にする。
- **ライブダッシュボードがファイルの上書きを検知するようになった。** 更新ポーリングは
  `reports/` を 2 階層までディレクトリの mtime で比較していたが、既存ファイルの上書きでは
  どのディレクトリの mtime も変わらない。これは stale 検知が対象とするケースそのもので、
  architect が書く場所 (`reports/before/{project}/*.md`・`reports/review/individual/*.json`)
  がまさにそこだった。件数上限付きで 3 階層までファイル自体を stat するようにした。
- **手動拡張ティアの宣言出力をコアパイプラインと同水準にした。** スキルが 3〜4 ファイルを書く
  のに 1 つしか宣言していなかったため (`estimate-cost`・`design-implementation`・
  `generate-test-specs`・`generate-scalardb-code`・`generate-infra-code`)、出力バーが 0/1 か
  1/1 しか取り得なかった。各 SKILL.md が約束する内容を宣言するようにし、`report-token-cost`
  を 15 番目のメンバーとしてティアに加えた。

### 追加
- **`tools/nexus-status.test.sh`** — 2 つのデータモジュールの上位にあたる CLI 契約の実行可能な
  検証: プロジェクト解決と終了コード 0/1/2、ビュー選択、全出力モード (`--md` の frontmatter と
  `--ascii` の純度を含む)、フィルタが `--json` に適用されること、不正なフィルタが使用法エラーに
  なること、2 つのビューの一致、上書きされた 3 階層目のレポートをポーリングが検知すること。
  導出テストも拡張ティアをドキュメントと各スキルの Output 表に対して検証するようになったので、
  ティアにスキルを追加してダッシュボードに反映し忘れることがなくなる。
- 存在するが未記載だったダッシュボードのオプションをスキルのドキュメントに追記:
  `--watch[=SEC]` / `--live`・`--glyphs`・`--color` / `--no-color`・`--plugin`。

## [0.21.1] - 2026-08-07

### 修正
- **`completed` は永続しない: `/architect:report-status` / `/product:report-status` が上流の変更で
  下流フェーズを無効化するようになった。** 従来は進捗レジストリの状態を最終的な答えとして読んでいた
  ため、前の工程を修正しても（再実行しても、出力レポートを手で直しても）下流のフェーズは `completed`
  のまま残り、すでに存在しない入力から作られた成果物でパイプラインが「完了」と表示され続けていた。
  依存先が自分の完了**後**に出力を書いているフェーズは、`completed` に代えて **`stale`**（`↺`、ASCII
  では `@`）と表示し、どの依存がいつ変わったかを併記する。無効化は依存グラフを 1 回のトポロジカル
  走査で伝播するので、パイプライン上流の 1 箇所の修正が、その下の連鎖全体を un-complete する — 対象
  フェーズは `n/m 完了` の分子とグループ集計から外れ、再び実行可能になり、既定アクションが再実行に
  変わり、`f` の状態フィルタで絞り込め、`次:` の推奨はその中で最も上流のものになる（上流から再実行
  すれば残りは自然に解消する）。書き戻しは一切しない — レジストリは無変更で、`--json` は記録上の
  `status` と表示用の `display_status` を両方返す。フラグの信頼性を保つための制限も明確にした:
  同一実行内の書き込み順のズレは 5 秒の猶予で吸収し、未実行の依存は何も無効化せず、出力を宣言して
  いるのに 1 つも書いていないフェーズは従来どおりドリフト扱い（実ファイルに否定されている記録は、
  何より古いかを判断する根拠にならない）。契約は `tools/lib/pipeline_status_data.test.py` で検証。

## [0.21.0] - 2026-08-06

### 追加
- **`/architect:report-status` / `/product:report-status`（新規スキル、haiku）: パイプライン進捗を
  バックログと同じダッシュボードでライブ表示。** バックログデリバリーにはライブ表示があったが、その
  手前の product / architect パイプラインには手段がなく、`work/pipeline-progress.json` を生の JSON で
  読むしかない上に、多くのスキルはフェーズ完了時にしか書き込まないため「今どこを走っているか」が
  分からなかった。ダッシュボードを `tools/nexus-status.sh` 1 本に統合し、`Tab` で **pipeline**（新規）と
  **backlog**（従来。`tools/backlog-status.sh` は薄い別名として存続、`/architect:report-backlog-status`
  も従来どおり）を切り替える。pipeline ビューはフェーズツリーをカテゴリ単位で表示し（architect の手動
  拡張ティアは折りたたみ可能な独立グループ）、各フェーズの状態、宣言された `outputs:` のうち実在する数
  （`[==..] 2/4`）、直近 5 分にファイル書き込みやトークン消費があったか、未充足の依存、モデルティア、
  記録済みコストを並べる。product ビューはヘッダに `validate-assumptions` のゲート判定と未検証前提の
  件数を追加する。状態は進捗レジストリ優先・実ファイル補完で、レジストリに記載のないフェーズは出力から
  導出し、食い違い（`completed` なのに出力なし／`pending` なのに全出力あり）はドリフトとして明示する。
  両ビューは次コマンド生成のアクションメニュー（クリップボード、または `--exec` で `claude` 実行）、
  選択行の文脈を添えて Claude に質問する新しい `a` キー、`?` のヘルプパネルを共有する。`--once` /
  `--json` / `--md` は非対話レンダリング。契約テスト `tools/lib/pipeline_status_data.test.py` を追加。
- **進捗レジストリの `in_progress` 契約（@skills/common/progress-registry.md）。** オーケストレータ
  （`/architect:pipeline`、`/architect:start`、`/product:start`）は各フェーズを 2 回書くようになった —
  スキル起動**前**に `in_progress` + `started_at`、復帰後に `completed`/`failed` と `completed_at` /
  `outputs` / `summary`。長いフェーズは任意で `note` / `updated_at` を更新する。これが実行中フェーズを
  実行中のまま可視化する唯一の手段であり、トークン使用量フックのコスト按分もこれに依存する（無いと
  トークンは pending バケットに溜まる）。
- **`/architect:capture-followup`（新規スキル、sonnet）: バックログデリバリー向けフォローアップ捕捉。**
  デリバリー中に発見される作業 — 先送りタスク、スコープ外の指摘、ドキュメントドリフト、Issue 分割で
  切り出したスコープ、マージ時に waive された受入条件 — は従来コメントやレビュー文中で行き止まりに
  なっていた。本スキルはそれらをレビュー可能なキュー（`reports/backlog/followup-queue.md`）に、
  半自律の実装ランを中断せずに捕捉し、明示的な承認ゲートを経てトラッカー Issue として起票する:
  `status::todo` ラベル付与、対応中の Sub-Epic/Epic への紐付け（ネイティブ Epic リンク、または
  未チェックの子ボックスをインプレース追記）、`backlog-manifest.json` への `F` 番台ローカル ID
  （`I1.2.F1`）+ `origin` トレイル付きノード追記。`F` 番台は `export-backlog` の位置採番 ID と
  構造的に非交差で、`--update` はフォローアップノードを明示的に保持する。`implement-backlog`・
  `review-issue`・`merge-issue` は各先送りポイントを `--queue-only` でキューに接続し、
  `deliver-backlog` は起票された Issue を通常の `status::todo` 作業として取り込む。ID/マニフェスト
  契約は `skills/capture-followup/followup-contract.test.py` が検証し、チェックリスト契約には本スキルが
  所有する「未チェック子ボックスの追記」操作が加わる。

- **`/architect:report-backlog-status`(新規スキル、haiku)+ `tools/backlog-status.sh`:
  バックログデリバリーのライブターミナルダッシュボード。** Epic → Sub-Epic → Issue のツリーを
  折り畳み可能に表示し、各アイテムのデリバリー状態(`todo/doing/review/done/blocked` —
  トラッカー優先、次に `impl.status`。シードの `labels` 配列は読まない)と
  Implemented/Reviewed/Merged のステージボックスを併記。ヘッダには Issue 全体の集計、
  フォローアップキュー、パイプラインフェーズ帯。`Enter` でアイテム別アクションメニューが開き、
  次に実行すべきスラッシュコマンド(`/architect:implement-backlog I1.2.3` など)を生成 —
  デフォルトはクリップボードにコピー、`--exec` 時は `claude` をフォアグラウンド実行。
  `s`/`--sync` で glab/gh のライブラベルを重ねドリフトを表示。マニフェストは 10 秒毎に再読込、
  `--once`/`--json`/`--md` で非対話レンダリング。表示層は `token-cost-report` と共通
  (`--ascii`/`--ambiguous-width` も同じ挙動)、導出契約は
  `tools/lib/backlog_status_data.test.py` が検証。

### 変更
- **チェックボックスの意味を「マージ済み」から「実装状態」に変更。** Epic/Sub-Epic の子タスクリストの
  ボックスは従来 `merge-issue` がマージ時にのみチェックしていたため、実装・テスト完了でレビュー待ちの
  Epic でも進捗 0% と表示されていた。チェックリスト契約を再定義し、**チェックボックス = 実装+テスト
  完了**（全受入条件がテスト証跡付きでチェックされた時点で `implement-backlog` がチェックし、
  `review-issue` が照合 — 未達が判明すれば理由付きでチェックを外す）、**デリバリー状態
  （マージ/done）= `status::*` ラベルと `impl.status`** に分離。`merge-issue` は通常フローでは
  チェックせず、マージ時に検証してチェック漏れのみ補完する（マージ済み・CI グリーンが証跡）。
  `backlog-checklists.md`・`implement-backlog`・`review-issue`・`merge-issue`・`deliver-backlog`・
  `capture-followup` に反映。
- **全 Epic/Sub-Epic/Issue の本文に `## Delivery Status` セクションを追加** — トラッカーラベルを
  ミラーする `Status:` 行と、ステージ別チェックリスト（`Implemented` / `Reviewed` / `Merged`、
  親アイテムは `Implemented`/`Merged` の 2 段）。実装チェックボックスが意図的に持たない
  「マージされたか」を本文が答えられるようにする。新規アイテムは `export-backlog` と
  `capture-followup` が起票時に付与し、`implement-backlog`・`review-issue`・`merge-issue` は
  自分が確立したステージをチェックしてラベル遷移のたびに `Status:` 行を書き換える
  （機械可読の情報源は引き続きラベルと `impl.status`）。**既存アイテムはレトロフィット**:
  セクションを持たない本文を編集しようとするスキルが、ライブのトラッカー状態から初期化して
  先に追記する。`export-backlog --update` は本文同期時にセクションとチェック済みボックスを保持。

### ドキュメント
- **`docs/analysis-mechanism_ja.md`（新規）: architect プラグインが既存コード・設計ドキュメントを
  どう解析しているか。** `skills/common/skill-dependencies.yaml` に従うパイプライン、2 つの入口
  （コードを読む `investigate`、RFP・議事録・既存設計書を読む `define-requirements`）、AST 優先の
  ツール階層（Serena MCP → Glob/Grep → Read → サブエージェント）を辿ったうえで、内部ロジックに
  踏み込む: シンボル参照のたどり方と別名実装（naming drift）の検出、評価を文書化済みの証拠に
  限定する 2 段階ルーブリック採点、テンプレート突合とギャップ駆動ヒアリング、決定論的スキーマで
  拘束される LLM 読解、ユビキタス言語の導出手順。最後に進捗レジストリという状態機械、exit 2 に
  よるフックの自己修正ループ、5 視点 × 3 次元の二重並列レビューと externalize された品質ゲート、
  架空のレガシー EC モノリスを通した具体例まで。日本語のみ。

## [0.20.0] - 2026-08-05

### 追加
- **`rules/scalardb-saga-patterns.md`（新規ルール）: ScalarDB Saga。** OKF ナレッジバンドルに
  ScalarDB Saga が 4 つ目の製品として追加されたことを受け、Saga オーケストレーションを
  「手作りのパターン」ではなく第一級の設計選択肢として扱えるようにしました。SAGA と TCC の
  選択、譲れない冪等性・補償の制約、Saga 定義（宣言的サービスステップと embedded 専用の
  コードステップ）、Saga のライフサイクルと `ESCALATED` の運用キュー、server / embedded の
  デプロイ形態とアーティファクト・Java マトリクス、`scalar.db.saga.server.*` の設定ルール
  （セキュリティプロバイダ、`owner_id`、リカバリタイムアウト、リテンション）を収録。
- **ScalarDB 3.19 を設計・採用判断のパスに反映。** サービス跨ぎトランザクションの判断を、
  2PC 既定ではなく 4 方式の順位付け——共有クラスタの 1PC、3.19 の **Global Transaction API**
  ＋ Transaction Coordinator ノード、アプリ駆動 2PC、ScalarDB Saga——に変更。
  `rules/scalardb-2pc-patterns.md`（スコープをサービス跨ぎトランザクション全体に拡大）、
  `design-scalardb`、`design-microservices`、`select-scalardb-edition`、`define-requirements`、
  `review-scalardb`、`skills/common/references/interface-matrix.md` に適用。
- **product プラグインの技術適合性チェックリストに ScalarDB Saga を追加**
  （`/product:design-architecture`、`rules/product/architecture-and-tech-fitness.md`）。Kong /
  ScalarDB / ScalarDB Analytics / ScalarDL と並んで毎回評価する対象とし、ScalarDB 採用に
  付随するのではなく「コンテキスト跨ぎで結果整合が要件」というシグナルで起動します。

### 変更
- **greenfield の適用判定ツリーで、結果整合の枝が ScalarDB Saga に接続されるようになりました。**
  `/architect:define-requirements` が実際に辿る `workflow/greenfield/01_requirements_analysis.md`
  Step 1.4 では、結果整合の枝が「ScalarDB 不要」で終端していました。これを「各ステップに補償が
  定義できるか」で分岐させ、ScalarDB Saga に到達するよう修正。ステップ名も Scalar **製品**の
  適用判定（ScalarDB / ScalarDB Saga / いずれも不要）に改め、業務プロセス単位で判定し、ScalarDB
  採用＝2PC という前提を置かないことを明記しました。Step 1.5 の XA 比較表には、共有クラスタと
  Global Transaction API を踏まえた「サービス跨ぎのアプリ実装複雑度」の行を追加。
- **`/architect:design-scalardb-analytics` の「Enterprise Premium only」表記を訂正** — ScalarDB
  Analytics は別契約の Enterprise **Option** のため、Premium 契約なら使える前提を置かず
  ライセンスを確認する挙動に変更。Oracle / MySQL / PostgreSQL 移行リファレンスのエディション表
  （ABAC を単なる Premium ではなく Enterprise Premium Option として明記）と、skill-reference の
  条件列も同様に訂正。
- **`/scalardb:migrate` は 1PC → 2PC 移行を勧める前に、そもそも必要かを確認**するようになりました。
  共有クラスタパターンと 3.19 の Global Transaction API はいずれもサービス跨ぎでもアプリコードを
  1PC に保てるためです。あわせて 2PC → 1PC の簡素化が以前より選択しやすくなった旨も記載。
- **OKF ナレッジバンドルを `7a723b8` に更新** — ScalarDB 3.19 と ScalarDB Saga 3.19 を追加。
  4 製品・21 バージョンライン・2,015 concepts（従来は 3 製品・19 バージョン・1,800 concepts）。
- **`rules/scalardb-edition-profiles.md` をバンドルの機能マトリクスに基づき全面改訂。**
  実害のある誤りがありました: SQL/JDBC/Spring Data/GraphQL は Enterprise **Standard** ではなく
  **Premium**、ScalarDB Analytics は Premium に含まれず別契約の Enterprise **Option** です。
  バンドルが使う 5 つのエディション値（ABAC 用の `Enterprise Premium Option` を含む）、3.19 の
  機能表、マイクロサービス向けクラスタトポロジ、ラインごとの保守サポート期限、そして SLA は
  エディション名ではなく商用契約で決まる旨を明記。
- **`rules/scalardb-exception-handling.md`**: 3.19 の Consensus Commit リカバリ API
  （`finishTransaction()`・`recoverRecord()`・write-set logging）はアプリの例外処理から呼ぶ
  ものではない低レベル運用 API であることを明記。あわせて Cluster pause RPC の `ABORTED` /
  `ErrorInfo` の扱い（`TIMED_OUT_STILL_PAUSED` のときは unpause しない）を追加。
- **`rules/scalardb-config-validation.md`**: 3.19 で追加された 2 つのプロパティ、グループコミットと
  2PC の非互換、`single-crud-operation` 時の注意を追加。
- **ScalarDB のアーティファクト固定を `3.16.0`/`3.17.x` → `3.19.0` に更新** —
  `spring-boot-integration`、6 つのコードパターン参照、Oracle/MySQL/PostgreSQL の移行テンプレート。
  各座標は Maven Central と v3.19.0 のリリースアセットで確認済み。
- `/architect:design-observability` は ScalarDB Cluster ネイティブの OpenTelemetry サポート
  （3.19+）を優先し、ScalarDB Saga を含む構成では Saga レベルのシグナルを追加します。

## [0.19.0] - 2026-08-04

### 追加
- **`/architect:report-token-cost`（新スキル・haiku）: エージェントが実際に記録したコストを
  ターミナルに表示。** `/architect:estimate-token-cost` の対になるスキルで、あちらが LOC から
  事前に見積もるのに対し、こちらは `record_token_usage.py` フックが
  `work/token-usage.json` と `work/token-usage.jsonl` に記録した**実績**を描画します。
  モデル別コストは台帳の値をそのまま信用せず
  `skills/common/references/model-pricing.json` から**再計算**するため、価格改定に追随します。
  - `tools/token-cost-report.sh` が `tools/lib/token_cost_*.py` を使って 5 つのモードを提供:
    **対話型 2 ペインダッシュボード**（TTY での既定。上ペインでフェーズ／モデル／セッション／
    日次／イベントを選び、下ペインにその詳細を表示。セッションでは拡張思考を含むトランスクリプト
    ログを表示。10 秒ごとに台帳を再確認）、`--once` による単発描画（サマリー、フェーズ別、
    入力／出力／キャッシュ読取／キャッシュ書込に分けたモデル別、日次推移、上位セッション、
    直近イベント）、`--session=ID` による単一セッションとそのログの非対話表示、
    `--follow` によるイベントのストリーム表示、`--json` / `--md` エクスポート。
  - セッションは台帳が指す Claude のトランスクリプトから**名前を解決**し、ログもそこから読みます。
    セッション一覧が UUID の羅列ではなくプロンプトとして読めるようになります。
  - 表示オプション: `--since`、`--breakdown=tokens|cost`、`--top=N`、`--lang`、
    `--currency=jpy --fx=RATE`、`--width`、`--color` / `--no-color`。

### 修正
- **描画の単位を文字数ではなく端末の桁数に統一。** 罫線は 1 桁につき 1 文字を出力していたため、
  East Asian Ambiguous 文字を 2 桁で描画する端末では 100 桁の罫線が 200 桁になり、すべての
  区切り線が画面外にはみ出していました。棒グラフも同じ不具合でした。どちらも桁数で計算します。
  表は 3 段階で端末幅に収縮し、収まらない場合は折り返さずモデル別の内訳列を落とします。
  `--follow` も固定 140 桁ではなく実際の幅に合わせて列幅を配分します。
- **ライブダッシュボードに前フレームの残像が残らないように。** curses は全角セルを数え違えるため、
  差分更新が「既に一致している」と判断したセルを書き換えず、セッションのコスト表に前のタブの数値が
  残ることがありました。毎フレーム全面再描画するようにしています（`touchwin()` では不十分で、
  ウィンドウを再コピーしても同じ古いモデルと差分を取るため）。
- スクロール位置の表示を表の内容の上ではなくヘッダー行と区切り行に配置。一覧ペインが行数以上に
  広がらないように修正。キー操作バーが右下セルに書き込んで毎フレーム描画に失敗していた問題を修正。

### 変更
- **Unicode の記号が正しく描画されない端末向けの描画オプションを追加。** `--ascii`
  （`--glyphs=ascii|unicode`）は棒グラフ・罫線・区切りを `# . - | ->` で描画します。これは
  **出力言語が `ja` のときの既定**になりました。日本語環境の端末は Ambiguous 幅を 2 桁で
  描画する設定が多く、フォントもシェード記号より仮名・漢字を優先して選ばれるためです。
  英語出力は従来どおり Unicode を使います。`--ambiguous-width=1|2` は Ambiguous 文字を
  何桁として扱うかを指定します（この設定を報告する端末は存在しないため、推測はしません）。
  `--debug[=PATH]` は描画環境と失敗した curses 書き込みを記録します。変更されるのは
  **描画用の記号だけ**で、日本語ラベルはいずれの場合も Unicode のままです。

## [0.18.0] - 2026-07-28

### 追加
- **ScalarDB / ScalarDL の実装判断を、バージョン固定の公式ドキュメントに基づかせるように。**
  [OKF-ScalarDB-ScalarDL](https://github.com/wfukatsu/OKF-ScalarDB-ScalarDL) バンドル —
  developers.scalar-labs.com の全ドキュメントを製品ごと・バージョンごとに分割したもの
  （ScalarDB 3.14–3.18、ScalarDL 3.10–3.13、ScalarDB Community 3.4–3.13、計 1,800 概念）—
  を git submodule として `knowledge/okf-scalardb-scalardl/` に組み込み、スキルがモデルの記憶や
  バージョン不定の「latest」ドキュメントではなく、**プロジェクトが実際に動かしているリリース**を
  根拠に回答するようにした。
  - `rules/okf-knowledge-bundle.md`（新しい共有契約）: バンドルの解決（submodule →
    `~/.cache/nexus-architect/` への shallow clone → 「バージョン非固定」と明示した上での
    オンラインドキュメント）、読む前に**製品・バージョン・エディション**を確定、スキル群に対応
    づけた `lifecycle_phase`（design / implement / operate）で概念を絞り込み、バージョンを跨いだ
    回答の禁止、各概念の正規 `resource` URL の引用、依存のピン留めには frontmatter の
    `patch_version` を使用 — `rules/dependency-versions.md` / `work/version-decisions.json` の
    フローに接続する。
  - `tools/update-okf-bundle.sh` + `/architect:update-knowledge`（新スキル、haiku）: バンドルの
    リモート取得・更新・確認 — 引数なしの *ensure* は未取得のときだけ取得、`update` は最新を
    取得（submodule のポインタが進むので、固定するにはコミットする）、`status` は解決パス・
    ローカル/リモートのコミット・収録バージョンを表示。

### 変更
- **3 プラグイン横断で 19 スキルがバンドルを参照するように。** `architect`: `design-scalardb`
  （Context7 はフォールバックに降格）、`design-scalardb-analytics`、`select-scalardb-edition`
  （エディション判定を frontmatter の `editions` / `feature_status` で検証）、
  `generate-scalardb-code`（API シグネチャ・設定キー・例外のリトライ可否は、固定したリリースの
  `implement` フェーズ概念を根拠にする）、`review-scalardb`（指摘の根拠として `resource` URL を
  引用）、`define-requirements`、`migrate-database`。`scalardb`: `docs` はバンドル優先の検索に
  変更し、WebFetch は「バージョン非固定」と明示するフォールバックに降格。`build-app`・`model`・
  `config`・`crud-ops`・`jdbc-ops`・`error-handler`・`scaffold`・`review-code`・`migrate`・
  `local-env` にはナレッジグラウンディングの注記を追加。`product`: `design-architecture` は
  ScalarDB / ScalarDL の適合性判断をバンドルに基づかせる。
- エントリドキュメントを同期: `CLAUDE.md`（Rules & References 行・Conventions・コマンド
  リファレンス）、`AGENTS.md` と `OMNIGENT.md`（グラウンディング規則 + 更新コマンド）、
  `README.md`（`--recurse-submodules` での clone、新セクション **ScalarDB / ScalarDL Knowledge
  Bundle**）、`rules/scalardb-coding-patterns.md`（ルール索引の先頭にバンドルを掲載）。

## [0.17.7] - 2026-07-27

### ドキュメント
- **コード生成と配送の呼び出し方を明文化。** コード生成スキルはカタログには載っていたが、
  使い方が書かれていなかった — `/architect:pipeline` の外にあること、どの順で連鎖するか、
  各スキルが何を前提とするかがどこにも書かれておらず、さらにバックログ配送のスキル群
  （`export-backlog`・`deliver-backlog`・`implement-backlog`・`review-issue`・`merge-issue`）は
  `CLAUDE.md` には記載があるのに `README.md` と `docs/skill-reference*` には**まったく載っていなかった**。
  - `README.md`: Quick Start にコード生成と配送の入口を追加。新セクション **Code Generation &
    Delivery** で4つの経路と、最も重要な違い — 経路 A は `generated/` 配下の使い捨てスキャフォールド、
    経路 B はプロジェクトの実ソースツリーに書くマージ対象コード — を提示。**Backlog Delivery** の
    コマンド表を新設し、Implementation & Codegen の表に *Requires* 列を追加。依存グラフに手動拡張
    ティアの説明を追記し、v0.17.6 のフラグとプロジェクト設定を説明する **Dependency Versions**
    セクションを新設。
  - `docs/getting-started.md` / `_ja.md`: §5「コードの生成」、§6「バックログ経由でのコード配送」、
    §7「依存バージョンの選択」を新設（既存の ScalarDB / 移行セクションは 8・9 に繰り下げ）。
  - `docs/skill-reference.md` / `_ja.md`: 実装の表に *前提* 列と手動拡張ティアの注記を追加し、
    スキルごとのモデルと役割を示す **バックログ配送** セクションを新設。

### 修正
- `CLAUDE.md` に「手動拡張ティアは `/architect:start` 経由でも呼べる」と書かれていたが、これは誤り。
  `start` は `skill-dependencies.yaml` のフェーズしか実行せず、コード生成スキルを一切参照していない。
  記述を実態に合わせ、新しい呼び出し手順への参照を追加した。

## [0.17.6] - 2026-07-27

### 追加
- **依存バージョンは pin する前に必ず調べる。確認するかどうかはユーザーが選べる**
  （`rules/dependency-versions.md` — 新しい共有契約）。従来のコード生成スキルは、モデルの記憶や
  本リポジトリ自身のスキル内サンプルからバージョン番号を書いていた。そしてそれはドリフトする —
  `config`・`local-env`・`migrate`・code-patterns はいずれも ScalarDB `3.16.0` を pin していたが、
  `spring-boot-integration.md` は `3.17.0`、実際の現行安定版は `3.18.0` だった
  （`gh release list -R scalar-labs/scalardb` と
  `repo1.maven.org/.../scalardb/maven-metadata.xml` で確認済み）。記憶から書いたバージョンは
  未検証の主張であり、古いバージョンは実際のビルドにそのまま流れ込む。

  対象はバージョンを pin するすべての生成物 — Gradle / Maven、`package.json`、イメージタグ、
  Helm / Terraform / Kubernetes、CI ランナーイメージ:
  - **記憶からバージョンを書かない。** エコシステムごとに参照先を明記した:
    `repo1.maven.org/.../maven-metadata.xml`（`search.maven.org` の solr は既定の並び順が
    バージョン順では**ない**ため、古いリリースを最新のように返す。使わない）、
    `npm view <pkg> dist-tags --json`（`latest` タグ。`next`/`canary` ではない）、
    `gh release list`（`Pre-release` 表示が明示される）、Docker Hub / Terraform レジストリ API
    （Terraform の versions 配列は**未ソート** — semver で自分で並べる）、
    `helm search repo --versions`、LTS / EOL 日付は `endoflife.date/api/<product>.json`、
    互換性の記述は context7。
  - **「最新」ではなく「安定」を選ぶ。** プレリリースは除外、`:latest`/`stable` のような可変タグは
    使わない、そのエコシステムが LTS を定義しているなら LTS を優先（多くの場合 LTS は最大の番号では
    ない）、EOL のラインは pin しない、出たばかりのメジャーは既定採用せずフラグとして扱う、
    対象プロジェクト既存の lockfile / BOM / 親 POM は "latest" より優先（作業のついでに無関係な
    依存を上げない）、そして最後に相互互換性で全体を判定する — 各々の最新版の組み合わせは
    しばしば動かない。
  - **決定を記録する。** バージョン決定表（採用 / 最新安定版 / リリース日 / 情報源 / 理由 /
    却下したもの）を成果物に書き、`work/version-decisions.json` にミラーして 7 日間再利用する
    （`--refresh-versions` で再解決）。並列サブエージェントや後続スキルが同じライブラリに
    異なるバージョンを pin することを防ぐ。
  - **調べられなかった時に推測で埋めない。** プロジェクト既存の pin にフォールバックし、
    `verified: false` と理由を記録してユーザーに提示する。

- **`--confirm-versions` / `--no-confirm-versions` と `options.confirm_versions`。**
  解決したバージョン群をユーザーに確認するか、黙って採用するかは設定可能: 実行単位はフラグ、
  プロジェクト既定は `work/pipeline-progress.json` のオプション、未設定なら対話実行では確認し
  `--auto` では確認せず採用。`/architect:start` と `/product:start` が出力言語と一緒にこの設定を
  尋ね、`init-output` が初期値を書き込む。設定に関わらず必ず確認するケース: 参照に失敗した場合、
  現行の選択肢が出たばかりのメジャーのみの場合、既存 pin が EOL の場合、ダウングレードなしに
  互換な組み合わせが存在しない場合、有償エディションや private レジストリが必要な場合。

### 変更
- バージョンを pin するすべてのスキルに contract を接続: `/architect:generate-scalardb-code`、
  `/architect:generate-infra-code`、`/architect:implement-backlog`（Step 5 — 一度解決した
  バージョンをサブエージェントに渡す。既存 lockfile は拘束的）、
  `/architect:design-infrastructure`（バージョンとサポート期限を併記）、
  `/product:generate-frontend`（React / Vite / Storybook の互換性を明示）、
  `/scalardb:scaffold`（Step 4 を新設）、`/scalardb:config`、`/scalardb:local-env`、
  `/scalardb:build-app`、`/scalardb:migrate`。
- 本文中の古い pin が「現在の正解」として読まれないようにした: `config`・`migrate`・`local-env` の
  schema-loader コマンド・migrate ルーターの `SCALARDB_TARGET_VERSION` はバージョン非依存の
  プレースホルダに変更し、code-patterns・`spring-boot-integration.md`・移行テンプレートには
  参照ルールを指す「これは日付付きサンプル」バナーを追加した。
- `/scalardb:local-env` から可変タグ `:latest` を排除した — compose ファイルは再現性のために
  具体的なタグを pin する必要がある。
- エントリードキュメントを同期: `CLAUDE.md`（ルール表・規約・フラグ）、`AGENTS.md`（Codex が使う
  シェル参照コマンド）、`OMNIGENT.md`、`skills/common/progress-registry.md`
  （`options` ブロック全体を表として明文化。`confirm_versions` を含む）。

## [0.17.5] - 2026-07-27

### 追加
- **Epic / Sub-Epic / Issue のチェックリストを進行に応じて更新するようになった**
  （`skills/common/backlog-checklists.md` — 新しい共有契約）。従来のバックログ系スキルは
  ステータスラベル・進捗コメント・manifest は更新していたが、トラッカー上のチェックボックスは
  誰も更新していなかった。GitLab / GitHub はタスクリストを進捗カウンタとして表示するため、
  実装・マージが完了した Issue でも受入基準と親のタスクリストのボックスが未チェックのまま残り、
  Epic を見る全員に対して実際の進捗を過少報告していた。チェックリストは 2 種類で、
  それぞれ更新責任を持つスキルは 1 つだけ:
  - **子アイテムのタスクリスト**（Epic の `## Sub-Epics`、Sub-Epic の `## Issues`）→
    `/architect:merge-issue`。しかもその子が実際に `done` になった時のみ（`done` を確定させるのは
    マージだから）。
  - **受入基準**（Issue の `## Acceptance Criteria`）→ `/architect:implement-backlog`（実装済み）→
    `/architect:review-issue`（検証済み）。

  全スキル共通のルール: 根拠がある時だけチェックし、意図ではチェックしない / 本文はその場で
  `[ ]` → `[x]` のマーカーのみを書き換える（`backlog-manifest.json` から本文を再生成しない —
  人間の編集を破棄してしまうため）/ 再実行は冪等 / レビューや revert で基準が満たされていないと
  判明した場合は理由を明記してチェックを外してよい / GitLab ネイティブ Epic・GitHub sub-issue
  経路では親がリンクを持ちタスクリストが存在しないためスキップ / `--dry-run` は本文を書き換えない。

### 変更
- **`/architect:export-backlog`** が両方のチェックリストを未チェックの `- [ ]` ボックスとして
  生成する（受入基準は 1 件 1 ボックス、子アイテムも 1 件 1 ボックス）。自身は何もチェックしない。
  Given/When/Then は 1 ボックスの *中* に収める — 散文として書かれた基準は下流のスキルが
  チェックできないため。
- **`/architect:implement-backlog`**（Step 7）がコミット済みコードで満たした受入基準を
  チェックし（根拠はコミット / テスト / ドキュメント）、未チェックのまま残したボックスを
  同じ進捗コメントに列挙する。親のタスクリストは触らない — Issue は PR/MR がマージされるまで
  done ではない。
- **`/architect:review-issue`**（Step 5）が PR/MR を上げる前にチェックリストとレビュー判定を
  突き合わせる: 確認できた基準はチェック、覆った基準は理由を Issue に書いてチェックを外し、
  未達のまま残るものは PR/MR 本文に明示する。
- **`/architect:merge-issue`** が未チェックの受入基準を **Step 2 の確認ゲート** で提示する
  （プリフライトには意図的に入れていない — 「プリフライトは全項目必須」という不変条件を
  弱めないため）。Step 4 では当該 Issue の Sub-Epic 内のボックスを、さらにその Sub-Epic が完了した
  場合は Epic 内の当該 Sub-Epic のボックスをチェックする。ユーザーが waive した基準はマージ
  コメントに記録し、完了に見せるためにチェックすることはしない。
- **`/architect:deliver-backlog`** に、チェックボックスは進捗の *出力* であり再開の入力では
  ないことを明記した。ステージ判定は従来どおり `impl.status` とトラッカーのラベルから読み、
  ずれているボックスは担当スキルが直すべき不具合として扱う。

## [0.17.4] - 2026-07-26

### 修正
- **`/architect:generate-docs` — v0.16.2〜v0.17.3 の全作業レビューで見つかった曖昧さ3件を解消。**
  いずれも検証済みの挙動を変えるものではなく、従来は導出可能だが暗黙だった点の明文化。
  - **単独起動時のモード判定を明記。** `--issue` なしで、かつ他スキルの一工程としてでもなく起動された
    場合は、解決された root がモードを決める — `generated/` 配下なら Scaffold、それ以外は Delivery。
    Delivery ではトラッカーへの書き込み前に `--issue` が必須で、参照する Issue が無い実行では
    コミットは作業ブランチに載せつつ、ドリフト所見はユーザーへの報告のみとなる。
  - **`findings` セクションの書き手とタイミングを明記。** 内容を生むのは Step 5 の検証だが、記載は
    Step 4 のセクション表のみで、初回実行の書き手が不在だった。Scaffold モードでは Step 5 が検証後に
    書くことを明記し、Step 4 側の記載は「前回の所見が既に存在する再実行」を扱うものと位置づけた。
  - **安定キー一覧の情報源を一本化。** SKILL.md の散文と契約テストの `STABLE` 集合に二重管理されて
    おり、同期はコメント頼みだった。テストが SKILL.md の「Section keys are stable (…)」の一文から
    一覧を parse するようになり、当該文が消えた場合はハードフェイル、ファイルが単体でコピーされた
    場合はフォールバック一覧で検査を継続する。検証済み: 8キー全て parse され、両フィクスチャと
    フォールバック経路がすべて PASS。

## [0.17.3] - 2026-07-26

本リリースの内容はすべて、バックログ配送経路を実地で動かした結果として得られたものです — マーカー契約を
実在の `/product:generate-frontend` スキャフォールドに対して、Output Location インターロックをスクラッチ
リポジトリで、Step 1 のサブエージェント委譲を実プロジェクトで、そしてトラッカーへの全書き込み経路
（ステータス遷移・進捗コメント・PR 連携・マージ・クローズ・ロールアップ）を実作業項目ではなく使い捨て
リポジトリに対して実行しました。

### 修正
- **`/architect:merge-issue` — 親ノードの完了が manifest に届くようになった。** Step 4 の記述が
  "update the node"（単数）で、しかも Issue にしか存在しない `pr.merged` や merge SHA と併記されて
  いた。そのため Sub-Epic/Epic をトラッカー上で `status::done` にしても manifest には何も書き戻され
  なかった。実在の35ノードのバックログでまさにこの状態を観測 — Issue 27件は全て `impl` を持つ一方、
  Epic と完了済み Sub-Epic 4件には `impl` キー自体が無かった。`deliver-backlog` は `impl.status` を
  読んで resume するため、完了済みの Sub-Epic を未着手と誤認する経路になる。Step 4 はロールアップが
  動かした全ノードを更新するようになり、`pr` 系フィールドは Issue のみに限定された。
- **`/architect:export-backlog`・`/architect:deliver-backlog` — manifest の `labels` 配列は作成時の
  シード値であり現在値ではない。** 作成時に付与された内容（`status::todo` と type/domain ラベル）を
  記録するだけで以後更新されず、ステータスはトラッカーと `impl.status` にある。実バックログでは全
  ノードが `status:todo` のままなのに、トラッカー側は done 7 / doing 9 だった。現状は誰も読んで
  いないため実害は無いが resume ロジックの罠になるため、`export-backlog` にフィールドの正体
  （`--update` 時のみ書き換わることも含む）を明記し、`deliver-backlog` には状態を `impl.status` と
  トラッカーから読むこと、`labels` からは読まないこと、食い違い時はトラッカーが正であることを明示した。
- **`/architect:generate-docs` — インベントリダイジェストが観測値と推論値を区別するようになった。**
  Step 1 の委譲を実行して設計自体は検証できた（haiku の Explore が6項目すべてを埋めたダイジェストを
  返し、独立に検証済みの数値・コマンドと全件一致、ソースの貼り付けも捏造もゼロ）が、穴が判明した —
  `package.json` に `engines` の宣言が無いにもかかわらず「Node.js 18+」をインベントリとして断定して
  いた（Vite 5 の要件からの推論）。結論は正しいが、オーケストレーターはダイジェストしか持たないため
  観測と推論を区別できず、推論が事実として README に流れ込み、本スキルの中核規律を無効化する。導出値は
  `inferred: <値> (<根拠>)` と明示することが必須となり、根拠付きで書くかヘッジする扱いになった。
- **`/product:generate-frontend` — 再生成が上書きする旨を事前に告げるようになった。** 出力先自体は
  正しい（再実行での置換が前提だからこそ `adapt-change` がこのスキルを再実行する）が、再実行が出力先
  配下の手編集を破棄することへの警告が皆無だった。`adapt-change` が可逆性を担保している一方で、実際に
  書き込む当人が沈黙していた。上書きする旨を明示して確認を取り（`--auto` 時を除く）、`--out=<path>`
  による併存の選択肢を提示し、手で保守されるフロントエンドに育った時点で `generated/` の外へ移すべき
  ことを明記した。

### 追加
- **`skills/implement-backlog/output-location.test.sh`** — Output Location インターロックを挙動として
  検証。`reports/`・`generated/`・`work/` を含む通常の `.gitignore` を持つスクラッチリポジトリを構築し、
  `check-ignore` が `generated/` 配下の source root を拒否して該当ルールを提示すること、ワークツリー内の
  実在する `services/` root を受理すること、ドキュメントのコミットが `feature/<issue-id>-<slug>` に
  Issue 参照付きで着地し意図したファイルを stage すること、git が無視するパスでは何も stage されず
  コミットが空コミットではなく拒否されることを確認する。11項目、失敗時 exit 1。

### 変更
- 両 CHANGELOG のリンク参照ブロックが陳腐化していた — `CHANGELOG.md` は `0.8.2` で止まり、タグ付き13
  バージョンが未リンクな上、作成されたことのないタグを指す壊れた `[0.7.0]` リンクが存在し、
  `CHANGELOG_ja.md` には参照が1件も無かった。両方に既存タグと1対1対応する参照を揃えた。
- `docs/codex-gap-analysis_ja.md` の「80 skills」を **87**（architect 50 / product 26 / scalardb 11）に修正。

## [0.17.2] - 2026-07-26

### 修正
- **`/architect:generate-docs` — 領域の挿入と撤去が正確な逆操作になった。** 再実行テストにより、
  マーク付き領域の周辺空白が未定義であることが判明。撤去 → 再挿入で元のファイルが再現せず、
  サイクルを繰り返すたびに空白だけの差分ノイズが残っていた（レビュー可能であることが存在理由の
  ファイルにおいて実害がある）。規則を明文化 — 領域と前後は空行ちょうど1行で区切る（ファイル
  先頭/末尾に接する場合を除く）、撤去は領域＋後続の空行1つ（EOF 隣接なら直前の1つ）を取る、
  ファイル末尾は改行1つで空行2連続は作らない。規則を書く前に検証済み: この規則の下で、中間位置と
  EOF 隣接の両方について撤去 → 再挿入がバイト一致し、撤去/追加を5サイクル繰り返してもドリフト
  しない。

### 追加
- **`skills/generate-docs/marker-mechanics.test.py` — オーナーシップマーカー契約を挙動として
  検証。** SKILL.md はマーカー規則を散文で記述しているため、後の編集が再実行安全性を静かに壊し
  得た。5つの性質にわたる17項目を検査 — その場更新でマーカー外の散文がバイト単位で不変かつ領域が
  重複しないこと、再適用が no-op であること、撤去が他のコンテンツに触れないこと、安定キー一覧外の
  キーが更新・撤去の両方で拒否されること、挿入と撤去の往復がバイト一致し繰り返してもドリフト
  しないこと。埋め込みフィクスチャで自己完結して動作し、パスを渡せば実 README も検査可能。
  失敗時は exit 1（`hooks/*.sh` の CLI 規約に準拠）。

### 変更
- CLAUDE.md の検証に関する記述に本テストを追加し、陳腐化していたプラグインバージョンの記載
  （`0.15.0`）を削除。3プラグインが同一バージョンを共有し一括で bump される旨に改め、リリース
  フローにタグ作成と GitHub Release の手順を追記。

## [0.17.1] - 2026-07-26

### 修正
- **`/architect:generate-docs` — ドリフト所見の置き場と、生成セクションの撤去規則を追加。**
  実在の `/product:generate-frontend` スキャフォールドに対して本スキルを実行したところ、3つの
  欠落が判明した。
  - **Scaffold モードにドリフト所見の置き場が無かった。** Step 5 は「ユーザーに報告し Issue に
    追記」と規定していたが、Scaffold モードにはトラッカーが存在せず、実行時にセクションキーを
    その場で発明せざるを得なかった。安定キー一覧に `findings` を追加し、モード別の記録先を表で
    明示 — Delivery モードでは **Issue** にコメントとして追記（トラッカーが記録媒体であり、
    ドキュメントには書かない）、Scaffold モードでは **`findings` セクション**に記載。いずれの
    場合もドリフトを散文で解消してはならない（コードが行っていない整合をドキュメントが主張して
    しまうため）。
  - **撤去規則が無かった。** 後続の実行で正当性を失ったマーク付きセクション（解消済みのドリフト、
    削除されたサービス、消滅した対象面）は、マーカーごと削除して実行レポートに列挙する。古い
    生成セクションが残るのは、無いことより悪い。削除可能なのは安定キー一覧にあるキーのみで、
    手書きコンテンツには触れない。一覧外のキーの発明も禁止（次回実行時に領域を発見できなくなる）。
  - **git 管理外の対象で生の git エラーが出ていた。** Delivery モードは git ワークツリー外では
    コミットできない旨を明示し、リポジトリを必要としない Scaffold モードを提案するようにした。

  検証結果（マーカー無しの手書き README を対象）: 元の散文は 24/24 行が温存され、生成領域はすべて
  安定キーのマーカー内に収まり、検証工程は実プロジェクトに対してコマンド 6/6・パス 18/18 の実在を
  確認したうえで、当該 README の実在する記述不備を3件検出した。

## [0.17.0] - 2026-07-25

### 追加
- **`/architect:generate-docs` — 生成・実装されたコードのドキュメント（`architect` プラグイン、新規
  スキル）。architect プラグインは 50 スキルに。** コード生成スキルと `implement-backlog` が
  コードを出力する一方で、それを説明する README や `docs/` を作る工程が存在しなかった。本スキルが
  その工程を担い、両方の経路に定位置を持つ。
  - **2つのモード。** *Scaffold* は `generate-scalardb-code` / `generate-infra-code` /
    `/product:generate-frontend` の後に `generated/` を対象とし、コミットしない（再生成可能な
    領域のため）。*Delivery* は作業ブランチ上の解決済み `source_root` を対象とし、Issue 参照付きで
    コミットするため、コードと同じ PR/MR にドキュメントが載る — git に無視されるドキュメントは
    PR に到達できないため、`git check-ignore` とワークツリー内チェックを踏襲。
  - **その場での更新。** オーナーシップマーカー（`<!-- nexus:begin:<section> -->` …
    `<!-- nexus:end:<section> -->`）により再生成対象を本スキルが書いた領域のみに限定。人間が
    書いた散文は保持し、マーカーの無い手書き README は確認なしにその場で書き換えない。
    セクションキー（`overview`・`build-and-run`・`configuration`・`layout`・`api`・`operations`・
    `traceability`）は安定しており、再実行時は同じ領域を更新する。
  - **存在するものを書く。** 内容は実際のコード・ビルドファイル・設定から導出し、設計レポートは
    *why* のみを供給する。検証工程で、記載した各ビルド/実行/テストコマンドが実在するビルド
    ターゲットに裏付けられているか、リンクとパスが解決するかを確認し、コードのインベントリに
    無い設定キーやルートを排除し、設計とコードの乖離は散文で埋めず所見として報告する
    （Delivery モードでは Issue に追記）。
  - **コストティアリング実行。** ソースではなくダイジェストを保持する薄い sonnet オーケストレーター。
    コードのインベントリ化・設計意図の抽出・検証は haiku、ページ執筆はページ単位の並列 sonnet、
    opus は判断が重い設計解説（2PC 境界、整合性モデル、障害・復旧セマンティクス）のみ。

### 変更
- **`/architect:implement-backlog` — 実装コードを記録する Step 5b を新設。** 実装（Step 5）と
  レビュー（Step 6）の間で `/architect:generate-docs --scope=changed --source-root=<resolved>
  --issue=<iid>` を実行し、ドキュメント変更を同じ作業ブランチにコミットする。これによりコードと
  ドキュメントが1つの PR/MR でレビュー・マージされる。スキップはドキュメント対象の変更が無い
  場合に限り許容され、その理由を進捗コメントに記録する必要がある。サブエージェント割当表・
  Desired Outcome・Acceptance Criteria も併せて更新。
- **`/architect:deliver-backlog`** — ステージ (a) に、implement 工程が README/`docs/` の更新を
  同じ PR/MR へ運ぶことを明記。
- `generate-scalardb-code`・`generate-infra-code`・`/product:generate-frontend` から
  `generate-docs` への downstream 参照を追加。CLAUDE.md の manual extension tier に
  **コード生成 → `generate-docs`** の固定順序を記載。AGENTS.md のモデルティア・README.md・
  `docs/skill-reference{,_ja}.md` も同期。

## [0.16.2] - 2026-07-25

### 修正
- **`/architect:implement-backlog` — マージ対象のコードを `generated/` ではなくソースツリーへ出力。**
  本スキルが生成するのは成果物であり、コードは `feature/<issue-id>-<slug>` にコミットされ、
  `/architect:review-issue` が PR/MR でレビューし、`/architect:merge-issue` がマージする。にもかかわらず
  デフォルト出力が `generated/` だったため契約が矛盾していた — `generated/` は再生成可能な
  パイプライン出力であり、対象プロジェクトでは `reports/`・`work/` と併せて git-ignore される
  ことが多く、`git add` が黙って何も stage せず、空コミットによって実装 → レビュー → マージの
  連鎖が破綻し得た。新設の **Output Location** セクションで source root の解決順を定義
  （`--out` → `shared-context/decisions.md` に記録された `source_root` → 既存のリポジトリ
  レイアウト → グリーンフィールドではユーザー確認のうえ `services/{service}/`）し、解決結果を
  `decisions.md` に記録することで Epic 配下の全アイテムが同一の出力先を使うようにした。
  Step 4 では、コード書き込み前に 2 つの事前チェックを必須化 — `git check-ignore -q <source_root>`
  が exit 1（無視ルール不一致）であること（それ以外の exit は git エラーとして提示し、安全と
  みなさない）、および root が対象ワークツリー内に解決されること。Step 5 では実装サブエージェントを
  解決済み root 内に限定し（外部への書き込みが必要な場合はスコープを広げず停止して報告）、
  各コミットが意図したファイルを実際に stage したかを `git show --stat` で検証し、空コミットは
  レビューへ進めず Output Location へ差し戻す。`generated/` はワンショットのコード生成スキル
  （`generate-scalardb-code`・`generate-infra-code`・`generate-frontend`）用の意味を維持し、
  使い捨てスキャフォールドが目的の場合は `--out=generated/<service>/` で従来どおり選択できる。
  `templates/output-structure.md` と CLAUDE.md のコマンドリファレンスも新しい契約に同期。

## [0.16.1] - 2026-07-25

### 変更
- **`/architect:implement-backlog` — サブエージェントによるトークン最適化実行。** スキル本体を薄い
  **sonnet** オーケストレーター（従来は opus）とし、重い工程をモデルティア別サブエージェントへ委譲。
  新設の「Sub-Agent Execution & Model Assignment」セクションに割当を明文化: 共有コンテキストパックの
  導出は並列 sonnet（Step 1）、Epic・兄弟 Issue・設計レポートのダイジェスト化は haiku の Explore
  （Step 3）、Epic 横断契約に対するミニプラン起案は opus（Step 4）、実装はまとまり単位の sonnet
  （判断が重い設計のみ opus へ昇格、Step 5）、Epic 整合性判定とロールアップレビューは opus
  （Step 6）、進捗コメントと impl-log ミラーの下書きは haiku（Step 7）。コスト規則も明示化 —
  オーケストレーターはレポート本体ではなくダイジェストのみ保持し、各工程は足りる最安ティアを使用
  （opus は計画と整合性判断のみに限定）。AGENTS.md のモデルティア表と CLAUDE.md のコマンド
  リファレンスも同期（モデル切替のないランタイム向けにセッションモデルのまま委譲構造を維持する
  指針を追記）。

## [0.16.0] - 2026-07-24

### 追加
- **Backlog Delivery スキルファミリ（`architect` プラグイン、新規5スキル）** — 生成済みレポートを
  GitLab/GitHub 上のマージ済みコードまで届ける一連のワークフロー。**architect プラグインは 49 スキルに。**
  - `/architect:export-backlog` — product/architect のレポートから Epic（What/Why）→ Sub-Epic
    （What/Key Results）→ Issue（How）の3階層バックログを起票。レビューファースト
    （`reports/backlog/backlog-plan.md` + `backlog-manifest.json` を承認後にリモート書込）、冪等な
    再実行、GitLab ネイティブ Epic＋スコープドラベルのフォールバック、GitHub ラベル＋タスクリスト
    方式、全階層へのトレーサビリティ ID 引き継ぎ、全ノードへの `status::todo` 付与。
  - `/architect:implement-backlog` — Epic 全体の整合性を保ちながら選択アイテムを実装。親 Epic と
    同一 Epic 配下の兄弟を参照し、共有エンジニアリングコンテキストパック
    （`reports/backlog/shared-context/`: アーキテクチャガードレール・コーディング規約・ユビキタス
    言語・データ契約・NFR 予算・ADR-lite 決定ログ）と照合し、共有ブランチ契約
    `feature/<issue-id>-<slug>` 上で `generated/{service}/` にコードを出力。Epic/Sub-Epic/Issue へ
    進捗を追記し、軽量＋オンデマンド（`--review-epic`）の整合性レビューを実行。指定がなければ
    `status::doing` のアイテムをユーザー確認のうえ選択。
  - `/architect:review-issue` — 実装済み Issue を Epic 全体の観点（親 Sub-Epic/Epic＋関連 Issue）で
    レビューし、`[B]` ブロッカーは修正サブエージェントによる有界ループで自動修正
    （`--max-fix-rounds`＋無進捗検知。非収束時は Issue に「判断が必要」コメントを書き
    `status::blocked` にしてユーザーに確認）。ブロッカー解消後は Issue 紐付きの PR/MR を起票して
    承認待ちで停止。各ラウンドの指摘は重複排除されたプロジェクトナレッジベース
    （`shared-context/review-knowledge.md`、`KN-` エントリ）に蒸留され、以降の計画・実装が参照する。
  - `/architect:merge-issue` — 承認済み PR/MR を厳格なプレフライト（open・Mergeable 判定・承認・
    CI green・コンフリクトなし）と明示確認ゲート（スキップは `--yes-merge` のみ、プレフライトは
    スキップ不可）の背後でマージし、Issue をクローズ（`status::done` の単一権限）、Sub-Epic/Epic の
    進捗をロールアップ、Sub-Epic 完了時に Epic 統合レビューを起動。
  - `/architect:deliver-backlog` — Epic 配下の各 Issue を implement → review →（人間の承認）→
    merge の順に駆動する半自律オーケストレーター。`backlog-manifest.json` から再開し、人間ゲートで
    ハード停止。`--yes-merge` なしでは自動マージしない。
- **共通ステータス語彙** — `status::todo/doing/review/done/blocked`（GitHub は `status:` 形式）を
  ファミリ全体で共有。export-backlog が seed し、下流スキルが遷移させる。

## [0.15.0] - 2026-07-15

### 追加
- **`architect` プラグイン: `/architect:estimate-token-cost` スキル** — architect パイプラインを
  コードベースに対して実行した場合のトークン使用量と USD コストを見積もる。事前見積もりモデル
  （コード行数 → 取り込みトークン → キャッシュ調整後の課金入力、typical/low/high の3バンド）と、
  `work/token-usage.json` の実測値による較正（部分実行時は残フェーズを外挿）を組み合わせる。
  インフラ・ライセンス・運用コストを扱う `/architect:estimate-cost` とは別物。
  **architect プラグインは 44 スキルに。**
- **フェーズ別トークン使用量の自動記録（`hooks/record_token_usage.py`）** — フェイルセーフな
  フック（`Write|Edit|MultiEdit|Task|Agent` の `PostToolUse` と `Stop`/`SubagentStop`）が
  セッショントランスクリプトを差分解析し、課金トークン（入力/出力、キャッシュ読み、5分/1時間
  キャッシュ書き込み、Web検索リクエスト）をパイプラインフェーズに帰属させる：`in_progress`
  フェーズ優先、次に新たに `completed` へ遷移したフェーズ（保留バケットを回収）、いずれも
  なければターン終了時に `_unassigned`。`work/token-usage.json`（フェーズ×モデル台帳 + USD）と
  `work/token-usage.jsonl`（追記専用監査ログ）を出力。初期化済みパイプラインプロジェクト外では
  不活性。並列サブエージェントの発火は flock で直列化し、message id はチャンク境界をまたいで
  重複排除。
- **`skills/common/references/model-pricing.json`** — モデル価格（期間限定の導入価格を含む）、
  キャッシュ倍率、サーバーツール価格、事前見積もりヒューリスティクスの単一ソース。記録フックと
  見積もりスキルが共有する。
- **`rules/token-pricing.md`** — 台帳スキーマ（`token-usage-v2`）、帰属の意味論と注意点、
  見積もり手法、サブスクリプション課金と API 課金の違いを記載。`CLAUDE.md` の Rules & References
  表から参照。

## [0.14.0] - 2026-07-13

### 追加
- **インプット要件ガイド（`docs/product-input-requirements.md`・
  `docs/architect-input-requirements.md`、EN/JA）** — 各プラグインのパイプラインを実行する際に
  利用者が用意すべき情報をまとめたドキュメント（エントリーポイント、必須／推奨インプット、
  対話モードと `--auto` モード、フェーズごとのヒアリング項目、product→architect のハンドオフ）。
  README・`getting-started`・`skill-reference`・`AGENTS.md`・`CLAUDE.md` からリンク。

## [0.13.0] - 2026-07-07

### 追加
- **`product` プラグイン: `/product:name-product` スキル** — プロダクトを**アルファベット・アクロニム**として
  命名する：各文字が英単語の頭文字になる短く発音可能なラテン文字名で、名前自体が価値フレーズに展開される。
  ビジョン/ポジショニングに根ざして候補を絞り込み、1 案を推奨する。任意実行（`full` プロファイルに含む）。
  新ルール `rules/product/naming-frameworks.md` を追加。**product プラグインは 26 スキルに。**
- **Omnigent 互換レイヤー** — `OMNIGENT.md` とローダー（`tools/omnigent/load-skill.sh`）により、
  汎用マルチエージェント・オーケストレーターが約 90 個の `SKILL.md` を無改変で実行できる。ローダーは
  `plugin:skill` 名をファイルパスに解決し、翻訳プリアンブルを出力し、`${CLAUDE_PLUGIN_ROOT}` を展開する。
  非侵襲（スキルファイルの変更なし）でテスト付き。

### 変更
- **`AGENTS.md` のモデル階層推奨を現行の product 26 スキルに同期**（16 opus / 10 sonnet）。各スキルの
  `model:` frontmatter と両依存マニフェストに一致。

### 修正
- **入れ子 migrate サブスキルの陳腐化フラットパス（12 ファイル 30 箇所）** — 実行可能な `cd` ブロック、
  Related Skills、出力ツリー、抽出スクリプトのコメントが入れ子化前のパス
  （例: `skills/analyze-mysql-schema/...`。正しくは `skills/migrate-mysql/analyze-mysql-schema/...`）を
  参照していた。
- **ドキュメントのドリフト**: README のスキル数を修正（77 → 80）。CLAUDE.md のモデル階層表を修正
  （`analyze` = opus、`report` = haiku）し、product の階層リストを全 26 スキルに補完。CLAUDE.md に
  `/product:design-architecture` を追加。スキルリファレンス（EN/JA）に `/product:create-domain-story` と
  `/product:design-system` を追加。`generate-ui-mock` の説明を実際の駆動源（ドメインストーリー +
  デザインシステム）に更新。
- **パイプラインの範囲を明確化**: `skill-dependencies.yaml` 外の architect 12 スキル（インフラ、
  セキュリティ、オブザーバビリティ、DR、実装、コード生成、コスト見積、セキュリティ調査）を
  `/architect:pipeline` が実行しない**手動拡張ティア**として明記し、pipeline スキルの「全スキル」の
  記述を実態に合わせて修正。
- **product→architect ブリッジ成果物を受け手側で宣言**: `design-microservices` が `architecture.md` /
  `tech-stack-fitness.md` を、`design-api` が `api-design.md` を任意入力として明記（再導出でなく
  リファインするセマンティクス）。
- レビューフェーズの `parallel_with` 宣言を対称化。見出しを `Desired Outcome` / `Decision Criteria` に
  正規化（5 スキル）。scalardb ユーティリティ 5 スキルの説明に「Use when」トリガーを追加。`workflow/` と
  `research/` に位置づけ README を追加。README にドキュメント言語ポリシーを追加。Codex 監査ドキュメントに
  時点スナップショット注記を追加。getting-started（EN/JA）に `samples/ec-monolith` の導線を追加。
  define-requirements の brainstorm ドキュメントの陳腐化した `research/` ファイル名を修正。

### ドキュメント
- getting-started ガイド（EN/JA）に `/product:generate-frontend` を掲載。

## [0.12.0] - 2026-06-29

### 追加
- **`product` プラグイン: `/product:generate-frontend` スキル** — ナビゲート可能な UI モックとアクティブな
  デザインシステムから、**実行可能な React + TypeScript フロントエンド**を `generated/frontend/` に生成する。
  画面を **Atomic Design** で分解し（デザイントークン → atoms → molecules → organisms → templates → pages）、
  デザインシステムの各 `CMP-` を対応する原子レベルのコンポーネントに、各 UI モック画面をページにする。
  コンポーネントは **CSS Modules + CSS 変数**でスタイリングし、デザイントークンのみを参照する（生値は使わない）。
  ストーリーフロー（`next`/`prev`）は **react-router** で配線し、各コンポーネントを **Storybook** に variant/state
  ごとの story として登録する。自己完結でインストール可能な scaffold（React 18 + Vite + Storybook 8 + TS）を出力する。
  新ルール `rules/product/atomic-react-storybook.md` を追加。トレーサビリティに `COMP-`/`PAGE-` ノードを
  `CMP-`/`TOK-`/`STORY-` への Upstream 参照付きで記録する。spec フェーズの `generate-ui-mock` の後に実行する。
  **product プラグインは 25 スキルに。**

### 変更
- **`product` プラグイン: `/product:start` が `generate-frontend` を選択式ステップとして提示**するようになりました。
  UI モックの後に、実行可能な React + Storybook フロントエンドを生成するか対話的に尋ね（インタラクティブ）、
  `--auto` ではプロファイルに従う（`ux-to-spec` / `full` に含まれる）。新フラグ `--frontend` / `--no-frontend` で
  選択を強制でき、決定は `work/pipeline-progress.json` → `options.frontend` に記録する。このステップは非ブロッキングで、
  後続フェーズは生成コードではなくモックを参照する。

## [0.11.0] - 2026-06-26

### 変更
- **`product` プラグイン: `/product:generate-ui-mock` がクリックで遷移できるナビゲート可能なプロトタイプを生成**
  するようになりました。これまでの画面が独立した単一 HTML ファイル群だった状態から、ドメインストーリーの
  番号付きアクティビティ順に画面を並べ、各画面の「フローを前進させるアクション」を次のアクティビティの画面への
  実際の `<a href>` リンクにします。これにより、ストーリー全体をクリックで端から端まで辿れます。各画面には
  戻る/次へのナビゲーションと `step N of M` 表示、分岐は対象画面へのリンク、ストーリーごとのフローインデックス
  （`{STORY}-index.html`）を入口として追加します。ファイル名は決定論的（`{STORY}-NN-{slug}.html`）で、ソースに
  欠けているステップは無効化した `TBD` リンクとして表示します（デッドエンドは作りません）。トレーサビリティに
  画面間の `next`/`prev` エッジを記録します。

## [0.10.0] - 2026-06-24

### 追加
- **`product` プラグイン: `/product:create-domain-story` スキル** — ペルソナ起点のドメインストーリーテリング。
  アクターはペルソナ（`PER-`）、アクティビティはジョブストーリー（`JOB-`）をジャーニー（`JNY-`）順に並べたもの、
  ワークアイテムは扱う対象から導出する。各ストーリーは「あるペルソナが主要ジョブを遂行する」ハッピーパスの
  シナリオで、ペルソナ×ジョブ単位でスコープする（境界づけられたコンテキストは `--domain` による任意の拡張）。
  UX フェーズの、ジャーニー／ポジショニングの後・UI モックの**前**に実行し、`reports/01_ux/domain-stories/` を
  `STORY-` トレーサビリティ付きで出力する。`/architect:create-domain-story` の product パイプライン版。
- **`product` プラグイン: `/product:design-system` スキル** — **分離管理**のデザインシステムを構築または
  `--import` で取り込む。構築はポジショニング／ペルソナ／ビジョンから **W3C DTCG** トークン
  （color/type/spacing/radius/elevation/motion）を WCAG コントラストゲート付きで導出。`--import` は既存システム
  （Tailwind config / DTCG JSON / Figma Tokens / CSS テーマ）を同一スキーマへ正規化する。出力は `reports/` 配下では
  なく専用の `design-system/<name>/` ツリーに置き、semver の `manifest.json` を持ち、複数の名前付きシステムを
  併存でき、**standalone**（いつでも単独実行可能）。アクティブなシステムは
  `work/pipeline-progress.json` → `options.design_system` に記録する。新ルール
  `rules/product/design-system.md` を追加。**product プラグインは 24 スキルに。**

### 変更
- **`/product:generate-ui-mock` がストーリー駆動＋デザインシステム適用に** — 画面は各ペルソナ×ジョブの
  ドメインストーリーから導出し（1 アクティビティ ≒ 1 画面操作）、アクティブなデザインシステムでスタイリングする。
  各 self-contained 画面に `tokens.css` をインライン注入し、`--fidelity=lo`（トークンのみ）または
  `mid`（トークン＋`CMP-` コンポーネントスタイル）で描画する。システム未設定時はアドホックな lo-fi へフォールバック。
  画面は `STORY-`/`CMP-` もトレースする。
- **UX フェーズの順序** — `full` プロファイルで `create-domain-story` と `design-system` をポジショニングの後・
  `generate-ui-mock` の前に実行し、モックが「選択された流れ」を「共有の視覚言語」で描けるようにした。

## [0.9.0] - 2026-06-24

### 追加
- **`product` プラグイン: `/product:design-architecture` スキル** — 境界づけられたコンテキスト・
  API レイヤー・データモデル・非機能要件を統合してランタイムの全体アーキテクチャを生成し（Mermaid の
  構成図 / クリティカルパス / デプロイ・スケーリングの 3 ビュー）、定型チェックリスト
  **Kong（API Gateway）・ScalarDB・ScalarDB Analytics・ScalarDL** に対する**技術適合度評価**を
  成果物の根拠に基づいて実施。各技術に **採用 / 条件付き採用 / 不採用** の判定と採用理由・配置を出力する。
  ScalarDB / ScalarDL の「採用」は architect プラグインの ScalarDB パイプラインへの橋渡しとなる。
  出力は `reports/03_domain/architecture.md` と `reports/03_domain/tech-stack-fitness.md`。
  `full` プロファイル（`define-nfr` の後の総合ステップ）と依存グラフに追加。新ルール
  `rules/product/architecture-and-tech-fitness.md` を追加。product プラグインは 22 スキルに。
- **product → architect ハンドオフ契約（`docs/design.md`）** — `product` の成果物が `architect`
  プラグインのインプットとしてどう橋渡しされるかの単一の真実。4 つの SKILL/ルールファイルで宙吊りに
  なっていた `design.md` 参照を解消。成果物マッピング（成果物ごとの ID 接頭辞 → `define-requirements`
  の成果物、§1.3）、`product` が供給しない設計上のギャップ（§1.4）、クロスプラグインの
  **トレーサビリティ書き戻し**契約（`FEAT-→FR-` リンク、`NFR-` の verbatim 再利用、§1.5）、
  正典の**適応エンジン**仕様（§7）を定義。

### 変更
- **`/architect:define-requirements` が product 成果物を取り込む** — `reports/0*_*/` の product
  レポートを自動検出し、product の ID を引き継ぎ、`tech-stack-fitness.md` を ScalarDB 適用判定の
  prior として利用し、`FR-`/`NFR-` ノードを `work/traceability.json` へ書き戻す。
- **`/architect:start`・`/architect:pipeline` の product 認識** — 前段でハンドオフ検出を行い、
  product レポートを渡してグリーンフィールドパスへ誘導する。
- **`/product:map-domains`** が `CTX-` ごとに粗い整合性ヒント（`Strong`/`Eventual`/`TBD`）を出力し、
  architect のトランザクション整合性分類の起点とする。
- **`/architect:review-consistency`** がクロスプラグインのトレーサビリティ継続性を検査する。

## [0.8.2] - 2026-06-20

### 変更
- 3 プラグインのバージョンを 0.8.2 に更新。

### ドキュメント
- これまで architect の 43 スキルのうち 41 件しか記載していなかった
  `create-domain-story`（設計）と `review-report`（レポート）を `README.md` および
  スキルリファレンス（en/ja）に追加。
- `/architect:pipeline` のフラグ記載を実態に合わせて修正
  （`--resume-from`・`--rerun-from`・`--skip-{phase}`・`--no-scalardb`・`--lang`）。
- Getting Started / Codex 利用ガイド（en/ja）に `product` プラグインの導線を追加：
  「プロダクトの方向性（グリーンフィールド）」の起点、`/product:*` のスキルマッピング
  （`skills/product/<name>/SKILL.md`）、product のインストールコマンドを追記。

## [0.8.1] - 2026-06-20

### 修正
- `product:` / `scalardb:` 名前空間のスキルが読み込まれないプラグイン名前空間の衝突を修正。
  マーケットプレイス マニフェストで各プラグインに明示的な `skills[]` 配列を持たせ、
  各プラグインが自身のコマンドのみを登録するようにした。

## [0.8.0] - 2026-06-20

### 追加
- **`product` プラグイン**（21 スキル、14 ルール）— プロダクトビジョンから SLA/NFR までを
  対話的・検証駆動で進めるプロダクト方向性パイプライン。深い設計の前に最もリスクの高い前提を
  抽出・検証し、トレーサビリティグラフで変更を再伝播し、システム実装設計のために
  `/architect:define-requirements` へ引き継ぐ。

これにより Nexus Architect は 3 プラグイン構成（`product`・`architect`・`scalardb`）、
合計 75 スキルのツールキットになりました。

## [0.7.0] - 2026-06-11

### 追加
- グリーンフィールドの起点となる `/architect:define-requirements` スキル：機能/非機能要件の
  分類、データ・トランザクション要件分析、ScalarDB 適用判断。`--input`・`--auto`・
  `--no-scalardb` をサポート。

## [0.6.2] - 2026-06-11

### 追加
- ドメインストーリーテリング用の `/architect:create-domain-story` スキル
  （ドメインごとの業務プロセスを可視化）。
- 生成された HTML レポートの品質をレビューする `/architect:review-report` スキル。
- ツールキット検証用の `ec-monolith` サンプルプロジェクト。

### 修正
- フック・スキル・マニフェスト全体のエージェント構成監査の指摘を解消。
- Mermaid バリデータのブロック解析を修復し、ユビキタス言語の用語整合ルールを追加。
- `investigate` スキルに計算手順と自己検証を追加。

## [0.6.1] - 2026-05-12

### 追加
- レビュー・評価スキルでの並列サブエージェント実行。
- スキーマレポート後の `migrate-oracle` SA3/SA4/SA5 ステージの並列化。

### 修正
- 28 ファイルにわたる多視点レビューの修正。
- 移行パイプライン全体のスキル呼び出しとネストされたサブスキルパスを修正。

## [0.6.0] - 2026-05-07

### 追加
- Codex 互換レイヤー（`AGENTS.md`）：Claude Code プラグインをインストールせずに
  同じスキルファイルを Codex から利用可能に。

### 修正
- `/architect:` プレフィックス登録を有効にするため、全 SKILL.md から `name` フィールドを削除。
- スキル監査の指摘（マニフェスト命名、フロントマター、JDBC パターン）を解消。

## [0.5.0] - 2026-03-24

### 変更
- ScalarDB 開発スキルを独立した `scalardb` プラグインに分離。

## [0.4.0] - 2026-03-23

### 追加
- データベース移行（Oracle / MySQL / PostgreSQL → ScalarDB）：スキーマ抽出、移行分析、
  ストアドプロシージャ/トリガーの Java 変換。

## [0.3.0] - 2026-03-23

### 追加
- ScalarDB アプリケーション開発スキル（スキーマモデリング、設定、CRUD/JDBC パターン、
  スキャフォールド、コードレビュー、移行アドバイザリ）。

## [0.2.0]

### 変更
- リポジトリを Claude Code プラグイン互換の構成に再編。

[0.22.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.22.0
[0.21.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.21.2
[0.21.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.21.1
[0.21.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.21.0
[0.20.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.20.0
[0.19.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.19.0
[0.18.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.18.0
[0.17.4]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.4
[0.17.3]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.3
[0.17.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.2
[0.17.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.1
[0.17.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.0
[0.16.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.16.2
[0.16.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.16.1
[0.16.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.16.0
[0.15.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.15.0
[0.14.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.14.0
[0.13.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.13.0
[0.12.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.12.0
[0.11.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.11.0
[0.10.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.10.0
[0.9.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.9.0
[0.8.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.2
[0.8.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.1
[0.8.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.0
[0.6.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.2
[0.6.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.1
[0.6.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.0
[0.5.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.5.0
[0.4.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.4.0
[0.3.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.3.0
