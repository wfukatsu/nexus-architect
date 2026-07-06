# はじめに

## セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/wfukatsu/nexus-architect.git
cd nexus-architect

# Python依存パッケージ（任意）
pip install -r requirements.txt

# Mermaid CLI（任意、図のレンダリング用）
npm install -g @mermaid-js/mermaid-cli
```

## 基本的な使い方

### Claude Code と Codex

Claude Code では plugin をインストールし、slash command を直接使います。

Codex ではリポジトリ root でセッションを開き、同じコマンド文字列をチャットで依頼してください。`AGENTS.md` が `/product:<name>`、`/architect:<name>`、`/scalardb:<name>` を対応する `SKILL.md` にマッピングします（`/product:<name>` は `skills/product/<name>/SKILL.md` に解決されます）。詳細は [Codex で Nexus Architect を使う](codex-usage_ja.md) を参照してください。

### 1. プロダクトの方向性を決める（グリーンフィールド）

新規プロダクトはここから始めます。ビジョンから SLA/NFR までを検証駆動で進めるパイプラインで、最終的に `/architect:define-requirements` へ引き継ぎます。

```bash
# インタラクティブなパイプライン（深い設計の前に最もリスクの高い前提を検証）
/product:start

# プロファイルでスコープを絞る
/product:start --profile=mvp

# React + Storybook のフロントエンド生成ステップを含める（--no-frontend で除外）
/product:start --frontend

# その後、システム実装設計へ引き継ぐ
/architect:define-requirements
```

UI モックの後、`/product:start` は任意で `/product:generate-frontend` を実行し、モックとアクティブなデザインシステムから実行可能な React + Storybook の scaffold を `generated/frontend/` に生成できます（Atomic Design、トークンスタイリング）。選択式で、対話的に確認するか `--frontend` / `--no-frontend` で強制できます。

プロダクトの名前が必要なときは `/product:name-product` が **アクロニム名** を作ります。各文字が英単語の頭文字になる短く発音可能なアルファベット名で、名前自体がプロダクトの価値を表すフレーズに展開されます（例: `N`ext-generation `E`xtensible e`X`change `U`nified `S`ystem）。展開に使う単語は Vision とポジショニングから取り、候補を絞り込んで 1 案を推奨します。`full` プロファイルでは Vision の後に実行され、任意のタイミングで単体実行もできます。

```bash
/product:name-product                     # 現在の Vision/ポジショニングから生成
/product:name-product --seed=SCALAR       # ベース単語の各文字に対応する英単語を探す
/product:name-product --style=initialism  # 発音可能な単語ではなく文字読み（例: SDK）
```

product スキルの全カタログは [スキルリファレンス](skill-reference_ja.md) を参照してください。

### 2. レガシーシステムの分析

```bash
# インタラクティブワークフロー（推奨）
/architect:start ./path/to/legacy-project

# または個別のスキルをステップごとに実行
/architect:investigate ./path/to/legacy-project
/architect:analyze ./path/to/legacy-project
/architect:evaluate-mmi ./path/to/legacy-project
/architect:evaluate-ddd ./path/to/legacy-project
/architect:integrate-evaluations
```

手元にレガシーシステムがない場合は、同梱のサンプルモノリス `samples/ec-monolith` を
ターゲットパスに指定すると、分析ワークフローを一通り試せます。

### 3. フルパイプライン実行

```bash
# 全フェーズを自動実行
/architect:pipeline ./path/to/project

# ScalarDBなしで実行
/architect:pipeline ./path/to/project --no-scalardb

# 分析のみ
/architect:pipeline ./path/to/project --analyze-only

# 特定のフェーズから再開
/architect:pipeline ./path/to/project --resume-from=design-microservices
```

### 4. レビューの実行

```bash
# 5視点並列レビュー（設計完了後）
# /architect:pipeline が自動的に実行しますが、個別に実行することも可能です
```

## 出力の確認

すべての出力は以下のディレクトリに生成されます：

```
reports/          # 分析・設計ドキュメント（Markdown）
generated/        # 生成コード（Java、K8sマニフェスト等）
work/             # パイプライン状態
```

統合HTMLレポート：
```bash
/architect:report
# -> reports/00_summary/full-report.html
```

## 5. ScalarDBアプリケーション開発

```bash
# スキーマをインタラクティブに設計
/scalardb:model

# 完全なスタータープロジェクトを生成
/scalardb:scaffold

# 要件からアプリケーション全体を構築
/scalardb:build-app

# ScalarDBの正確性についてコードレビュー
/scalardb:review-code
```

詳細は [ScalarDB開発ガイド](scalardb-development.md) を参照してください。

## 6. ScalarDBへのデータベース移行

```bash
# 統合エントリポイント（データベースを選択）
/architect:migrate-database

# または特定のデータベースに直接移行
/architect:migrate-oracle
/architect:migrate-mysql
/architect:migrate-postgresql
```

前提条件：Python 3.9以上、データベースクライアントツール、`pip install python-dotenv mysql-connector-python psycopg2-binary`

詳細は [データベース移行ガイド](database-migration.md) を参照してください。

## MCPサーバー（推奨）

- **Serena**：AST レベルのコード分析とシンボル検索に最適
- **Context7**：最新のScalarDBドキュメントの動的取得
