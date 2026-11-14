# Runtimes Assessment: Kiro, GitHub Copilot, Cursor

What it would take to run this toolkit's skills on three runtimes it does not support today, from
their public documentation as read on 2026-11-14. **Nothing below was executed on those runtimes**:
this is what the documents state and what follows from it, kept apart. The three runtimes the
toolkit does support are in `AGENTS.md` § Runtimes (Claude Code, Codex, Omnigent); the loader those
share is `tools/omnigent/load-skill.sh`.

## What a runtime has to offer

A skill here is a `SKILL.md` with frontmatter (`description`, `argument-hint`, `model`,
`allowed-tools`, `disable-model-invocation`) invoked as `/<plugin>:<name>`, whose body names Claude
Code tools (`Read`, `AskUserQuestion`, `Agent(...)` with `model`), cites `@rules/…` paths from the
plugin root, writes under `reports/` and `work/` of the project, and relies on three hooks
(`validate-mermaid.sh` and `validate-frontmatter.sh` after Write/Edit, `record_token_usage.py` after
Write/Edit/Agent and at Stop/SubagentStop). A runtime is a candidate when it can (1) load a
directory of `SKILL.md` files as invokable units, (2) run a shell command after a file write and at
the end of a turn, (3) delegate a prompt to a sub-agent, and (4) ask the user a question and wait.
The translation table in `AGENTS.md` § Skill vocabulary is what (1) and (3) need; (2) needs the
runtime's hook format; (4) is the numbered-list fallback `rules/open-questions.md` §8 already
states for Codex.

## Kiro (kiro.dev)

Stated by its documentation (`/docs/skills/`, `/docs/hooks/`, `/docs/hooks/types/`,
`/docs/custom-agents/`, `/docs/steering/`):

- Skills live in `.kiro/skills/<name>/SKILL.md` (workspace) or `~/.kiro/skills/`, and the page
  says they follow the open Agent Skills standard. `name` is required and must equal the folder
  name (lowercase, digits, hyphens, 64 characters at most); `description` is required (1,024
  characters at most); `license`, `compatibility` and `metadata` are optional. Skills are invoked
  as `/<skill-name>`, with the text after the name passed as context; `$ARGUMENTS` substitution
  is marked CLI-only. A custom agent loads a skill only when its `resources` lists it as
  `skill://`.
- Hooks are `.kiro/hooks/<id>.json`: `version`, a `hooks` array, each with `name`, `trigger`
  (Prompt Submit, Agent Stop, Session Start/End, Pre/Post Compaction, Pre/Post Tool Use, File
  Create/Save/Delete, Pre/Post Task Execution, Manual), a `matcher` for the tool-use triggers
  (tool ids, categories such as `write`, `@mcp`), an `action` of type `command` or `agent`, a
  `timeout`. Command actions run in the project root with session context on stdin. **No
  subagent-stop trigger** is listed.
- Custom agents are `.kiro/agents/<name>.json|.md` with `name`, `description`, `tools`,
  `resources`, `permissions`, `prompt`, `model`, and a `hooks` field the reference names.
- `AGENTS.md` at the repository root is read, always included, without inclusion modes.

What follows: the skill folders could be placed (or symlinked) under `.kiro/skills/` as they are,
with two edits per skill — a `name` equal to the directory, and the `description` as it is (ours are
under 300 characters). `argument-hint`, `model`, `allowed-tools` and `disable-model-invocation`
are **not in Kiro's documented field list**; whether they are ignored or rejected is not stated, so
a loader for Kiro would strip them and carry `model` into a custom agent per tier. The three hooks
map to `PostToolUse` with a `write` matcher and `AgentStop`; the SubagentStop firing has no
equivalent, which costs the token ledger its per-sub-agent checkpoint and nothing else. The
`/<plugin>:<name>` spelling becomes `/<name>` — the loader's bare-name resolution already exists.
`AGENTS.md` is read as it is.

## GitHub Copilot (CLI, cloud agent, IDE agent mode)

Stated by its documentation (`/copilot/concepts/agents/about-agent-skills`,
`/copilot/concepts/customizations/hooks`, `/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli`,
`/copilot/reference/customization-cheat-sheet`):

- Agent Skills are "an open standard"; skills are discovered in `.github/skills`, `.claude/skills`
  or `.agents/skills` (project) and `~/.copilot/skills` or `~/.agents/skills` (personal), in the
  app, the CLI, the cloud agent, code review and the IDE agent modes. Required frontmatter is not
  listed on the page read.
- Hooks are `.github/hooks/*.json` (`~/.copilot/hooks/*.json` for the CLI): `version`, a `hooks`
  object keyed by event — `sessionStart`, `sessionEnd`, `userPromptSubmitted`, `preToolUse`,
  `postToolUse`, `agentStop`, `subagentStop`, `errorOccurred` — each with `type: "command"`,
  `bash` / `powershell`, `cwd`, `env`, `timeoutSec`. Hooks run synchronously and block the agent.
  No per-tool matcher field is shown; the cloud agent supports a subset of events.
- Custom agents are `.github/agents/*.agent.md` with `name`, `description`, `model`, `tools`,
  `mcp-servers`; `/agent` selects one. `AGENTS.md` is read (nearest file wins); `CLAUDE.md` at the
  root is read too.
- Plugins bundle skills, custom agents, hooks and MCP servers.

What follows: the closest match of the three. `.claude/skills` as a discovery path means a
project could point at this repository's skill directories without moving them, and the plugin
shape maps onto Copilot's plugin. The hook events map one to one (`postToolUse`, `agentStop`,
`subagentStop`); the Write/Edit matcher has to move inside the scripts, which already read the tool
input from stdin. Unknown frontmatter handling is not documented; the `model` tier would move into
a custom agent per tier as for Kiro. Hooks blocking the agent changes the token recorder's
`async: true` into a synchronous wait of a few hundred milliseconds per firing.

## Cursor

Not assessed. The documentation index (`cursor.com/llms.txt`) lists rules, hooks, skills and
subagents pages, but every one returned 404 to a non-browser fetch on 2026-11-14, and the older
`docs.cursor.com` paths redirect to the product page. Nothing about `.cursor/rules/*.mdc`,
`.cursor/commands/*.md`, hooks or Agent Skills support could be verified, so nothing is claimed.

## What would be measured before support is promised

For each runtime, in this order, on one scratch project and the `greenfield-brief` outcome task
(`evals/README.md` § Outcome evals):

1. The skill is listed and `/investigate` (or the runtime's spelling) runs it to completion —
   which frontmatter keys were rejected, which ignored.
2. The three hooks fire where the runtime says they do, and the validators' exit codes reach the
   agent as feedback (Claude Code's exit 2 convention has no stated equivalent on either runtime).
3. `AskUserQuestion` is answered — by the runtime's own question tool or by the numbered-list
   fallback — and the answer lands in the store.
4. A phase that spawns sub-agents on a named model does so on that model (the ledger records it).
5. The outcome scorecard of the run against the same task's thresholds, beside Claude Code's.

Until those five are measured, `AGENTS.md` keeps naming three runtimes. A translation for Kiro or
Copilot would be a preamble in `tools/omnigent/` like the existing one — the loader already
resolves a bare name and expands the plugin root — plus a generated hook file per runtime; that is
the shape, not a promise.
