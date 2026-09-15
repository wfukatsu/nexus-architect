---
title: "SQL 移行スキルの実装・検証記録"
schema_version: 1
skill: skill-creator
date: 2026-09-15
status: in_progress
---

# SQL 移行スキルの実装・検証記録

[実装計画](2026-09-15-feat-sql-migration-skills-plan.md)（2026-09-15 承認）に沿って、`design-sql-migration`・
`implement-sql-migration`・`verify-sql-migration` の 3 スキルを architect の拡張ティアに追加した。
`github.com/wfukatsu/sql-migration`（commit `1d2e4db`、MIT）を英語化して `skills/common/sql-migration/` に複製し、
出所と変更点は同ディレクトリの `PROVENANCE.md` に記録した。

## テスト先行の履歴

| 単位 | Red | Green |
|---|---|---|
| 変換器とランタイムの複製（元のテストを移植して同等性を示す。複製のため test-first の対象外） | — | `ec94c95` |
| SQL インベントリ | `4b5dd0c` | `43ee1cf` |
| 抽出できなかった呼び出しの計数 | `822acba` | `b7f6006` |
| マニフェストの契約とバリデータ（`rules/sql-migration.md`） | `8821aab` | `d4469c6`（CLAUDE.md への索引漏れを `cea29fb` で修正） |
| インベントリの変換と経路の案 | `21a9a6e` | `38eef5d` |
| 移行モジュールの生成とオフラインゲート | `cb0185c` | `5d194cf` |
| 検証（比較・差分テスト・golden・記録） | `84ccd7e` | `3424c45`（テストの期待値 2 件の誤りを同時に修正） |
| 差分テストでバインド変数付きの文をスキップ | `0bb2567` | `ec16343` |
| 生成した実行計画の namespace と、ID・時刻を使う書き込みの雛形 | `db5ea72` | `f01842d` |
| 指摘メッセージのマスク範囲とキーの出どころ | `e57c5c5` | `384bfcc` |
| Java のバインド変数とランタイムのビルド場所 | `713ce12` | `f12faf8` |

SKILL.md、登録、カタログ、サンプル、文書は `c273f6a`、`797fc0a`、`9dfb0bc`、`e16c2ee`、`f8d040b`、`0ba9d0c`、`287fcf7`。

## 同等性と依存バージョン

- 移植した変換器のテスト（関数 77 件、元の pytest 257 ケース相当）は sqlglot 30.18.0 で全件成功。
- 複製した Java ランタイムのテスト 37 件（例の `AreaSalesReportTest` 2 件を除く）は、元の固定版と最新安定版の
  どちらでも成功した。利用者の承認により最新安定版（ScalarDB 3.19.1、H2 2.5.250、Gson 2.14.0、JUnit 5.14.4）を採用。
- `requirements.txt` に `sqlglot==30.18.0` を追加。CI は変換器のスイートを実行し、sqlglot の無い手元では SKIP と表示する。
- `bash tools/run-tests.sh` は 35/35 スイート成功。

## サンプルとスモーク

`samples/sql-migration-shop/`（PostgreSQL の DDL、MyBatis、JDBC、JPA、バッチ SQL の 16 文と答え表）で次を確認した。

1. **opus サブエージェントによる実行**: コミットを固定した worktree の SKILL.md だけを読み、`design-sql-migration --auto`
   と `implement-sql-migration --auto` を最後まで実行。バリデータ、`gradle build`、全実行計画の `residual-runner validate`、
   レポートのフックがすべて成功し、全経路が答え表と一致した。
2. **報告された 12 件の指摘への対応**

   | 指摘 | 対応 |
   |---|---|
   | 生成した実行計画の namespace が null（ゲートの再変換が schema.json の表定義を上書き） | 修正。namespace の無い計画をゲートで拒否 |
   | 採番と日付を使う INSERT に書き込みの雛形が出ない／ID 生成器が重複 | 修正。`LongSupplier` と `Clock` を受ける書き込みの雛形 |
   | Auto Mode で namespace の出どころが無い | `--namespace` を追加。無ければ停止 |
   | Auto Mode が Stage 5 の確定作業を省く | Auto Mode の確定手順と Open Question 化を明記 |
   | マスクが指摘メッセージの識別子まで潰す | 修正。文に実在するリテラルだけをマスク |
   | 変換器の文言の誤り（SUM の矛盾、`--expected-rows` の案内） | **未対応**。複製した変換器の挙動を変えるため、元リポジトリの課題とする |
   | JPA の名前付きパラメータが `binds` に入らない | 修正 |
   | SQL ファイル由来のキーが `investigation` と表示される | 修正。`source_ddl` を追加 |
   | `target.scalardb_version` を設定する手順が無い | 変換時に版を渡す手順を追記 |
   | 動的 SQL の説明が実態（`ERROR PARSE`）と合わない | 説明を修正 |
   | ルール §6 の ID 採番の文言、`work/context.md` の作り方 | 修正 |
   | ランタイムのビルドがプラグインのディレクトリに書かれる | プロジェクトの `work/sql-migration/runtime-java` に変更し、検証ツールもそちらを優先 |

3. **修正後の再実行**: 現在のスクリプトでサンプルを最後まで通し、実行計画の namespace が `shop` になること、
   書き込みの雛形がコンパイルできること（`gradle build` 成功）を確認した。

## 差分テスト（実 DB）

2026-09-15、使い捨ての PostgreSQL 18.6 コンテナで `verify-sql-migration` の差分テストを Core API 経路で実行した。

- 移行元 DB `shop_source` にサンプルの DDL と seed を投入。ScalarDB 側のバックエンドは同じコンテナの別 DB `scalardb`
  とし、Schema Loader 3.19.1（`--coordinator`）で `schema.json` を適用して、`residual-runner load` で同じ行
  （customers 4、orders 8、order_items 10、stock 5）を入れた。
- 接続情報はその場で生成し、権限 600 のファイルと環境変数の参照（`environment: local`）だけで渡した。
- `difftest.py --fetcher core --record` の結果は **pass 1、skipped 10**、終了コード 0。記録後もバリデータは成功した
  （16 文）。

| 文 | 経路 | 結果 |
|---|---|---|
| SQM-001 | plan | **verified**（元 DB と ScalarDB + H2 の結果集合が一致） |
| SQM-011 | plan | skipped（バインド変数付き。golden か単体テストで確かめる） |
| SQM-009、013、014 | scalardb_sql | skipped（ScalarDB Cluster とライセンスが必要） |
| SQM-002、008、010、012、015、016 | app_side | skipped（golden で確かめる） |
| SQM-003〜007 | schema | pending（差分テストの対象外。Schema Loader の適用は成功） |

スキップの理由はすべて manifest の `verification` にそのまま書き戻され、`verified` は実際に一致した 1 文だけだった。

## 未検証

- **golden 検証の実 DB での取得**: `golden.py capture` を移行元 DB に対して実行していない。app_side の 6 文は
  `skipped` のまま。
- **ScalarDB SQL（JDBC）経路**: ScalarDB Cluster とライセンスが無いため未検証。
- **変換器自体の文言の誤り**（上表）は元リポジトリで扱う。
