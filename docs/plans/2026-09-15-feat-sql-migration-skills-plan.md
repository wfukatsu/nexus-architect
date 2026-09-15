---
title: "SQL 移行スキル（設計・実装・検証）の実装計画"
schema_version: 1
skill: skill-creator
type: feat
status: approved
date: 2026-09-15
---

# SQL 移行スキル（設計・実装・検証）の実装計画

## Context

既存システムの SQL を ScalarDB に移す作業は、今の nexus-architect では分析止まりである。

- `migrate-{oracle,mysql,postgresql}` は、スキーマ抽出と移行手順の Markdown を作る。アプリケーションの SQL は「Application Impact」という散文の評価に留まる。
- `investigate-db-design` / `investigate-db-live`（v0.40.0）は、DDL・カタログ・統計を根拠付きで棚卸しする。ただし、その結果を移行に使う経路がない。
- アプリ内の SQL（JDBC 文字列、MyBatis、JPA ネイティブクエリ）を棚卸しする仕組みはない。Schema Loader JSON を出すスキルも、Core API と ScalarDB SQL のどちらを使うかを記録するスキルもない。

`github.com/wfukatsu/sql-migration`（MIT、commit `1d2e4db`）は、SQLGlot で SQL を 1 文ずつ ScalarDB SQL に変換し、次の 4 つに判定する PoC である。

- **OK / WARN**: ScalarDB SQL に変換できた。
- **PLANNED**: ScalarDB から行を取得し、H2 で元の SQL を実行する実行計画に分解した。
- **ERROR**: 自動では移せない。理由と対応案を付ける。

あわせて、Schema Loader JSON、Java のランタイムとアプリ側の補助クラス、正解データとの突き合わせ（golden）、差分テストを持つ。

これを nexus に取り込み、**分析結果を入力にして 1 文ずつ移行経路を決め、コードを生成し、実データで確かめる**仕組みにする。

利用者の決定（2026-09-15）:

- **取り込み**: sql-migration を nexus に複製し、その際に英語へ書き直す。
- **スキル構成**: 設計・実装・検証の 3 スキルに分ける。
- **対象 SQL**: DDL（調査結果から）、アプリ内の SQL、ビュー・ルーチンの本体、利用者が渡す SQL ファイルのすべて。
- **実装の出力先**: `generated/`。

## 全体像

```
investigate-db-design / investigate-db-live   (table and key facts, row estimates)
design-scalardb / select-scalardb-edition     (keys, backend, edition = whether ScalarDB SQL is available)
application code / DB objects / SQL files     (statement sources)
        │
        ▼
/architect:design-sql-migration   (opus)  → reports/03_design/sql-migration/
        SQL inventory → converter run → one route per statement → migration manifest (SQM-)
        ▼
/architect:implement-sql-migration (sonnet) → generated/sql-migration/<target>/
        ScalarDB SQL, schema.json, plan JSON, Java module (runtime + app-side code), offline gate
        ▼
/architect:verify-sql-migration   (sonnet) → reports/09_verification/sql-migration/
        golden check (no DB) → optional differential test (source DB vs ScalarDB) → verified status written back
```

## 1. sql-migration の複製（英語化）

置き場所は `skills/common/sql-migration/`（`database-investigation` と同じ流儀）とする。

| 複製するもの | 元 | 扱い |
|---|---|---|
| 変換器 `scalardb_migrate/` 7 モジュール（`converter`、`decomposer`、`appside`、`dialect`、`schema`、`types`、`__init__`） | 同名 | コードは既に英語。挙動は変えない。import パスだけ調整する |
| CLI | `scalardb_migrate/cli.py` | 英語のまま移し、nexus の出力規約（frontmatter）に合わせたレポート出力を追加する |
| Java ランタイム | `runtime-java/`（`Runner`、`Fetcher`/`CoreFetcher`/`JdbcFetcher`、`Residual`、`OracleFunctions`、`appside/*`、`golden/GoldenCheck`） | 移す。`Bench` と例の `AreaSalesReport` は外す。依存バージョンは実装時に dependency-versions ルールで調べ直す |
| 検証 | `difftest/golden.py`、`difftest/run.py`、`backends.py` | 移す。固定の接続情報（`postgres:postgres` など）は、investigate-db-live と同じ環境変数参照の profile に置き換える |
| 参照資料 | `skills/sql-transpile/references/{scalardb-grammar,app-side-notes,operations}.md`、`docs/architecture.md` の要点 | **英語に書き直す**（日本語は計 400 行ほど） |
| テスト | `tests/test_{converter,decomposer,appside,dml_examples}.py`（77 件）、Java テスト（`AreaSalesReport` 以外） | 移す。Python は nexus のランナーが見つける `*.test.py` にし、日本語の期待値文字列を英語化する |

**移さないもの**: 汎用方言変換（`generic.py`、関数カタログ）、`sql-transpile` スキル本体、ベンチマーク、spikes、スライドの生成元。いずれも ScalarDB 移行の対象外である。

