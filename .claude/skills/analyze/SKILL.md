---
name: analyze
description: |
  ユビキタス言語、アクター・ロール・権限、ドメイン-コード対応表を抽出する。
  /architect:analyze [target_path] で呼び出し。
  investigate-system の出力を前提条件とする。
model: opus
user_invocable: true
---

# システム分析

## 達成すべき結果

対象システムのドメイン知識を構造化し、以下の4つの分析ドキュメントを生成する:
1. **システム概要** — ビジネスコンテキスト、主要機能、システム境界
2. **ユビキタス言語** — ドメイン用語辞書（用語、定義、コード上の対応、使用コンテキスト）
3. **アクター・ロール・権限** — ユーザー種別、ロール定義、権限マトリクス
4. **ドメイン-コード対応表** — ドメイン概念とコード実装の対応関係

## 判断基準

- ユビキタス言語はコード内の実際の命名と照合する
- 同一概念に異なる名称が使われている場合を検出する
- ドメイン-コード対応の欠落（コードに反映されていないドメイン概念）を特定する
- ビジネスルールがコードのどこに実装されているかを追跡する

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/before/{project}/ | 必須 | /architect:investigate |

## 利用可能なリソース

- **Serena MCP** — `find_symbol`, `find_referencing_symbols` でシンボル関係分析（優先）
- **Glob/Grep** — ドメイン用語のコード内検索
- **Read** — ドキュメント、コメント、テストケースからのドメイン知識抽出
- **Task(Explore)** — 大規模コードベースの並列エンティティ抽出

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/01_analysis/system-overview.md` | ビジネスコンテキスト、機能一覧 |
| `reports/01_analysis/ubiquitous-language.md` | ドメイン用語辞書 |
| `reports/01_analysis/actors-roles-permissions.md` | アクター・ロール・権限マトリクス |
| `reports/01_analysis/domain-code-mapping.md` | ドメイン-コード対応表 |

## 完了条件

1. 4つの出力ファイルが全て書き込まれている
2. ユビキタス言語が最低20個のドメイン用語を含む
3. pipeline-progress.json を更新

## 関連スキル

| スキル | 関係 |
|-------|------|
| /architect:investigate | 入力元 |
| /architect:evaluate-mmi | 出力先 |
| /architect:evaluate-ddd | 出力先 |
| /architect:analyze-data-model | 出力先 |
