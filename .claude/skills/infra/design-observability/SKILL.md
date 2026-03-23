---
name: design-observability
description: |
  監視、分散トレーシング、ログ集約、アラート設計を行う。
  /design-observability で呼び出し。
model: sonnet
user_invocable: true
---

# 可観測性設計

## 達成すべき結果

- SLI/SLO定義（サービス別、ビジネスKPI紐づけ）
- 分散トレーシング設計（OpenTelemetry、相関ID伝搬）
- ログ集約戦略（構造化ログ、集中管理）
- メトリクス設計（RED/USE メソッド）
- アラート設計（閾値、エスカレーション、ダッシュボード）
- ScalarDB固有メトリクス（トランザクション成功率、OCC競合率）

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/08_infrastructure/observability-design.md` | 可観測性全体設計 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /design-infrastructure | 関連 |
| /review-operations | レビュー時に参照 |
