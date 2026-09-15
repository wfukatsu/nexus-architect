---
title: "既存DB調査スキル：設計資料・実DB接続と拡張可能なアダプタ"
schema_version: 1
skill: skill-creator
type: feat
status: completed
date: 2026-09-14
---

# 既存データベース調査スキルの実装計画

## 1. 目的と承認範囲

Oracle、PostgreSQL、MySQL の既存データベースを、設計資料と実DB接続の2経路で調査する。入口は2スキル、調査結果の契約と評価基準は共通、製品固有の処理は追加可能なアダプタとする。

この文書はリポジトリ調査と公式資料の確認に基づき作成し、2026-09-15にユーザーが承認した実装計画である。同日、2スキル・共通契約・3製品アダプタを実装し、Docker Desktop上の隔離DBで検証した。結果と対応範囲は [検証記録](2026-09-15-database-investigation-validation.md) を参照。

初回は独立した architect スキルとして提供する。ScalarDB 移行は前提にせず、既存の移行スキルを置換しない。自動パイプラインへの組み込み、継続監視、DDLと実DBの自動差分判定は後続拡張とする。

## 2. 調査結果

### リポジトリで確認した事実

| 対象 | 現状 | 今回への示唆 |
|---|---|---|
| `skills/investigate/SKILL.md` | コードベース、技術スタック、技術負債、DDD準備状況の調査 | DB単体の入力・成果物を持つ入口が必要 |
| `skills/analyze-data-model/SKILL.md` | エンティティ・関連・正規化・インデックス・ER図を分析 | 共通調査結果の後続利用先とする |
| `skills/migrate-{oracle,postgresql,mysql}/analyze-*-schema/` | 製品別の抽出スクリプト、スキル、レポート書式がある | 取得項目とSQLの参考にするが、共通契約は新設する |
| Oracle抽出器 `execute_sqlplus` | SQL*Plus経由、接続文字列をコマンド引数に渡す | 新経路は認証情報をargvへ載せない接続方式を設計する |
| PostgreSQL抽出器 `execute_psql` | psql経由、区切り文字による出力解析、一部の不存在エラーを空配列化 | 型・改行・区切り文字の保持、取得状態の区別が必要 |
| MySQL抽出器 `execute_query` | Python connector経由、接続・問い合わせエラーを空配列化 | 空集合と失敗を共通の取得契約で区別する |
| `.claude-plugin/marketplace.json` | architect の公開スキルを明示列挙 | 2スキルの登録が必要 |
| `tools/docs_consistency.test.py` | 登録スキル、日英カタログ、呼び出し形式の整合性を検査 | カタログも同時に更新する |
| `tools/run-tests.sh` | `*.test.py` / `*.test.sh` を自動検出 | 新規の動作テストを既存ランナーへ自然に接続できる |

既存抽出器をそのままラップする案は、認証・エラー・出力の差異を残すため採用しない。全抽出器を今回置換する案も、既存移行の挙動まで変更するため採用しない。新しい共通基盤を小さく追加し、既存SQLは出典と取得条件を確認して必要なものだけ移植する。

### 公式資料から確認した制約

