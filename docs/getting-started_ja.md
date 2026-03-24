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

### 1. レガシーシステムの分析

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

### 2. フルパイプライン実行

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

### 3. レビューの実行

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

## 4. ScalarDBアプリケーション開発

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

## 5. ScalarDBへのデータベース移行

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
