---
description: |
  Initialize output directories and pipeline-progress.json.
  /architect:init-output [project_name]. Use --reset to reinitialize.
model: haiku
user_invocable: true
---

# Output Initialization

## Expected Outcome

Create the directory structure and progress management files required for pipeline execution.

## Execution Steps

1. Create the following directories:
   - `reports/before/{project}/`
   - `reports/00_summary/`
   - `reports/01_analysis/`
   - `reports/02_evaluation/`
   - `reports/03_design/`
   - `reports/review/individual/`
   - `generated/`
   - `work/`

2. Initialize `work/pipeline-progress.json` (register all phases from skill-dependencies.yaml as "pending", each with the fields defined in @skills/common/progress-registry.md). Include the `output_language` field under options, defaulting to `"en"`, and `confirm_versions`, defaulting to `true` (whether codegen skills confirm resolved dependency versions with the user — see @rules/dependency-versions.md).

3. Create `work/context.md` as an empty file.

## Options

- `--reset`: Back up the existing pipeline-progress.json before reinitializing.

## Completion Criteria

The directory structure and pipeline-progress.json exist.
