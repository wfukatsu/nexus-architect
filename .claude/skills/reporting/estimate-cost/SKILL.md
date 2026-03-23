---
name: estimate-cost
description: |
  クラウドインフラ、ScalarDBライセンス、運用コストの見積もりを作成する。
  /estimate-cost で呼び出し。サイジング見積もりも統合。
model: sonnet
user_invocable: true
---

# コスト見積もり

## 達成すべき結果

プロジェクトの総コストを多角的に見積もる:
- クラウドインフラコスト（AWS/Azure/GCP、コンピュート/ストレージ/ネットワーク）
- ScalarDBライセンスコスト（エディション別、直接契約 vs AWS Marketplace）
- 運用コスト（監視ツール、サポート、人件費）
- ScalarDBサイジング（Pod数、クラスタ構成、DB容量）

## 判断基準

AskUserQuestion で以下を確認:
- 環境タイプ（dev/staging/prod）
- 想定TPS、データ量、可用性目標
- 通貨（USD/JPY）

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/05_estimate/cost-summary.md` | コスト概要 |
| `reports/05_estimate/infrastructure-detail.md` | インフラ詳細見積もり |
| `reports/05_estimate/scalardb-sizing.md` | ScalarDBサイジング |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /design-infrastructure | 入力元 |
| /design-scalardb | 入力元（サイジング情報） |
