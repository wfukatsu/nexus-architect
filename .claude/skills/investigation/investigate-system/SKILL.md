---
name: investigate-system
description: |
  現行システムの技術スタック、コードベース構造、技術的負債、DDD準備度を包括的に調査する。
  /investigate-system [target_path] で呼び出し。
  レガシーシステム分析の最初のステップとして使用。
model: sonnet
user_invocable: true
---

# システム調査

## 達成すべき結果

対象システムの全体像を把握し、以下の4つの調査レポートを生成する:
1. **技術スタック分析** — 使用言語、フレームワーク、ライブラリ、外部サービス
2. **コードベース構造** — ディレクトリ構成、モジュール構造、エントリポイント
3. **課題と技術的負債** — 問題点の特定と重要度分類（CRITICAL/High/Medium/Low）
4. **DDD準備度** — ドメイン駆動設計への移行準備度の評価

## 判断基準

- 技術的負債が最も集中している領域を優先的に深掘りする
- ドメイン分解を阻害する結合の問題を特にフラグする
- DDD準備度はエビデンスに基づいて評価する（推測ではなく）
- セキュリティ上の懸念があれば記録する

## 前提条件

| ファイル | 必須/推奨 | 説明 |
|---------|----------|------|
| target_path（引数） | 必須 | 調査対象のコードベースパス |

## 利用可能なリソース

- **Serena MCP** — `get_symbols_overview`, `find_symbol` でAST解析（優先）
- **Glob/Grep** — ファイルパターン検索、コード内キーワード検索
- **Read** — 設定ファイル、依存定義ファイルの読み込み
- **Task(Explore)** — 大規模コードベースの並列調査

## 出力

各セクション完了時に即座にファイル出力:

| ファイル | 内容 |
|---------|------|
| `reports/before/{project}/technology-stack.md` | 技術スタック一覧と評価 |
| `reports/before/{project}/codebase-structure.md` | ディレクトリ・モジュール構造 |
| `reports/before/{project}/issues-and-debt.md` | 技術的負債と課題一覧 |
| `reports/before/{project}/ddd-readiness.md` | DDD準備度評価 |

全出力にYAML frontmatter（title, schema_version: 1, phase, skill, generated_at）を含める。

## 完了条件

1. 4つの出力ファイルが全て書き込まれている
2. pipeline-progress.json の investigate-system を "completed" に更新
3. 発見事項のサマリーと未解決の懸念点を報告

## 関連スキル

| スキル | 関係 |
|-------|------|
| /analyze-system | 出力先（この調査結果を入力として使用） |
| /security-analysis | 関連（セキュリティ詳細調査） |
