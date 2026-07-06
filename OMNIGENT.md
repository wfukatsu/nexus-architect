# OMNIGENT.md

Instructions for running this repository under **Omnigent**, a generic multi-agent
orchestrator, while preserving Claude Code plugin compatibility.

This file is the Omnigent counterpart of [`AGENTS.md`](AGENTS.md) (which targets
Codex) and [`CLAUDE.md`](CLAUDE.md) (which targets Claude Code). All three describe
the **same** skills; only the runtime translation differs. Nothing here modifies the
skills — Omnigent reads the existing `skills/*/SKILL.md` files directly.

## What This Repository Is

A three-plugin system-architecture toolkit originally packaged for Claude Code:

- **architect** — system architecture, refactoring, design, database migration, reporting
- **scalardb** — ScalarDB application development, review, configuration, scaffolding
- **product** — product-direction skills (vision → SLA/NFR), nested under `skills/product/`

There are ~90 `SKILL.md` files. Each is a self-contained instruction document. Under
Claude Code they are invoked as slash commands (e.g. `/architect:investigate`); under
Omnigent a worker resolves the command to a file, reads it, and follows it.

## Quick Start: the loader

A worker does not need to memorize the resolution rules below — it can call the loader,
which resolves the path, prints a translation preamble, and emits the skill body with
`${CLAUDE_PLUGIN_ROOT}` already expanded:

```bash
bash tools/omnigent/load-skill.sh architect:investigate     # flat (architect) skill
bash tools/omnigent/load-skill.sh scalardb:model            # flat (scalardb) skill
bash tools/omnigent/load-skill.sh product:define-vision     # nested product skill
bash tools/omnigent/load-skill.sh investigate               # bare name → architect namespace
bash tools/omnigent/load-skill.sh --list                    # enumerate every skill
```

The loader exits non-zero (with a stderr message naming what it looked up) when a skill
does not exist. See [`tools/omnigent/README.md`](tools/omnigent/README.md).

## Slash → Path Resolution

When a user invokes a Claude-style command, map it to the matching local file. There are
**three** plugins; only `product` is nested.

| Command form        | Resolves to                          |
|---------------------|--------------------------------------|
| `/architect:<name>` | `skills/<name>/SKILL.md`             |
| `/scalardb:<name>`  | `skills/<name>/SKILL.md`             |
| `/product:<name>`   | `skills/product/<name>/SKILL.md`     |

`architect` and `scalardb` share the flat `skills/` directory — both prefixes (and a
bare `<name>` with no prefix) resolve flat skills identically. `product` skills are the
only ones nested under `skills/product/`.

**Nested sub-skills.** The migration routers (`migrate-oracle`, `migrate-mysql`,
`migrate-postgresql`) delegate to sub-skills that are *not* slash commands — they are
read by path, e.g. `skills/migrate-oracle/migrate-oracle-to-scalardb/SKILL.md`. The
router body references them via `${CLAUDE_PLUGIN_ROOT}/skills/...` paths, which the
loader expands automatically. They are also loadable directly:
`load-skill.sh architect:migrate-oracle/migrate-oracle-to-scalardb`.

If a referenced skill does not exist, explain that it is unavailable and choose the
closest documented fallback.

## Path Resolution: `${CLAUDE_PLUGIN_ROOT}` and `@`-prefixes

Repository root is an **absolute path** — the loader prints it as
`CLAUDE_PLUGIN_ROOT == <absolute root>` in its preamble. Resolve `${CLAUDE_PLUGIN_ROOT}`,
`@rules/`, `@templates/`, `@skills/` and other repo-relative paths against this absolute
root; **do NOT assume your CWD equals it** (the loader never `cd`s). Treat the repository
root as the plugin root:

- `${CLAUDE_PLUGIN_ROOT}` → the absolute repo root. The loader substitutes any literal
  `${CLAUDE_PLUGIN_ROOT}` in a skill body with the absolute root before emitting it, so a
  worker that uses the loader never sees the raw token. If a worker reads a `SKILL.md`
  directly (without the loader), it must perform this substitution itself.
- `@rules/...`, `@templates/...`, `@skills/...` → resolve as repository-relative paths.

Runtime output directories (repository-relative):

| Purpose            | Path                          |
|--------------------|-------------------------------|
| Reports            | `reports/`                    |
| Generated code     | `generated/`                  |
| Pipeline state     | `work/`                       |
| Rules              | `rules/`                      |
| Common references  | `skills/common/references/`   |
| Subagent templates | `skills/common/subagents/`    |

## Claude Tool → Omnigent Tool Mapping

Skill bodies mention Claude Code tools. Interpret them as Omnigent tools:

| Claude tool        | Omnigent tool   | Notes                                    |
|--------------------|-----------------|------------------------------------------|
| `Read`             | `sys_os_read`   | read a file                              |
| `Write`            | `sys_os_write`  | create/overwrite a file                  |
| `Edit` / `MultiEdit` | `sys_os_edit` | in-place edit                            |
| `Bash`             | `sys_os_shell`  | run a shell command                      |
| `Grep`             | `sys_os_shell`  | `rg` / `grep` within the shell           |
| `Glob`             | `sys_os_shell`  | `rg --files` / `find` within the shell   |
| `LS`               | `sys_os_shell`  | `ls`                                     |
| `WebFetch` / `WebSearch` | (orchestrator web capability) | when network is approved      |

