# パイプライン進捗レジストリ

## JSONスキーマ: `work/pipeline-progress.json`

```json
{
  "$schema": "progress-registry-v1",
  "project_name": "sample-project",
  "target_path": "./target/path",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "options": {
    "scalardb_enabled": true,
    "workflow_type": "legacy|greenfield",
    "skip_phases": []
  },
  "phases": {
    "investigate-system": {
      "status": "pending|in_progress|completed|failed|skipped",
      "started_at": null,
      "completed_at": null,
      "outputs": [],
      "summary": ""
    }
  },
  "errors": [],
  "warnings": []
}
```

## ステータス値

| ステータス | 意味 |
|-----------|------|
| pending | 未実行 |
| in_progress | 実行中 |
| completed | 正常完了 |
| failed | 実行失敗 |
| skipped | スキップ（条件不一致またはユーザー指定） |

## レジューム動作

- `--resume-from=phase-N`: phase-N以降で status != completed のフェーズを実行
- `--rerun-from=phase-N`: phase-N以降を全て pending にリセットして再実行
- 自然なレジューム: completed フェーズは自動スキップ（冪等）

## オーケストレーターの利用パターン

1. パイプライン開始時に全フェーズを pending で初期化
2. 各スキル実行前に status を in_progress に更新
3. 完了時に outputs と summary を記録し completed に更新
4. 失敗時に errors に詳細を記録し failed に更新
5. 下流フェーズの依存が failed の場合、自動 skipped
