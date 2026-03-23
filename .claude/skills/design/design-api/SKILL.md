---
name: design-api
description: |
  REST/GraphQL/gRPC/AsyncAPI仕様を生成する。
  /design-api で呼び出し。design-microservices の出力を前提条件とする。
model: opus
user_invocable: true
---

# API設計

## 達成すべき結果

マイクロサービス間およびクライアント向けのAPI仕様を設計する:
- REST API (OpenAPI 3.0仕様)
- GraphQL スキーマ（必要に応じて）
- gRPC protobuf定義（サービス間通信）
- AsyncAPI（イベント駆動通信）
- API Gateway設計（ルーティング、認証、レート制限）

## 判断基準

- サービス分類に応じたプロトコル選択（Process→gRPC, Master→REST, Integration→AsyncAPI）
- 認証・認可パターン（OAuth2/OIDC + RBAC/ABAC）
- APIバージョニング戦略
- エラーレスポンス標準化

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/03_design/target-architecture.md | 必須 | /design-microservices |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/03_design/api-specifications/openapi/` | REST API仕様 |
| `reports/03_design/api-specifications/graphql/` | GraphQLスキーマ |
| `reports/03_design/api-specifications/grpc/` | protobuf定義 |
| `reports/03_design/api-specifications/asyncapi/` | イベント仕様 |
| `reports/03_design/api-gateway-design.md` | Gateway設計 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /design-microservices | 入力元 |
| /review-consistency | レビュー対象 |
