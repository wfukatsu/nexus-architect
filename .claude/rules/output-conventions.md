# 出力規約

## YAML Frontmatter（必須）

全出力ファイルは以下のfrontmatterを含むこと:

```yaml
---
title: "ドキュメントタイトル"
schema_version: 1
phase: "Phase N: カテゴリ名"
skill: skill-name
generated_at: "ISO8601"
input_files:
  - reports/XX/input-file.md
---
```

## ファイル命名規約

- **kebab-case限定**: `ubiquitous-language.md`（NOT `ubiquitous_language.md`）
- ディレクトリがフェーズを示すため、ファイル名にフェーズプレフィックス不要
- サフィックス例: `-analysis.md`, `-evaluation.md`, `-design.md`, `-specs.md`

## 即時出力ルール

**重要**: 各ステップ完了時に即座にファイル出力すること。最後にまとめて出力しない。

理由:
- パイプラインを中断・再開可能にするため
- 中間成果を可視化するため
- スキル並列化を可能にするため

## 言語

- 全出力ドキュメント: 日本語
- YAML frontmatter: 英語キー、日本語値
- Mermaidノード: 日本語テキストはクォートで囲む

## ドキュメント構造

- 見出しレベルは `##` から開始（`#` はタイトル用）
- Mermaid図は適切な箇所に配置
- テーブルは Markdown 標準形式
- コードブロックには言語指定を含める
