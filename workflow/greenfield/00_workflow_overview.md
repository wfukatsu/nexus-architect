# グリーンフィールド設計ワークフロー

## 概要

新規システムをゼロから設計する。要件分析からScalarDBアーキテクチャ、インフラ、デプロイまで。
coding-agent-for-scalardb の4フェーズ×13ステップをベースとする。

## フェーズ

```
Phase 1: Requirements & Judgment（要件と判断）
  Step 01: 要件分析 → ビジネス要件、NFR定義
  Step 02: ドメインモデリング → DDD戦略設計
  Step 03: ScalarDB適用判断 → 利用有無の決定

Phase 2: Design（設計）
  Step 04: データモデル設計 → ScalarDBスキーマまたは汎用DB設計
  Step 05: トランザクション設計 → Consensus Commit/2PC/Saga選択
  Step 06: API設計 → REST/gRPC/AsyncAPI仕様

Phase 3: Infrastructure（インフラ）
  Step 07: インフラ設計 → K8s構成、IaC
  Step 08: セキュリティ設計 → 認証・認可、ゼロトラスト
  Step 09: 可観測性設計 → 監視、トレーシング、アラート
  Step 10: 災害復旧設計 → RTO/RPO、バックアップ

Phase 4: Execution（実行）
  Step 11: 実装ガイド → 実装仕様、コード生成
  Step 12: テスト戦略 → BDDシナリオ、テスト仕様
  Step 13: デプロイ計画 → デプロイ戦略、ロールアウト
```

## レガシーワークフローとの共有スキル

多くのスキルは両ワークフローで共有される。
グリーンフィールドではPhase 0（Investigation）とPhase 2（Evaluation）をスキップし、
直接要件定義から設計に入る。

## 5視点レビュー

Phase 2-3完了後にレビューを実行可能。
Phase 4完了後にも最終レビューを推奨。
