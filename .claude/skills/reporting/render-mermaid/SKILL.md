---
name: render-mermaid
description: |
  Mermaid図をPNG/SVG/PDFに変換し、構文エラーも修正する。
  /render-mermaid [target_path] で呼び出し。
model: haiku
user_invocable: true
---

# Mermaidレンダリング・修正

## 達成すべき結果

指定されたMarkdownファイルまたはディレクトリ内のMermaid図を画像に変換する。
構文エラーがある場合は自動修正する。

## 機能

- Mermaid → PNG/SVG/PDF変換（mmdcコマンド使用）
- 構文エラーの自動検出・修正
- 日本語テキストのクォート修正
- 括弧の不一致修正

## ツール

- `mmdc` (mermaid-cli) がインストールされている場合は利用
- 未インストールの場合は構文検証のみ実行

## 出力

レンダリング結果は元ファイルと同じディレクトリに配置。
