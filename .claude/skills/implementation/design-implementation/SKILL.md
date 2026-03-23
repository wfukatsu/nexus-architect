---
name: design-implementation
description: |
  ドメインサービス、リポジトリインターフェース、値オブジェクト、例外マッピングの実装仕様を策定する。
  /design-implementation で呼び出し。設計フェーズ完了後に使用。
model: opus
user_invocable: true
---

# 実装設計

## 達成すべき結果

設計ドキュメントからコーディング可能な詳細実装仕様を生成する:
- ドメインサービスのメソッドシグネチャと責務定義
- リポジトリインターフェース仕様（CRUD + カスタムクエリ）
- 値オブジェクトの定義と不変条件
- 例外階層と外部例外マッピング
- サービス間通信のインターフェース契約

## 判断基準

- 設計ドキュメントの全エンティティ・集約がカバーされていること
- インターフェースは実装技術に依存しない抽象度で記述
- ScalarDB利用時は @.claude/rules/scalardb-coding-patterns.md に準拠

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/03_design/ | 必須 | design-* スキル群 |
| reports/02_evaluation/ | 推奨 | integrate-evaluations |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/06_implementation/domain-services-spec.md` | サービス仕様 |
| `reports/06_implementation/repository-interfaces-spec.md` | リポジトリ仕様 |
| `reports/06_implementation/value-objects-spec.md` | 値オブジェクト定義 |
| `reports/06_implementation/exception-mapping-spec.md` | 例外マッピング |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /design-microservices | 入力元 |
| /design-scalardb | 入力元 |
| /generate-test-specs | 出力先 |
| /generate-scalardb-code | 出力先 |