**出所の記録**: `PROVENANCE.md` に次を書く。

- 元リポジトリの URL、commit、MIT の著作権表示
- 翻訳したこと、外した部分、変更点の一覧
- 取り込み直す手順

**同等性の確認**: 複製後に元のテスト 77 件と Java テストがすべて通ることを確認する。

**CI**: ルートの `requirements.txt` に `sqlglot` を追加する（バージョンは調べて固定）。`duckdb` と `pytest` は、テストを unittest に移せば不要なので加えない。

## 2. スキル

### 2.1 `/architect:design-sql-migration`（opus、拡張ティア）

1. **入力の確定**
   - 移行元の製品と版
   - 対象の範囲
   - 使う調査結果の run（明示して選ばせる。最新を黙って選ばない）
   - ScalarDB のエディション（`select-scalardb-edition`。ScalarDB SQL は Enterprise Premium）
   - バックエンド（`design-scalardb` の ADR）
   - 不明な点は open-questions ルールで尋ねる
2. **SQL インベントリ**（新規 `scripts/inventory.py`、決定的に動かす）

   | 出どころ | 取り出し方 | 根拠 |
   |---|---|---|
   | DDL | investigate-db-design の inventory の証拠行から、元の DDL を読み直す | ファイル・ハッシュ・行 |
   | ビュー・ルーチン本体 | 調査スキルは本体を保存しないので、同じ証拠行から元ソースを読む。live しかない場合は、利用者が出したソースを要求する | 同上 |
   | アプリ内 | MyBatis XML の `<select|insert|update|delete>`、JPA `@Query(nativeQuery = true)`、JDBC の `prepareStatement` / `executeQuery` などに渡す文字列リテラル、`.sql` リソース | 同上 |
   | 利用者のファイル | そのまま | 同上 |

   - 動的 SQL（文字列連結、MyBatis の `<if>` / `<foreach>`、`${}`）は `dynamic` とし、自動変換には回さない。展開例を利用者に確認する。
   - リテラルは保存しない方針を DB 調査スキルから引き継ぐ。
3. **変換器の実行**。分析結果を変換器の引数に写す。

   | 分析結果 | 変換器への入力 |
   |---|---|
   | 調査 inventory の PK / 索引、`design-scalardb` のキー設計 | `--schema`（Schema Loader JSON を組み立てる）、`--keys` |
   | ADR のバックエンド | `--storage jdbc\|cassandra` |
   | live の行数推定（`semantics: estimate` と明記） | `--expected-rows` |
   | 分離レベルの設計 | `--isolation` |

4. **経路の決定**。1 文に 1 経路を割り当て、根拠と代替案を残す。

   | 経路 | いつ |
   |---|---|
   | `scalardb_sql` | 変換器が OK / WARN、かつエディションが ScalarDB SQL を持つ |
   | `core_api` | 変換器が OK / WARN、かつ ScalarDB SQL を使えない。Core API のコードに落とす |
   | `plan` | PLANNED。行数とガードレールを確認する |
   | `app_side` | ERROR の読み取りと書き込み。アプリ側処理の方式（P9〜P12 など）と、結果を変えないための注意（APP_SEMANTICS）を必ず付ける |
   | `redesign` | FULL_SCAN、複合列インデックス、トリガーなど。キーの追加、集計表、ScalarDB Analytics を提案する |
   | `retire` | 使われていない文。根拠を付ける |

   - キー設計やバックエンドを変える判断は ADR にする。
5. **出力**（`reports/03_design/sql-migration/`）
   - `sql-inventory.json`
   - `sql-migration-manifest.json`（`SQM-###`、正本）
   - `schema.json`（Schema Loader）
   - Markdown の閲覧用ビュー: 移行経路の一覧、手作業の見積もり、未解決事項
   - `work/traceability.json` への `SQM-` ノードの追記（上流は `FR-` / `AGG-` / 調査 run の証拠）

### 2.2 `/architect:implement-sql-migration`（sonnet、拡張ティア・codegen）

manifest だけを入力にして `generated/sql-migration/<target>/` に次を出力する。

- `migration/*.scalardb.sql`、`schema.json`、`plans/SQM-###.plan.json`
- Java モジュール
  - 複製したランタイムと補助クラス
  - `plan` 経路の呼び出しコード
  - `app_side` 経路の実装。`AppSideQuery` と書き込みテンプレート（読む → 計算 → キーで書く）を 1 トランザクションで行う
  - `core_api` 経路の Get/Put/Scan
  - 採番とアプリ時計の差し替え点
- `build.gradle`。バージョンは調べて決め、確認は `--confirm-versions` の方針に従う。
- TDD ルールに沿ったテスト

**オフラインゲート**（DB 不要）:

- 変換器を再実行し、manifest の判定と一致する。
- すべての計画が `residual-runner validate` を通る。
- `gradle test` が通る。
- `app_side` の各文に golden テストの枠がある。

