---
name: design-disaster-recovery
description: |
  RTO/RPO定義、バックアップ戦略、フェイルオーバー設計、復旧手順を策定する。
  /design-disaster-recovery で呼び出し。
model: sonnet
user_invocable: true
---

# 災害復旧設計

## 達成すべき結果

- サービスティア別RTO/RPO定義
- バックアップ戦略（頻度、保持期間、テスト計画）
- フェイルオーバー設計（リージョン間、AZ間）
- データリカバリ手順（ScalarDB Coordinatorテーブル含む）
- ランブック（障害シナリオ別の復旧手順）
- 復旧テスト計画（カオスエンジニアリング含む）

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/08_infrastructure/disaster-recovery-design.md` | DR全体設計 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /architect:design-infrastructure | 関連 |
| /architect:review-operations | レビュー時に参照 |
