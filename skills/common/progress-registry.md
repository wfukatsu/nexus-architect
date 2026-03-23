# Pipeline Progress Registry

## JSON Schema: `work/pipeline-progress.json`

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
    "output_language": "en",
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

## Status Values

| Status | Meaning |
|--------|---------|
| pending | Not yet executed |
| in_progress | Currently running |
| completed | Finished successfully |
| failed | Execution failed |
| skipped | Skipped (condition not met or user-specified) |

## Resume Behavior

- `--resume-from=phase-N`: Execute phases from phase-N onward where status != completed
- `--rerun-from=phase-N`: Reset all phases from phase-N onward to pending and re-execute
- Natural resume: Completed phases are automatically skipped (idempotent)

## Orchestrator Usage Patterns

1. Initialize all phases as pending at pipeline start
2. Update status to in_progress before each skill execution
3. Record outputs and summary upon completion, then update to completed
4. Record details in errors upon failure and update to failed
5. Automatically skip downstream phases when a dependency has failed