- Oracle のテーブル統計には最終解析時刻や統計の状態があり、現在の件数と同一視できない。[ALL_TAB_STATISTICS](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/ALL_TAB_STATISTICS.html)
- PostgreSQL の累積統計には更新遅延、トランザクション内キャッシュ、リセットがある。単一取得のカウンタからレートや長期傾向は断定しない。[Cumulative Statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- PostgreSQL の `pg_stats` には頻出値やヒストグラム境界値が含まれる。メタデータ照会であっても実データ由来の値を取得し得る。[pg_stats](https://www.postgresql.org/docs/18/view-pg-stats.html)
- MySQL の InnoDB `TABLE_ROWS` は概算で、INFORMATION_SCHEMA の統計はキャッシュされる場合がある。[INFORMATION_SCHEMA TABLES](https://dev.mysql.com/doc/refman/8.4/en/information-schema-tables-table.html)
- Oracle の AWR 等には管理パックの利用条件がある。初期収集から除外し、将来追加する際は対象版・契約の確認を要件にする。[Licensing Information](https://docs.oracle.com/en/database/oracle/oracle-database/19/dblic/Licensing-Information.html)

上記の資料の版は調査根拠であり、対応版の保証範囲や新規依存のバージョン指定ではない。実装時には対象版別のSQL・ドライバ互換性を確認し、実際に検証した組み合わせを明記する。

## 3. 提供する2スキル

| スキル（提案名） | 入力 | 調査範囲 |
|---|---|---|
| `/architect:investigate-db-design` | DDLファイル群、スキーマのテキストエクスポート、Markdown/CSV等の設計資料 | テーブル・列・型・制約・インデックス・関連・ビュー・ルーチン等の設計上の構造、設計上の懸念 |
| `/architect:investigate-db-live` | 接続プロファイル、製品、対象DB/スキーマ、収集範囲 | ディクショナリの実構造、件数推定・容量・インデックス利用等の既存統計、取得制限 |

両スキルはコードベース調査やScalarDB版の指定なしで起動できる。設計資料側はネットワーク接続不要。PDF・画像・バイナリ形式の専用変換器は初期対象外とし、読み取り可能なテキスト入力へ変換して利用する。

入力時に製品・版（判明範囲）・対象スキーマ・資料の基準時点または調査環境を確認する。版が分からないDDLに最新版の構文を無条件適用せず、版依存の判断を保留する。実DBでは接続後に製品と版を検出し、指定と相違すれば停止して確認する。MySQL互換製品等を自動的に同一製品として扱わない。

設計資料間に矛盾がある場合は、出典ごとに保持して確認する。静的資料から行数・利用頻度・性能を創作しない。FK宣言による関連と、名前等から推測した関連を別に記録する。

## 4. 共通基盤とアダプタ契約

配置案（ファイル名は実装時に既存命名と調整可能）：

```text
skills/investigate-db-design/SKILL.md
skills/investigate-db-live/SKILL.md
skills/common/database-investigation/
  contract.md
  inventory.schema.json
  adapters/
    registry.json
    oracle/       # adapter.json、設計構文ガイド、取得SQL、公式根拠
    postgresql/
    mysql/
  scripts/
    investigate.py
    core/         # 型、検証、出典、接続ポート、実行制御
    adapters/     # 製品別Python実装
  tests/          # 共通契約テスト、3製品の入力・期待結果
templates/database-investigation/  # 調査報告・ER図のテンプレート
rules/database-investigation.md
```

共通基盤は製品名の分岐を持たず、registry の明示登録からアダプタを選択する。入力資料や接続プロファイルに指定された任意のPythonモジュールはロードしない。

アダプタが担う機能：

1. `capabilities`：設計/接続モード、対象機能、版条件、必要権限、取得の根拠資料を宣言する。
2. `parse_design`：対応するDDLの構造化と、未対応文・未解決参照の返却。
3. `probe`：製品・版・接続対象・閲覧可能範囲・利用可能な取得機能の確認。
4. `collect_metadata` / `collect_statistics`：固定された問い合わせ定義を実行し、出典付きの結果を返す。
5. `normalize`：製品固有の識別子・型・統計を共通形式に変換し、固有情報は `extensions` に保持する。

接続・タイムアウト・出力先・記録・マスキングは共通層へ置く。実DB接続ポートにはFakeを用意し、時刻とrun IDの生成を注入可能にする。型名や識別子を破壊的に小文字化しない。Oracleの所有者、PostgreSQLのdatabase/schema、MySQLのdatabaseの違いをモデルに保持する。

アダプタの新規追加は「宣言・製品実装・資料/SQL・fixture・契約テスト」を追加してregistryへ登録する手順とする。第4の架空アダプタのテストで共通コードに変更不要なことを確認する。外部パッケージ配布機構までは作らない。

### 共通データ形式

- 実行：`schema_version`、`run_id`、入力モード、製品/版、対象、開始・終了時刻、完了状態。
- オブジェクト：catalog/schema/name/kind に基づく衝突しないID、列・型・順序、PK/FK/UNIQUE/CHECK、インデックス、ビュー、ルーチン、トリガー、製品固有要素。
- 証拠：入力ファイル・ハッシュ・行範囲、またはquery ID・取得時刻・対象範囲。レポートの指摘は証拠IDを参照する。
- 統計：値、単位、粒度、推定/実測/累積の区別、収集時刻、統計更新時刻/リセット時刻（取得できる場合）、適用範囲。
- 収集状態：`ok` / `empty` / `permission_denied` / `unsupported` / `disabled` / `timeout` / `error` / `not_collected`。途中打ち切りは件数と `truncated` も記録する。
- 観測した事実、資料に記載された内容、推論、未解決事項を区別する。情報不足を空配列・ゼロ・「問題なし」に変換しない。

部分取得は `partial` として報告できるが、接続失敗や対象確認失敗を完了扱いにしない。全体の終了コードは成功0、部分取得2、致命的失敗1とする案で実装・テストを揃える。

## 5. 初期調査範囲

### 設計資料モード

初期の自動構造化は CREATE TABLE、列定義、PK/FK/UNIQUE/CHECK、CREATE INDEX、COMMENT、ALTER TABLEによる制約追加を中心とする。複合キー、引用識別子、スキーマ修飾、複数ファイル間の参照に対応する。

文分割ではOracleのブロック終端、PostgreSQLのdollar quote、MySQLのDELIMITERを区別し、単純なセミコロン分割や正規表現だけで完全解析したとみなさない。ビュー・ルーチン・トリガー等は少なくともオブジェクトと定義の出典を記録し、依存解決の対応範囲を明示する。

自動抽出を越える設計書の読解・評価はスキルが行い、JSON Schemaと出典照合で成果物を検証する。完全な汎用SQLパーサーは作らず、未対応構文は入力位置とともに残す。マイグレーション履歴は実行順序・基準状態が指定された場合のみ状態を再構成し、単なるDDL集合を現行スキーマと断定しない。入力DDLやクライアントメタコマンドは実行しない。

### 実DBモード

| 製品 | 構造情報の取得元候補 | 初期統計の取得元候補 | 主な制限 |
|---|---|---|---|
| Oracle | USER_/ALL_ の表・列・制約・索引・ビュー等。追加権限がある場合のみ必要なDBA_ビュー | 表/索引の既存統計、参照可能なセグメント容量 | CDB/PDB・所有者を識別。DBA権限を必須にしない。AWR/ASH/ADDMは対象外 |
| PostgreSQL | pg_catalog、information_schema、定義取得関数 | pg_stat_user_tables/indexes、容量取得関数、値を含めない選択済み列統計 | 拡張導入や統計設定変更は行わない。リセット・可視範囲を記録 |
| MySQL | information_schema の表・列・制約・索引・ビュー等 | TABLES の推定件数/容量、利用可能な場合に限定したperformance_schemaの集計 | ストレージエンジンと統計収集状態を記録。監視機能を有効化しない |

固定のSELECTと必要なセッション制御を、最小権限の接続で実行する。ドライバ接続を基本案とし、既存CLI抽出の区切り文字パースには依存しない。ドライバは対象製品分のみ導入できる構成とする。Oracle Wallet等の既存認証方式との適合も検証する。

対象スキーマを必須で絞り、バインド変数、取得行数上限、接続/問い合わせ/全体のタイムアウトを設ける。クライアントの待機打ち切りだけでなく、可能な範囲でサーバー側の停止・キャンセルと接続解放を検証する。

業務テーブルのサンプル取得、COUNT(*)による全件走査、ANALYZE、DBMS_STATS、EXPLAIN ANALYZE、DDL/DML、監視設定変更を収集処理へ含めない。認証情報をチャット・argv・レポート・Git管理ファイルへ出力しない。接続情報は既存の安全な認証機構または環境変数参照を使う。TLS検証を無条件に無効化しない。

頻出実値・ヒストグラム境界・SQL本文・リテラルは既定で収集しない。定義に含まれる秘密やリテラルにも注意し、未加工の問い合わせ結果を自動で保存しない。単一スナップショットの利用回数0から「削除してよい索引」と結論しない。

## 6. 成果物と既存スキルへの接続

`reports/01_analysis/database-investigation/<target-id>/<mode>/<run-id>/` 配下へ保存する。

| ファイル | 内容 |
|---|---|
| `inventory.json` | 共通形式の構造・統計・出典・取得状態 |
| `investigation-report.md` | 範囲、調査結果、問題候補と根拠、限界、次の調査候補 |
| `er-diagram.md` | 確認済み関連のER図。大規模時はスキーマ単位で分割 |
| `collection-summary.json` | 機能別の成功/失敗/未取得、時間、打ち切り、アダプタ識別情報 |

run単位で保存し、設計資料と実DBや再実行の成果物を上書きしない。Markdownには必須frontmatterと既存の出力言語設定を適用する。

`analyze-data-model` に任意入力として上記成果物の利用方法を追加する。複数runがある場合は入力を明示し、DDLと実DBを黙って合成しない。初回は `skills/common/skill-dependencies.yaml` を変更せず、既存pipelineの必須条件も増やさない。

未解決事項は既存の `work/context.md` に既存OQ番号と衝突しないよう追記する。新たな独立Open Questionsストアを作らない。共有の進捗・traceabilityを初期化しない。

## 7. 実装手順と完了条件

| 段階 | 実施内容 | 検証・完了条件 |
|---|---|---|
| 1. 契約 | 共通モデル、取得状態、アダプタ宣言、出典、fixtures、受入シナリオ | 3製品の例を同じ契約で表現し、未知・空・失敗を区別できる |
| 2. 設計資料 | designスキル、DDL処理、資料読解手順、3アダプタの静的部分 | 複合キー・引用符・コメント・ブロック・未対応構文・複数ファイルの動作テスト |
| 3. 実DB | liveスキル、接続ポート/Fake、製品判定、取得SQL、版/権限別能力判定 | Fakeで障害系、実DBで各製品の構造/統計取得を検証 |
| 4. レポート | 共通正規化、出典付き報告、ER図、部分成功の表示 | 同等DDL/実DB fixtureの共通構造一致、統計の推定と時点の保持 |
| 5. 公開・接続 | marketplace、日英skill-reference、必要な概要/入力ガイド、analyze-data-modelの任意入力 | 登録・日英呼び出し形式・参照整合性の既存テストが通る |
| 6. 品質確認 | 新規動作テスト、既存全テスト、静的検査、依存検査、ドキュメント検証 | 8段階の証跡と、未実施の理由を記録。FAILを残して実装完了としない |

ロジック追加は失敗するテストから着手し、適用対象の実装単位でRed → Green → Refactorと実行証跡を残す。既存抽出器は変更しないため、その移行・置換に伴う特性テストは今回不要。

### 受入シナリオ

1. 各製品のDDLからテーブル・列・複合制約・索引を抽出し、全オブジェクトを出典へたどれる。
2. DDL内のコメント、改行、引用符、ルーチン内セミコロンで後続オブジェクトが消失しない。
3. 不明な構文・版・外部参照を、対応済み・不存在として扱わない。
4. 実DBの権限不足・統計無効・タイムアウト・0件がそれぞれ異なる結果になる。
5. 読み取り可能範囲が制限された接続で、可視範囲外のオブジェクトを「存在しない」としない。
6. 実データ由来の統計値や認証情報が、出力・エラー・コマンドラインに漏れない。
7. scope外のスキーマを収集せず、部分失敗でも取得済み証拠を保持し、接続を閉じる。
8. 第4アダプタを登録し、共通実行コードを変更せずロード・正規化・報告できる。
9. 既存移行の登録と既存成果物を維持し、既存テストが回帰しない。

### 検証環境と証跡

ローカルのfixture/Fakeテストは全製品で実施する。実DBテストは隔離されたOracle/PostgreSQL/MySQLで、基本スキーマ・制限された権限・既存統計を使う。環境未提供やOracle実行環境を用意できない場合は、その製品の実DB検証を未実施として明記し、「3製品接続確認済み」とはしない。Fakeは実DB検証の代わりにしない。

8段階は build（Python構文/パッケージ検査）、unit、adapter contract、実DB integration、SAST、dependency scan、API security、design↔code conformance を記録する。HTTP APIを追加しないためAPI securityは対象外の理由を記録し、接続・SQL・秘密情報の安全性はSAST/動作テストで別途確認する。

依存パッケージやテストDBイメージを固定する直前にレジストリから版を調べ、互換性とサポート状態を確認し、`work/version-decisions.json`へ追記する。確認方法は既存の `options.confirm_versions` と `--confirm-versions` / `--no-confirm-versions` の規則に従う。この計画では未確認の依存版を固定しない。

Markdown成果物は `hooks/validate-frontmatter.sh` と `hooks/validate-mermaid.sh` で検証する。公開前に `tools/run-tests.sh` と `git diff --check` を実行し、実DB検証の製品・版・権限・実行日時を別途記録する。

## 8. 承認する内容

承認対象は「2つの独立したarchitectスキル、共通契約と3製品のアダプタ、必要な実行補助コード、動作テスト、既存カタログと任意入力の更新」である。上記1〜6の順序で実装し、全体の自動pipeline化や既存移行器の置換は行わない。

承認時点で製品別の実接続情報は不要。実装後の接続検証で環境が必要になった時点で確認する。

## 9. 実装時の調整

- アダプタの取得機能は、宣言的なquery registryとPython接続ポートで実装した。metadata/statisticsはqueryのkindで分類し、入口スキルごとの重複した取得メソッドは作らない。
- inventoryとER図の機械出力は共通レンダラー、スキルが加える考察は共通reviewテンプレートに分けた。
- CLIによる自動構造化はSQLが対象。その他のテキスト設計資料はスキルが共通契約に沿って読解・構造化・検証する。
- 実行可能なオフラインテスト、3製品のDDL fixture、実DB専用integration harnessを追加した。DDLと実DBの列・制約一致、最小権限、実際のタイムアウトを検証した。
- 新規driver/imageの版はレジストリで確認してユーザー承認を得た。既存 `work/version-decisions.json` は既存エントリーを保持して追記した。
- Claude互換frontmatterを維持した。Codex標準スキル検証器はこの追加フィールドを受理しないため、互換フィールドを別途検査したうえで、標準フィールドの一時投影に対して検証した。
