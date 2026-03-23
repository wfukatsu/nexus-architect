# Getting Started

## セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/wfukatsu/nexus-architect.git
cd nexus-architect

# Python依存関係（オプション）
pip install -r requirements.txt

# Mermaid CLI（オプション、図のレンダリング用）
npm install -g @mermaid-js/mermaid-cli
```

## 基本的な使い方

### 1. レガシーシステムの分析

```bash
# 対話的ワークフロー（推奨）
/workflow ./path/to/legacy-project

# または個別スキルで段階的に実行
/investigate-system ./path/to/legacy-project
/analyze-system ./path/to/legacy-project
/evaluate-mmi ./path/to/legacy-project
/evaluate-ddd ./path/to/legacy-project
/integrate-evaluations
```

### 2. フルパイプライン実行

```bash
# 全フェーズ自動実行
/full-pipeline ./path/to/project

# ScalarDB無しで実行
/full-pipeline ./path/to/project --no-scalardb

# 分析のみ
/full-pipeline ./path/to/project --analyze-only

# 特定フェーズから再開
/full-pipeline ./path/to/project --resume-from=design-microservices
```

### 3. レビュー実行

```bash
# 5視点並列レビュー（設計完了後）
# workflow/full-pipeline が自動的に実行するが、個別実行も可能
```

## 出力の確認

全出力は以下のディレクトリに生成:

```
reports/          # 分析・設計ドキュメント（Markdown）
generated/        # 生成コード（Java, K8s manifests等）
work/             # パイプライン状態
```

統合HTMLレポート:
```bash
/compile-report
# → reports/00_summary/full-report.html
```

## MCP サーバー（推奨）

- **Serena**: コードのAST解析、シンボル検索に最適
- **Context7**: ScalarDB最新ドキュメントの動的取得
