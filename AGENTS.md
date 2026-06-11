# AGENTS.md

Instructions for using this repository with Codex while preserving Claude Code plugin compatibility.

## What This Repository Is

This repository is a dual-plugin architecture toolkit originally packaged for Claude Code:

- `architect`: system architecture, refactoring, design, migration, and reporting skills
- `scalardb`: ScalarDB application development, review, configuration, and scaffolding skills

Claude Code continues to use `CLAUDE.md`, `.claude-plugin/`, and slash commands such as `/architect:start`.
Codex uses this `AGENTS.md` file plus the `skills/*/SKILL.md` files directly.

## Codex Command Mapping

When the user invokes a Claude-style command in Codex, map it to the matching local skill:

- `/architect:<name>` -> read and follow `skills/<name>/SKILL.md`
- `/scalardb:<name>` -> read and follow `skills/<name>/SKILL.md`
- `@rules/...`, `@templates/...`, and `@skills/...` -> resolve as repository-relative paths

If a referenced skill does not exist, explain that it is unavailable and choose the closest documented fallback.

## Claude Tool Mapping

Many skill files mention Claude Code tools. In Codex, interpret them as follows:

- `Read`: use `sed`, `cat`, or `rg` to read files
- `Write`: create files with `apply_patch`
- `Edit` / `MultiEdit`: use `apply_patch`
- `Bash`: use shell commands
- `Grep`: use `rg`
- `Glob`: use `rg --files` or `find`
- `LS`: use `ls`
- `WebFetch` / `WebSearch`: use Codex web access, Context7, or `curl` when network access is approved
- `AskUserQuestion` / `Question`: present numbered choices in chat and wait for the user's reply
- `Task` / `Subagent`: run the steps in the main Codex thread unless the user explicitly asks for sub-agents
- `Parallel`: use parallel shell reads where useful; keep code-writing steps coordinated
- `TodoWrite` / `TodoRead`: use local todo files only if the task requires persistent todos
- `Skill`: open the referenced `SKILL.md` and follow it
- `ExitPlanMode`: ignore

## Runtime Paths

Prefer repository-relative paths for Codex execution:

- Reports: `reports/`
- Generated code: `generated/`
- Pipeline state: `work/`
- Rules: `rules/`
- Common references: `skills/common/references/`
- Subagent prompt templates: `skills/common/subagents/`

Skills reference plugin files via `${CLAUDE_PLUGIN_ROOT}/...` (e.g.
`${CLAUDE_PLUGIN_ROOT}/skills/common/references/api-reference.md`,
`${CLAUDE_PLUGIN_ROOT}/rules/scalardb-crud-patterns.md`). In Codex, resolve
these as repository-relative paths (see the `CLAUDE_PLUGIN_ROOT` note below).

Legacy fallbacks (only if an old skill copy still mentions them):

- `.claude/docs/*` -> `skills/common/references/*`
- `.claude/rules/*` -> `rules/*`

For migration skills that mention `.claude/configuration/databases.env` or `.claude/output/`, keep those paths unless the user asks to migrate the runtime state. They are compatibility paths and can be used by both Claude Code and Codex.

When a skill mentions `CLAUDE_PLUGIN_ROOT`, treat the repository root as the plugin root in Codex.

- `${CLAUDE_PLUGIN_ROOT}/skills/common/subagents/<db>/` -> `skills/common/subagents/<db>/` (subagent prompt templates for migration skills)
- `${CLAUDE_PLUGIN_ROOT}/subagents/<db>/` -> `skills/common/subagents/<db>/` (legacy subagent prompt path)

## Pipeline Skill

`skills/pipeline/SKILL.md` is an orchestrator. It does not perform analysis itself — it reads
`skills/common/skill-dependencies.yaml` to determine execution order, then invokes each phase's
`SKILL.md` in sequence. When running the pipeline in Codex, follow the dependency graph manually:
read each skill file in order and execute it before moving to the next phase.

The `disable-model-invocation: true` frontmatter in that file is a Claude Code plugin hint; Codex
does not interpret it, so treat the file as the orchestration specification described above.

## Model Recommendations

Claude Code switches models automatically based on the `model:` frontmatter. In Codex the flag is
ignored — the session model is used throughout. For best results, prefer a capable model (equivalent
to Sonnet or above) for the following skill groups:

| Recommended: Opus equivalent | Recommended: Sonnet equivalent | Haiku equivalent sufficient |
|---|---|---|
| analyze, create-domain-story, design-api, design-data-layer, design-implementation, design-infrastructure, design-microservices, design-scalardb, generate-scalardb-code, map-domains, redesign | analyze-data-model, design-disaster-recovery, design-observability, design-scalardb-analytics, design-security, estimate-cost, evaluate-ddd, evaluate-mmi, generate-infra-code, generate-test-specs, integrate-evaluations, investigate, investigate-security, migrate-database, migrate-mysql, migrate-oracle, migrate-postgresql, pipeline, review-*, select-scalardb-edition | init-output, render-mermaid |

## Interaction Rules

- Preserve Claude Code compatibility. Do not remove `.claude-plugin/`, `CLAUDE.md`, or Claude-specific frontmatter unless explicitly asked.
- If a skill asks for multiple-choice input with `AskUserQuestion`, show the choices as a numbered list and wait for the user's answer before continuing.
- If a skill asks for parallel Claude subagents, execute the prerequisite steps in order and only parallelize independent shell reads or explicit user-approved agent work.
- Keep generated outputs in the documented output directories and include YAML frontmatter for Markdown reports.
- After editing any report Markdown file or Mermaid diagram, you **must** run the validation hooks before proceeding:
  - `hooks/validate-frontmatter.sh <file.md>`
  - `hooks/validate-mermaid.sh <file.md>`

  A non-zero exit means the file has a frontmatter or diagram error — fix it before continuing.
