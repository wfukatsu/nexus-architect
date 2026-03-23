---
name: full-pipeline
description: |
  依存関係順に全フェーズを自動実行するパイプライン。
  /full-pipeline [target_path] で呼び出し。
  --skip-*, --resume-from, --rerun-from フラグ対応。
model: sonnet
user_invocable: true
disable-model-invocation: true
---

# フルパイプライン実行

## 達成すべき結果

対象プロジェクトの包括的なアーキテクチャ分析・設計を完成させる。
最終成果物は reports/ 配下の完全なレポートセット。

## 利用可能なスキル

@.claude/skills/common/skill-dependencies.yaml の全スキルを依存順に実行可能。

## 実行戦略

1. `skill-dependencies.yaml` から依存グラフを読み込む
2. `/init-output` で出力ディレクトリを初期化
3. 各スキルを実行し、出力を検証してから次に進む
4. `parallel_with` が指定されたスキルは並列 Task で実行
5. `conditions` フィールドに基づき ScalarDB関連スキルの有効/無効を判断
6. 進捗を `work/pipeline-progress.json` に記録
7. フェーズ間で `work/context.md` に発見事項を蓄積

## コマンドラインオプション

- `--skip-{phase}`: 指定フェーズをスキップ
- `--resume-from=phase-N`: 指定フェーズから再開（完了済みフェーズはスキップ）
- `--rerun-from=phase-N`: 指定フェーズ以降を全て "pending" にリセットして再実行
- `--analyze-only`: 分析フェーズのみ実行
- `--no-scalardb`: ScalarDB関連スキルを全てスキップ

## エラー処理

- **必須前提ファイル欠損**: エラーログを記録し、下流フェーズを自動スキップ
- **スキル実行失敗**: pipeline-progress.json に status: "failed" を記録
- **依存フェーズ失敗**: 下流フェーズも自動スキップ

## コンテキスト管理

長いパイプラインではコンテキストウィンドウの制限を超える。
各フェーズ完了時に `work/context.md` を更新し、次のフェーズ開始時に読み込む。

```
work/context.md の構造:
- 調査結果サマリー
- 分析で抽出したドメイン知識
- 評価スコアと改善優先度
- 設計で行った重要な決定
- 未解決の問題
```

## 進捗レジストリ

@.claude/skills/common/progress-registry.md のスキーマに準拠。

## 完了条件

1. 全フェーズが completed または skipped
2. `reports/00_summary/executive-summary.md` が生成されている
3. pipeline-progress.json の status が "completed"

## 関連スキル

| スキル | 関係 |
|-------|------|
| /workflow | 対話版 |
| /init-output | 初期化 |
| /compile-report | 最終レポート |
