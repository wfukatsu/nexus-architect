---
name: map-domains
description: |
  ドメイン分類、境界コンテキストマッピング、ビジネス構造タイプを識別する。
  /map-domains で呼び出し。
model: opus
user_invocable: true
---

# ドメインマッピング

## 達成すべき結果

- ドメイン分類（Core/Supporting/Generic サブドメイン）
- ビジネス構造タイプ識別（Pipeline/Blackboard/Dialogue/Hybrid）
- マイクロサービス境界分類（Process/Master/Integration/Supporting）
- 境界コンテキスト間の関係マップ

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/01_analysis/ | 推奨 | /analyze-system |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/03_design/domain-analysis.md` | ドメイン分類、構造タイプ、境界マップ |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /analyze-system | 入力元 |
| /ddd-redesign | 出力先 |
