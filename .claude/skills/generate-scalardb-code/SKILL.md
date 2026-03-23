---
name: generate-scalardb-code
description: |
  設計仕様からSpring Boot + ScalarDBのJavaコードを自動生成する。
  /architect:generate-scalardb-code で呼び出し。ScalarDB利用プロジェクト専用。
model: opus
user_invocable: true
---

# ScalarDBコード生成

## 達成すべき結果

設計仕様と実装仕様からサービス別のJavaコードを生成する:
- エンティティクラス（ScalarDB Result マッピング）
- リポジトリ実装（Get/Put/Scan/Delete操作）
- ドメインサービス（トランザクション管理含む）
- Spring Boot設定（scalardb.properties、Config クラス）
- Gradle ビルド設定（build.gradle）
- Dockerfile

## 判断基準

- @.claude/rules/scalardb-coding-patterns.md のパターンに完全準拠
- @.claude/rules/spring-boot-integration.md の設定パターン適用
- トランザクション例外の適切なハンドリング（リトライ、ロールバック）
- エンティティは不変設計、値オブジェクトはイミュータブル

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/06_implementation/ | 必須 | /architect:design-implementation |
| reports/03_design/scalardb-schema.md | 必須 | /architect:design-scalardb |
| reports/07_test-specs/ | 推奨 | /architect:generate-test-specs |

## 出力

| ファイル | 内容 |
|---------|------|
| `generated/{service}/src/main/java/` | Javaソースコード |
| `generated/{service}/build.gradle` | ビルド設定 |
| `generated/{service}/Dockerfile` | コンテナ定義 |
| `generated/{service}/scalardb.properties` | ScalarDB設定 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /architect:design-implementation | 入力元 |
| /architect:design-scalardb | 入力元 |
| /architect:review-scalardb | レビュー対象（--mode=code） |
