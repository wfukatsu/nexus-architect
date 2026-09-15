---
title: "既存DB調査スキルの実装・検証記録"
schema_version: 1
skill: skill-creator
date: 2026-09-15
status: completed
---

# 既存DB調査スキルの実装・検証記録

`investigate-db-design` と `investigate-db-live` を architect に登録した。既存の移行器と自動pipelineの依存関係は変更していない。共通契約、製品別query registry、接続ポート、DDL処理、レポート出力、日英カタログ、任意入力の受け渡しを追加した。

## 実DB検証

ユーザーがDocker Desktopでの検証と版の組み合わせを承認。今回専用のloopback公開コンテナにfixtureを作成し、調査はSELECT権限を持つ読み取り用ユーザーで実行した。fixture作成のDDL/DMLは `tests/integration.py` のみで、調査CLIには含まれない。

| 製品 | 実際に確認した版 | ドライバ | 結果 |
|---|---|---|---|
| PostgreSQL | 18.6 (Debian 18.6-1.pgdg13+2) | psycopg 3.3.5 | PASS |
| MySQL | 8.4.11 | PyMySQL 1.2.0 | PASS |
| Oracle Free | 23.26.3.0.0 | python-oracledb 26.0.0 thin | PASS |

3製品とも以下を確認した。

- テーブル2件、列4件、ビュー1件を正しく分類。複合PK/FKの列順と参照先を保持。
- 同じ設計のDDL fixtureと、実DBから取得した列・NULL許容・宣言制約の一致。
- 件数・容量等の既存統計、0/null、取得時刻と利用可能な更新時刻の保存。
- 取得上限1件時の打ち切り検出、SQL injectionの形をしたスキーマ値が範囲を広げないこと。
- 1秒の問い合わせ制限による停止と `timeout` への分類。3製品とも実測約1.0秒。
- 認証情報を含まないCLI出力、共通JSON Schema検証、レポートのfrontmatter/Mermaid構造検証。

MySQLの読み取り用ユーザーでは追加監視統計が `permission_denied` となり、適切な権限を持つ接続では `ok` となることも確認した。Oracleでは別所有者の `USER_SEGMENTS` を取得したと誤認せず、`not_collected` と理由を残した。これらは期待した部分取得であり、テスト失敗を許容したものではない。

実行コマンド（各製品終了コード0）：

```text
/tmp/nexus-db-investigation-venv/bin/python skills/common/database-investigation/tests/integration.py postgresql --runtime /tmp/nexus-db-investigation-runtime
/tmp/nexus-db-investigation-venv/bin/python skills/common/database-investigation/tests/integration.py mysql --runtime /tmp/nexus-db-investigation-runtime
/tmp/nexus-db-investigation-venv/bin/python skills/common/database-investigation/tests/integration.py oracle --runtime /tmp/nexus-db-investigation-runtime
```

初期化時だけ `--initialize-disposable-fixtures` を付けた。再実行時には付けない。検証用コンテナ名は `nexus-inv-pg`、`nexus-inv-mysql`、`nexus-inv-oracle`。終了後は停止し、既存コンテナを操作しない。

## 8段階の品質確認

| 段階 | 実行・証跡 | 結果 |
|---|---|---|
| Build | `python3 -m compileall -q skills/common/database-investigation/scripts`、終了0 | PASS |
| Unit | `design.test.py` 7件、`live.test.py` 6件、終了0。CLI 3件も終了0 | PASS |
| Contract | `contract.test.py` 8件、終了0。第4アダプタ追加、SQL束縛、秘密情報、証拠参照を検査。実DB成果物はJSON Schemaでも検証 | PASS |
| Integration | 上記の3製品テスト。fixture一致、読み取りユーザー、実際の上限・停止、CLI、終了0 | PASS |
| SAST | `bandit -r skills/common/database-investigation/scripts -f json`、終了0、未抑制の指摘0 | PASS |
| Dependency scan | 隔離venvの `pip-audit --format json`、終了0、既知の脆弱性0 | PASS |
| API security | HTTP APIを追加しないため対象外。SQL束縛・scope・秘密情報は契約/実DB/SASTで確認 | N/A（理由を記録） |
| Design↔code | 承認計画と下記対応表、DDL↔実DB一致、登録・日英カタログ整合性35チェック、終了0 | PASS（範囲は下記） |

