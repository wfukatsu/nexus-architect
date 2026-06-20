# Using Nexus Architect with Codex

Nexus Architect remains a Claude Code plugin, but it can also be used from Codex through the repository's `AGENTS.md` compatibility rules.

## Setup

Clone the repository and install optional dependencies:

```bash
git clone https://github.com/wfukatsu/nexus-architect.git
cd nexus-architect
pip install -r requirements.txt
```

Optional, for Mermaid rendering:

```bash
npm install -g @mermaid-js/mermaid-cli
```

## How To Invoke Skills

Claude Code exposes slash commands such as `/product:start`, `/architect:start`, and `/scalardb:model`.

In Codex, use the same command text in chat. Codex maps it through `AGENTS.md`:

- `/product:start` reads `skills/product/start/SKILL.md` (product skills are nested under `skills/product/`)
- `/architect:start ./path/to/project` reads `skills/start/SKILL.md`
- `/architect:pipeline ./path/to/project` reads `skills/pipeline/SKILL.md`
- `/scalardb:model` reads `skills/model/SKILL.md`
- `/scalardb:review-code ./path/to/app` reads `skills/review-code/SKILL.md`

You can also ask directly, for example:

```text
Use skills/design-microservices/SKILL.md to design the target architecture for ./target-app.
```

## Compatibility Rules

Codex interprets Claude Code tool references as local operations:

| Claude Code reference | Codex behavior |
|---|---|
| `Read` | Read files with shell commands such as `sed`, `cat`, or `rg` |
| `Write`, `Edit`, `MultiEdit` | Edit files with `apply_patch` |
| `Bash` | Run shell commands |
| `Glob`, `Grep`, `LS` | Use `rg --files`, `rg`, `find`, or `ls` |
| `WebFetch`, `WebSearch` | Use Codex web access, Context7, or approved `curl` |
| `AskUserQuestion` | Show numbered choices in chat and wait for a reply |
| `Task`, `Subagent` | Run in the main Codex thread unless the user explicitly asks for sub-agents |
| `Skill` | Open the referenced `SKILL.md` and follow it |

## Runtime Paths

Codex treats the repository root as `CLAUDE_PLUGIN_ROOT`.

Use these paths for normal outputs:

```text
reports/      analysis and design documents
generated/    generated code
work/         pipeline state and intermediate context
```

Some database migration skills intentionally use `.claude/configuration/databases.env` and `.claude/output/`. These are compatibility paths and can remain in place so Claude Code and Codex can share the same migration configuration.

When a skill refers to installed Claude reference docs under `.claude/docs/` or `.claude/rules/`, Codex uses the repository copies in `skills/common/references/` and `rules/`.

When a migration skill refers to subagent prompt templates under `${CLAUDE_PLUGIN_ROOT}/subagents/<db>/` or `${CLAUDE_PLUGIN_ROOT}/skills/common/subagents/<db>/`, Codex uses `skills/common/subagents/<db>/`.

## Validation

Claude Code can run the hooks automatically as `PostToolUse` hooks. Codex should run them manually when relevant:

```bash
hooks/validate-frontmatter.sh reports/before/example/technology-stack.md
hooks/validate-mermaid.sh reports/before/example/codebase-structure.md
```

Both hooks still accept Claude Code hook JSON on stdin, so Claude Code compatibility is preserved.

## Claude Code Compatibility

The Claude Code path is unchanged:

```bash
claude plugin marketplace add wfukatsu/nexus-architect
claude plugin install product@nexus-architect --scope user
claude plugin install architect@nexus-architect --scope user
claude plugin install scalardb@nexus-architect --scope user
```

After installation, use `/product:*`, `/architect:*`, and `/scalardb:*` commands as documented in `README.md`.
