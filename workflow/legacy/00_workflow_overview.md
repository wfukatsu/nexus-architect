# レガシーリファクタリングワークフロー

## 概要

既存システムを分析・評価し、マイクロサービスアーキテクチャへの移行設計を策定する。

## フェーズ

```
Phase 0: Investigation（調査）
  /investigate-system → 技術スタック、構造、負債、DDD準備度
  /security-analysis → セキュリティ態勢評価（オプション）

Phase 1: Analysis（分析）
  /analyze-system → ユビキタス言語、アクター、ドメインマッピング
  /analyze-data-model → データモデル、ER図（オプション）

Phase 2: Evaluation（評価）
  /evaluate-mmi + /evaluate-ddd → 並列実行
  /integrate-evaluations → 統合評価、改善計画

Phase 3: Design（設計）
  /map-domains → ドメイン分類
  /ddd-redesign → 境界コンテキスト再設計
  /design-microservices → ターゲットアーキテクチャ
  /select-scalardb-edition → エディション選定（ScalarDB利用時）
  /design-scalardb | /design-data-layer → データ層設計
  /design-api → API仕様

Phase 4: Implementation（実装設計）
  /design-implementation → 実装仕様
  /generate-test-specs → テスト仕様
  /generate-scalardb-code → コード生成（ScalarDB利用時）

Phase 5: Infrastructure（インフラ）
  /design-infrastructure → インフラ構成
  /design-security → セキュリティ設計
  /design-observability → 可観測性設計
  /design-disaster-recovery → DR設計

Phase 6: Review（レビュー）
  5視点並列レビュー → /review-synthesizer → 品質ゲート判定

Phase 7: Report（報告）
  /compile-report → 統合HTMLレポート
  /estimate-cost → コスト見積もり
```

## 依存関係

各フェーズは前フェーズの完了を前提とするが、一部のスキルはオプション（スキップ可能）。
詳細は `skill-dependencies.yaml` を参照。