### 2.3 `/architect:verify-sql-migration`（sonnet、拡張ティア）

1. **golden 検証**（DB 不要）: 利用者が一度だけ取得した正解データ（`golden.json`）と、`app_side` の実装を突き合わせる。正解データの取得には移行元 DB が必要で、利用者の許可と環境変数参照の profile を使う。
2. **差分テスト**（任意、明示して呼ぶ）: 使い捨てコンテナの移行元 DB と ScalarDB で、同じデータに対する結果集合を比べる。
   - Core API 経路はライセンス不要。
   - ScalarDB SQL 経路は Cluster とライセンスが必要で、無い場合はスキップと明記する。
   - 本番 DB には接続しない。
3. 結果を manifest の `verification` 欄に書き戻す（`verified` / `failed` / `skipped` + 理由）。レポートは `reports/09_verification/sql-migration/`。

## 3. 契約とバリデータ（テストで守る）

- `rules/sql-migration.md`: 経路の定義、判定と経路の対応、動的 SQL の扱い、ライセンスとエディションの制約、「バックエンドに直接接続しない」。
- `tools/lib/sql_migration_manifest.py` と `*.test.py`。検証する規則:
  - インベントリの全文に、ちょうど 1 つの経路がある。
  - 経路が変換器の判定と矛盾しない（ERROR を `scalardb_sql` にしない）。
  - 経路が manifest に記録したエディションと矛盾しない（ScalarDB SQL の無いエディションで `scalardb_sql` を選ばない）。
  - `dynamic` の文は、利用者の確認なしに自動経路へ回さない。
  - `app_side` の文に APP_SEMANTICS への対応がある。
  - キーが宣言済みの表と列を指す。
  - 根拠の行が実在する。
  - `verification` の値が正しい。
- `skills/common/sql-migration/tests/`: 複製した変換器のテスト、インベントリ抽出（MyBatis の動的 SQL、Java の連結、JPA）、CLI の終了コードとレポートの frontmatter。
- Java テスト: `samples/scalardb-transaction-tests` と同じく、ネットワークが必要な明示実行とする（CI のランナー外）。

## 4. 登録とドキュメント

- **登録と一覧**:
  - `marketplace.json` に 3 スキルを登録する。
  - `tools/lib/pipeline_status_data.py` の `EXTENSION_PHASES`、`CODEGEN_PHASES`（implement のみ）と、`pipeline_status_data.test.py` の `DOC_EXTENSION_TIER` を更新する。
  - `CLAUDE.md`（112 → 115 コマンド、拡張ティア 21 → 24、テスト表）、`README`、`AGENTS.md`、`OMNIGENT.md`、`docs/skill-reference(_ja).md` を更新する。
- **既存スキルからの参照**:
  - `migrate-database` から、アプリ SQL の移行経路として 3 スキルを案内する。既存の DB 別ワークフローは変えない。
  - `analyze-data-model` と `investigate-db-*` の Related Skills に追記する。
- **検証の確認**: `bash tools/run-tests.sh`（docs_consistency を含む）で漏れを確認する。

## 5. 進め方（Red → Green のコミット単位）

1. 複製と英語化。元のテストが通ることを Green とする。
2. SQL インベントリの抽出器（テスト先行）。
3. manifest の schema とバリデータ（テスト先行）。
4. `design-sql-migration` の SKILL.md、ルール、テンプレート。
5. `implement-sql-migration` の生成器とオフラインゲート（テスト先行）。
6. `verify-sql-migration` の golden 検証と差分テスト（profile は環境変数参照）。
7. 登録、ドキュメント、サンプルでのスモークテスト。

## 6. 検証

- `bash tools/run-tests.sh` が全スイート成功する。
- 複製した変換器テスト 77 件と Java テストが成功する。
- **スモーク**: 小さなサンプル（Oracle 方言の DDL + MyBatis/JDBC の SQL を含む `samples/sql-migration-shop/` を新設）で、3 スキルを通しで実行する。
  - 使い捨ての移行元 PostgreSQL/Oracle コンテナと、ScalarDB（Core API 経路）で差分テストを成功させる。
  - 前回と同様、実行を固定した worktree に向け、opus サブエージェントに SKILL.md の曖昧な点を引用付きで報告させ、修正に反映する。
- ScalarDB SQL（JDBC）経路は、ライセンスがある場合だけ検証する。無い場合は「未検証」と記録する。

## 7. リスクと前提

- ScalarDB SQL は Enterprise Premium の機能で、ライセンスが必要である。変換、`validate`、Core API 経路はライセンス無しで動く。
- 変換器は PoC である。OK は「文法として生成できた」という意味にとどまるので、重要な SQL は差分テストか golden で確かめる前提にする。
- アプリ内 SQL の抽出は、静的に読める範囲に限る。動的 SQL と ORM が生成する SQL は対象外とし、未抽出の件数を報告する。
- 規模が大きいため、段階 1〜3 の完了時点で途中経過を報告する。