## `Task(...)` Blocks → Sequential Bodies or Orchestrator Dispatch

Several skills (notably the 5-perspective parallel reviews and the migration routers)
spawn Claude sub-agents via `Task(...)`. Under Omnigent, for each `Task` prompt body:

- **Default (sequential):** run each prompt body one after another in the same worker
  and have the orchestrator aggregate the results.
- **Parallel (orchestrator capability):** genuine concurrent sub-agent execution is
  performed by the **orchestrator** via the session/sub-agent dispatch API (e.g.
  `sys_session_send`), not by a plain worker.

> **Note:** `sys_call_async` dispatches a registered local **Python tool**, not an
> agent/sub-agent session — do **not** use it to run `Task(...)` prompt bodies.

Either way, the **orchestrator** computes any composite scores *after* collecting all
results — individual sub-agents only return their own findings (e.g. each review writes
`reports/review/individual/review-<perspective>.json`; the synthesizer merges them).

## `AskUserQuestion` → Orchestrator ↔ Human Gate

When a skill asks a multiple-choice question (`AskUserQuestion`) or otherwise needs human
input:

1. Present the choices as a **numbered list**.
2. **Pause** the run and surface the question to the human via the orchestrator's gate.
3. **Resume** when the human replies, using their selection.

When a skill is run with `--auto` (or a `--profile=...` in the product pipeline),
interactivity is bypassed: pick the documented default for each gate and continue without
pausing.

## Hooks → Explicit Validation Gate

Under Claude Code, two `PostToolUse` hooks fire automatically after every `Write`/`Edit`
(see `hooks/hooks.json`):

- `hooks/validate-frontmatter.sh` — every `reports/**/*.md` must open with valid YAML
  frontmatter containing `title`, `schema_version`, `skill`.
- `hooks/validate-mermaid.sh` — Mermaid diagram syntax.

**These do NOT auto-fire under Omnigent.** After writing any report `.md`, run them as an
explicit gate (both scripts already support CLI mode — pass file paths as arguments):

```bash
bash hooks/validate-frontmatter.sh <file.md>
bash hooks/validate-mermaid.sh <file.md>
```

A **non-zero exit** means the file has a frontmatter or diagram error — fix it before
continuing. Run both after each report write, not in a batch at the end.

## `model:` Frontmatter

Each `SKILL.md` carries a `model:` tier (opus / sonnet / haiku). Under Omnigent either:

- **ignore it** and use a single capable session model throughout (simplest), or
- **map the tier** to a per-dispatch model when the orchestrator supports model selection.

Recommended tiers (from the skill frontmatter): **opus** for judgment-heavy work
(`analyze`, `redesign`, `design-microservices`, `design-scalardb`, `design-api`,
`map-domains`, `review-risk`, and the product strategy skills), **sonnet** for standard
analysis/generation/reviews, **haiku** for templating (`init-output`, `render-mermaid`).
Prefer Sonnet-or-above for anything not explicitly haiku-tier.

## Pipeline Sequencing

`skills/pipeline/SKILL.md` (and `skills/start/SKILL.md`) are orchestrators — they do no
analysis themselves. To run a pipeline under Omnigent:

1. Read the DAG from `skills/common/skill-dependencies.yaml` (the architect pipeline) or
   `skills/product/common/skill-dependencies.yaml` (the product pipeline). Each entry
   lists `depends_on`, `parallel_with`, `conditions`, `outputs`, and `model`.
2. Execute phases in dependency order; run `parallel_with` groups concurrently (see the
   `Task` dispatch section). Honor `conditions` (e.g. `scalardb_enabled` selects
   `review-scalardb`; `scalardb_disabled` selects `review-data-integrity`).
3. Track progress in `work/pipeline-progress.json` (plain data — not a Claude construct).
   It also holds `options.output_language` (`en` default, `ja` supported).

The `disable-model-invocation: true` frontmatter on orchestrator files is a Claude Code
hint; Omnigent ignores it and treats the file as the orchestration spec above.

## Interaction Rules

- **Non-invasive.** Do not modify `.claude-plugin/`, `CLAUDE.md`, `AGENTS.md`, the
  `SKILL.md` bodies, `rules/`, `templates/`, or `hooks/`. Omnigent adds only this file and
  the `tools/omnigent/` helpers; Claude Code compatibility is preserved.
- Present `AskUserQuestion` choices as a numbered list and wait for the human's reply
  (unless `--auto`).
- Keep generated outputs in the documented output directories with YAML frontmatter.
- After writing any report `.md` or Mermaid diagram, run **both** validation hooks and fix
  any non-zero exit before proceeding.

## Output Language

Configurable per project in `work/pipeline-progress.json` (`options.output_language`:
`en` default, `ja` supported). Report prose uses the configured language; YAML frontmatter
keys and Mermaid node IDs stay in English. See [`rules/output-conventions.md`](rules/output-conventions.md).
