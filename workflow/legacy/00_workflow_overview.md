# レガシーリファクタリングワークフロー

## 概要

既存システムを分析・評価し、マイクロサービスアーキテクチャへの移行設計を策定する。

## フェーズ

```
Phase 0: Investigation（調査）
  /architect:investigate → 技術スタック、構造、負債、DDD準備度
  /architect:investigate-security → セキュリティ態勢評価（オプション）

Phase 1: Analysis（分析）
  /architect:analyze → ユビキタス言語、アクター、ドメインマッピング
  /architect:analyze-data-model → データモデル、ER図（オプション）

Phase 2: Evaluation（評価）
  /architect:evaluate-mmi + /architect:evaluate-ddd → 並列実行
  /architect:integrate-evaluations → 統合評価、改善計画

Phase 3: Design（設計）
  /architect:map-domains → ドメイン分類
  /architect:redesign → 境界コンテキスト再設計
  /architect:design-microservices → ターゲットアーキテクチャ
  /architect:select-scalardb-edition → エディション選定（ScalarDB利用時）
  /architect:design-scalardb | /architect:design-data-layer → データ層設計
  /architect:design-api → API仕様

Phase 4: Implementation（実装設計）
  /architect:design-implementation → 実装仕様
  /architect:generate-test-specs → テスト仕様
  /architect:generate-scalardb-code → コード生成（ScalarDB利用時）

Phase 5: Infrastructure（インフラ）
  /architect:design-infrastructure → インフラ構成
  /architect:design-security → セキュリティ設計
  /architect:design-observability → 可観測性設計
  /architect:design-disaster-recovery → DR設計

Phase 6: Review（レビュー）
  5視点並列レビュー → /architect:review-synthesizer → 品質ゲート判定

Phase 7: Report（報告）
  /architect:report → 統合HTMLレポート
  /architect:estimate-cost → コスト見積もり
```

## 依存関係

各フェーズは前フェーズの完了を前提とするが、一部のスキルはオプション（スキップ可能）。
詳細は `skill-dependencies.yaml` を参照。
