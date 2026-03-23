---
name: init-output
description: |
  出力ディレクトリとpipeline-progress.jsonを初期化する。
  /architect:init-output [project_name] で呼び出し。--reset で再初期化。
model: haiku
user_invocable: true
---

# 出力初期化

## 達成すべき結果

パイプライン実行に必要なディレクトリ構造と進捗管理ファイルを作成する。

## 実行内容

1. 以下のディレクトリを作成:
   - `reports/before/{project}/`
   - `reports/00_summary/`
   - `reports/01_analysis/`
   - `reports/02_evaluation/`
   - `reports/03_design/`
   - `reports/review/individual/`
   - `generated/`
   - `work/`

2. `work/pipeline-progress.json` を初期化（skill-dependencies.yaml の全フェーズを "pending" で登録）

3. `work/context.md` を空で作成

## オプション

- `--reset`: 既存の pipeline-progress.json をバックアップしてから再初期化

## 完了条件

ディレクトリ構造と pipeline-progress.json が存在すること。
