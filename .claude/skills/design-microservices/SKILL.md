---
name: design-microservices
description: |
  ターゲットマイクロサービスアーキテクチャ、変換計画を設計する。
  /architect:design-microservices で呼び出し。ddd-redesign の出力を前提条件とする。
model: opus
user_invocable: true
---

# マイクロサービス設計

## 達成すべき結果

1. **ターゲットアーキテクチャ** — サービス一覧、分類、通信パターン、Mermaid図
2. **変換計画** — レガシーからの段階的移行ロードマップ

サービス分類:
- **Process**: ステートフル、Saga/2PC対象
- **Master**: CRUD中心、マスターデータ管理
- **Integration**: 外部システム連携アダプター
- **Supporting**: 横断的関心事（認証、通知等）

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/03_design/bounded-contexts-redesign.md | 必須 | /architect:redesign |
| reports/03_design/context-map.md | 推奨 | /architect:redesign |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/03_design/target-architecture.md` | サービス一覧、アーキテクチャ図 |
| `reports/03_design/transformation-plan.md` | 段階的移行ロードマップ |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /architect:redesign | 入力元 |
| /architect:design-scalardb | 出力先 |
| /architect:design-api | 出力先 |