全体の回帰確認は `bash tools/run-tests.sh`、26/26スイート成功。新規の4スイートは合計24テスト。既存の22スイートも成功した。`git diff --check` は終了0。

SASTの限定的な抑制：OracleのROWNUM wrapperで、SQL文字列はリポジトリの固定registryからのみ読み、スキーマと上限はbindする。Bandit B608の誤検知をその1行だけ根拠付きで抑制した。入力SQLやprofileを文字列連結していない。DDL lexerの変数名も、認証tokenとの誤検知を避けるためlexemeへ整理した。

Codex標準 `quick_validate.py` はClaude互換の `model` / `user_invocable` を未知フィールドとして拒否する。この既存互換性を壊さず、両フィールドを別途検査し、標準フィールドだけの一時コピーに対して両スキルの検証を実行して終了0を確認した。実ファイルから互換フィールドは削除していない。

一時的な詳細ログ・生成レポートは `/tmp/nexus-db-investigation-runtime/`、検証Python環境は `/tmp/nexus-db-investigation-venv/`。この記録には認証情報を含めない。

## 計画との対応・実装範囲

| 要件 | 実装・検証 |
|---|---|
| 2つの入口 | `skills/investigate-db-design/`、`skills/investigate-db-live/`、marketplace登録 |
| 共通契約 | `skills/common/database-investigation/inventory.schema.json`、意味上の証拠/範囲検証 |
| アダプタ拡張 | 宣言registry＋製品モジュール。第4アダプタを一時配置してcore変更なしでロード/解析するテスト |
| DDLの製品差 | 引用識別子、複合キー、複数ファイルALTER、Oracleブロック、PostgreSQL dollar quote、MySQL DELIMITER |
| 未取得・不明の保持 | 状態の列挙、未対応文の出典、重複/未解決参照、部分取得終了コード2 |
| 既存連携 | analyze-data-modelの任意入力、元のpipeline依存グラフと移行器は維持 |
| 機密性・負荷 | 環境参照、固定SELECT、bind、上限、deadline、値/定義本文の非収集、TLS既定 |

汎用SQLパーサーではない。対応外の列修飾や式索引、任意のマイグレーション履歴、ルーチン本体、パーティション構造などは自動解析の対象外または部分取得として保持し、スキルが出典を読んで補足する。Markdown/CSV等はスキルが契約に沿って読解する。全DB版対応、全メタデータ取得、業務的な正規化判定の自動完了は主張しない。

TLS/Walletの設定経路は実装したが、今回のloopbackコンテナ検証は明示的な平文接続であり、実証明書/Walletを使った接続は未検証。予算はquery/driver単位の制限で、ネットワーク切断やcleanupを含む厳密なwall-clock SLAではない。

## テスト先行の履歴

主な単位でRed→Green→Refactorを記録した。

| 単位 | Red | Green | Refactor |
|---|---|---|---|
| DDL解析 | `390a1e8` | `9727fb2` | `a1759bf` |
| Live収集 | `41c2d88` | `e133f25` | `a1759bf` |
| CLI・成果物 | `ca560d6` | `af000fc` | `50e2067` |

後続の不具合も、式索引/証拠参照 `cfb5ec9`、版表記 `04371a8`、取得上限/統計無効 `8a16965`、Oracle timeout `72f7fd1` の失敗テストを修正前に記録した。接続実装・固定SQLは実インフラアダプタとして実DB検証を実施。文書・登録・表示のみの変更は独立のTDD単位にしていない。
