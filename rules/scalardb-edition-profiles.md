# ScalarDB エディションプロファイル

## エディション比較

| 機能 | OSS | Enterprise Standard | Enterprise Premium |
|------|-----|--------------------|--------------------|
| Consensus Commit | Yes | Yes | Yes |
| JDBC対応DB | Yes | Yes | Yes |
| NoSQL対応 | Cassandra, DynamoDB, CosmosDB | 同左 | 同左 |
| Two-Phase Commit | Yes | Yes | Yes |
| ScalarDB Cluster | No | Yes | Yes |
| SQL Interface | No | Yes | Yes |
| GraphQL | No | Yes | Yes |
| Spring Data統合 | Basic | Full | Full |
| ScalarDB Analytics | No | No | Yes |
| マルチリージョン | No | No | Yes |
| SLA | Community | 99.9% | 99.99% |
| サポート | Community | Business Hours | 24/7 |

## デプロイモード

### Core（OSS）
- アプリケーション埋め込み型
- ライブラリとして直接利用
- gRPCサーバー不要

### Cluster（Enterprise）
- 独立したgRPCサーバークラスタ
- Kubernetes上にデプロイ
- アプリケーションはgRPCクライアントで接続
- 水平スケーリング対応

## 選定基準

| 要件 | 推奨エディション |
|------|----------------|
| 単一DBトランザクション | OSS |
| マルチDBトランザクション | OSS or Enterprise |
| SQLインターフェース必要 | Enterprise Standard+ |
| 分析クエリ必要 | Enterprise Premium |
| 99.99% SLA | Enterprise Premium |
| 5サービス以上の2PC | Enterprise Standard+（Cluster推奨） |
