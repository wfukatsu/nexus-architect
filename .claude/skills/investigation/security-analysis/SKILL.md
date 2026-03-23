---
name: security-analysis
description: |
  OWASP Top 10対応状況、アクセス制御、ゼロトラスト準備状況を評価する。
  /security-analysis [target_path] で呼び出し。
model: sonnet
user_invocable: true
---

# セキュリティ分析

## 達成すべき結果

対象システムのセキュリティ態勢を評価し、脆弱性と改善点を報告する:
- OWASP Top 10 各項目の対応状況
- 認証・認可メカニズムの評価
- アクセス制御マトリクス（ゼロトラスト観点）
- シークレット管理、暗号化、監査ログの状況

## 判断基準

- OWASP Top 10の各項目について、コード内の具体的な対応/非対応箇所を特定する
- セキュリティ上のリスクはCRITICAL/HIGH/MEDIUM/LOWで分類する
- 即座に対応すべき脆弱性と、設計改善で対応すべき課題を区別する

## 前提条件

| ファイル | 必須/推奨 | 生成元 |
|---------|----------|--------|
| reports/before/{project}/ | 推奨 | /investigate-system |

## 出力

| ファイル | 内容 |
|---------|------|
| `reports/before/{project}/security-analysis.md` | OWASP評価、アクセス制御、脆弱性一覧 |

## 関連スキル

| スキル | 関係 |
|-------|------|
| /investigate-system | 関連（並行実行可能） |
| /review-operations | レビュー時に参照 |
