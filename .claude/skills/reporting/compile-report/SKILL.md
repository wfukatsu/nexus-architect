---
name: compile-report
description: |
  全Markdownレポートを統合HTMLレポートにコンパイルする。
  /compile-report で呼び出し。
model: haiku
user_invocable: true
---

# レポートコンパイル

## 達成すべき結果

reports/ 配下の全Markdownファイルを統合したHTMLレポートを生成する。

## 機能

- Markdown → HTML変換
- Mermaid図のインラインレンダリング
- 自動目次生成
- フェーズ別セクション構成
- ライト/ダークテーマ対応
- レスポンシブデザイン（モバイル/印刷対応）

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/00_summary/full-report.html` | 統合HTMLレポート |
