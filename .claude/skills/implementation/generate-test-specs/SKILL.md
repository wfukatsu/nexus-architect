---
name: generate-test-specs
description: |
  BDDシナリオ、ユニットテスト、統合テスト、パフォーマンステストの仕様を生成する。
  /generate-test-specs で呼び出し。design-implementation の出力を前提条件とする。
model: sonnet
user_invocable: true
---

# テスト仕様生成

## 達成すべき結果

実装仕様に基づき、包括的なテスト仕様を生成する:
- **BDDシナリオ**: Gherkin形式のフィーチャーファイル
- **ユニットテスト仕様**: サービス・リポジトリ・値オブジェクトのテストケース
- **統合テスト仕様**: サービス間連携、DB操作の統合テスト
- **パフォーマンステスト仕様**: 負荷条件とSLO検証

## 判断基準

- 各集約のCRUD操作が最低1つのBDDシナリオでカバーされること
- 境界値、エラーケース、並行処理のテストケースを含むこと
- ScalarDB利用時はOCC競合シナリオのテストを含むこと

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/06_implementation/ | 必須 | /design-implementation |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/07_test-specs/bdd-scenarios/` | Gherkin .feature ファイル |
| `reports/07_test-specs/unit-test-specs.md` | ユニットテストケース |
| `reports/07_test-specs/integration-test-specs.md` | 統合テストケース |
| `reports/07_test-specs/performance-test-specs.md` | パフォーマンステスト条件 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /design-implementation | 入力元 |
| /generate-scalardb-code | 関連（テストコード生成） |
