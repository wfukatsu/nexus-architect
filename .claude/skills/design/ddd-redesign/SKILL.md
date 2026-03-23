---
name: ddd-redesign
description: |
  境界コンテキストの再設計、集約定義、コンテキストマップを生成する。
  /ddd-redesign で呼び出し。integrate-evaluations の出力を前提条件とする。
model: opus
user_invocable: true
---

# DDD再設計

## 達成すべき結果

評価結果に基づき、新しい境界コンテキスト設計を策定する:
1. **境界コンテキスト再設計** — 各BCの責務、含まれる集約、公開インターフェース
2. **コンテキストマップ** — BC間の関係パターン（ACL, OHS, Conformist等）をMermaid図で

## 判断基準

- 各BCが単一の明確な責務を持つこと
- BC間の依存は最小限に保つ
- コアドメインに最も投資するサブドメイン分類を反映する
- 既存システムからの段階的移行パスを考慮する

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/02_evaluation/unified-improvement-plan.md | 必須 | /integrate-evaluations |
| reports/01_analysis/ubiquitous-language.md | 推奨 | /analyze-system |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/03_design/bounded-contexts-redesign.md` | BC定義、集約一覧、責務 |
| `reports/03_design/context-map.md` | コンテキストマップ（Mermaid図） |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /integrate-evaluations | 入力元 |
| /design-microservices | 出力先 |
| /map-domains | 関連 |
