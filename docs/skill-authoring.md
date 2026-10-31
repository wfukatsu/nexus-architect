# Skill Authoring

Contributor reference for writing and changing `skills/**/SKILL.md`. `AGENTS.md` § Repository
Mechanics states the rules; this page holds the measurements and history behind them, read on
demand. Every measurement names the Claude Code version it was taken on — re-measure before
relying on one after an upgrade.

## Anatomy of a skill

Each skill is a single self-contained `skills/<name>/SKILL.md` with YAML frontmatter and a body in
the house structure: Desired Outcome → Decision Criteria → Prerequisites table → steps. The body
references shared knowledge via `@rules/...`, `@templates/...`, `@skills/common/...` and `@docs/...`
paths. That notation is this repository's, not Claude Code's: `@` imports work in CLAUDE.md only, so
in a SKILL.md it is plain text, and an installed skill runs with the user's project as its working
directory. Every SKILL.md that uses the notation therefore opens with the `Shared files:` line that
anchors it to `${CLAUDE_PLUGIN_ROOT}`:

```
Shared files: a path written `@rules/…`, `@skills/…`, `@templates/…` or `@docs/…` is relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` — not to the project being worked on. Read it from there.
```

`tools/docs_consistency.test.py` checks the line is there and that every cited file exists.

All SKILL.md prose, rules and embedded prompts are **English**; the per-project `output_language`
governs generated report content only.

### Frontmatter keys

| Key | Rule | Why |
|-----|------|-----|
| `description` | What the skill does and when to use it, ≤ 300 characters. No flags or usage notes | This is the text the model matches a request on. The listing that carries every skill's description is capped at 1 % of the context window; past the cap Claude Code drops descriptions, least-used skills first. On a machine with about 300 skills from other plugins, 54 of this toolkit's 95 listed skills had lost theirs — every `/scalardb:*` and `/infra:*` skill among them (`/skill-doctor`, v2.1.294). The test sums all descriptions against a listing budget |
| `argument-hint` | The argument signature (`'[target_path] [--auto]'`), repeated as the body's `**Usage:**` line | `argument-hint` is an autocomplete hint, not part of the skill's content |
| `model` | `opus` \| `sonnet` \| `haiku`, or `inherit` on the two interactive orchestrators | See § Where `model` takes effect |
| `disable-model-invocation: true` | On skills that run only when explicitly called | |
| `allowed-tools` | On the nine skills whose whole job is one bundled script (status dashboards, the two report builders, `update-knowledge`, `infra:start`, `investigate-db-design`). Each entry names that one script under `${CLAUDE_PLUGIN_ROOT}` (which expands here), in a quoted and an unquoted spelling, because a quoted path is a different command from an unquoted one | Measured on v2.1.294: it holds when the user types the slash command, and not reliably when a model invokes the skill — 0 of 3 in the main session, 3 of 5 inside a sub-agent. So it does nothing for the pipeline's phases, and a non-interactive run still needs its permissions from whoever starts it. Skills that connect to a database, generate code or fetch from the network are left to ask |

There is deliberately **no `name`**: the directory names the skill. On a plugin skill `name`
additionally registers the bare command (`/start` beside `/architect:start` — measured on
v2.1.294), and eight names are shared between plugins, `start` by three, so the alias would go to
whichever plugin loaded first. The Agent Skills specification asks for the field; the Codex and
omnigent runtimes resolve skills by path and do not need it. The test rejects it.

A registered skill is a slash command by default; there is no key to opt in (`user-invocable`
exists only to opt *out* with `false`). The test rejects any frontmatter key outside the set Claude
Code documents — an unrecognised key is silently ignored at load time, which is how
`user_invocable` survived on 116 skills while doing nothing.

### Size

A SKILL.md is loaded whole when the skill runs, so it stays under 500 lines: what one step alone
needs — a file template, a display format, a long code example — goes in a `reference/` file beside
it that the step says to read. What must not be skipped (the order of steps, stop conditions,
exception rules) stays in the body. The test enforces the ceiling. `design-aggregate` was the one
exemption until its manifest shape, catalog shape and document template moved to
`skills/design-aggregate/reference/`, which is the pattern to follow: the step that writes a file
names the reference file that gives its shape, and the judgment rules the validator cannot check
stay in the body.

### Registration

`.claude-plugin/marketplace.json` lists the skill directories each plugin ships. Adding a skill is
two edits: create `skills/<name>/SKILL.md` **and** register its path in the plugin's `skills` array.
An unregistered SKILL.md will not surface as a slash command. The one deliberate exception is the
ten migration sub-skills nested under `skills/migrate-{oracle,mysql,postgresql}/`: the parent router
reads them by `${CLAUDE_PLUGIN_ROOT}/skills/...` path, so leaving them unregistered is intentional
there and a bug anywhere else.

## Where `model` takes effect

Measured on Claude Code v2.1.293–294 (issue #52). A skill's `model` applies when the user types its
slash command, for that turn. It does **not** apply when another skill invokes it in the same turn —
the phase then runs on the invoking skill's model — and it does not apply inside a sub-agent, which
runs on the `model` passed on the call or, with none, on the user's sub-agent default. Two rules
follow, and `skills/common/subagent-model.test.py` enforces both:

- **Every sub-agent call names its `model`**, the calling skill's own tier unless it says otherwise
  (`skills/common/sub-agent-patterns.md` § Always pass `model`).
- **`/architect:pipeline` runs every phase as a sub-agent on the manifest's `model`**, never inline
  (`skills/pipeline/SKILL.md` § Phase Execution). The price is that a phase cannot ask the user:
  what it would have asked is recorded `unasked` in the Open Questions store. Phase calls pass
  `run_in_background: false` and tell the phase to do the same for its own sub-agents: a
  non-interactive run otherwise launches parallel calls in the background and loses the ones still
  running when a turn ends. A parallel group goes out three phases at a time, because Claude Code
  runs 20 sub-agents at once and counts the ones each phase spawns. And no phase output is a Markdown
  file named `report*`, `summary*` or `findings*`: a sub-agent's Write of one is refused.

**The interactive orchestrators declare `model: inherit`.** `/architect:start` and `/product:start`
run dialogue-driven phases inline, because only the main conversation can ask the user, and an
inline phase runs on what the conversation runs on — a tier on the orchestrator would be the tier of
every one of them. Inline phases therefore run on the session's model (the orchestrators suggest
`/model opus` when it is smaller); `/architect:start` sends every phase that is not dialogue-driven
to a sub-agent on its manifest model and then asks the user what that phase could not, and
`/product:start --auto` does the same for all of its phases. In an interactive session those
sub-agents run in the background whatever the skill asks — on v2.1.295 the main session's Agent tool
has no `run_in_background` parameter, and all 21 phase calls of a full `/architect:start` run were
launched that way — so both orchestrators say what to do then: end the turn, resume on the
completion notice, and settle a phase's questions before starting what depends on it.

**`effort` behaves as `model` does, and no phase sets it.** Measured on v2.1.294, reading the level
each request actually ran at from the transcript: a skill's `effort` applies when the user types its
command; it does not apply when a model invokes the skill, in the main session or inside a
sub-agent; an `effort` passed on the Agent call does apply. So a per-phase level would have to live
in the manifest and be passed on the call, exactly as `model` is. None is declared: every phase of
the full runs completed at the session's level, and nothing observed gives a reason to raise or
lower one. (`${CLAUDE_EFFORT}` in a skill body prints the skill's declared value even when it is
not in effect — do not use it to check.)

### Tier criteria per plugin

The **architect** tiers are the manifest's (`skills/common/skill-dependencies.yaml`); the
extension-tier and utility skills carry theirs in frontmatter. The **product** plugin follows the
same tiers in its own manifest (`skills/product/common/skill-dependencies.yaml`): opus for
strategy and judgment, sonnet for structured generation, `inherit` for `start`, and haiku for
`report-status` — the one product skill the manifest does not list, since it is not a phase. The
**infra** plugin has no manifest — a router plus three modes — so every `model` lives in its own
frontmatter: opus for `design` and `review`, sonnet for `implement` and `start`. Its criterion
differs from the tiers above and is stated in `skills/infra/start/SKILL.md` § Model Policy: how
hard the error is to undo, times how many tokens it generates. Design and review emit little and
cost much when wrong; implementation emits the most and is held by written conventions plus
verification commands.

## Hooks: one copy per enabled plugin

`hooks/hooks.json` is loaded by every enabled plugin, because the four plugins share one source
root, and Claude Code keeps a plugin's copy of a handler separate: unguarded, one Write ran each
hook four times and the model read the same error four times. `hooks/claim.sh` (and its Python half
in `record_token_usage.py`) lets exactly one copy per `tool_use_id` do the work. Keep that guard in
any hook you add.

`validate-frontmatter.sh` is filtered to `reports/` by the handler's `if` (one handler per tool —
an `if` rule matches one tool's calls) and is inert outside a pipeline project: with no
`work/pipeline-progress.json` at or above the file, as the recorder is, because the plugins are
enabled per user and `reports/` is a common directory name (issue #60). In hook mode a failure
exits 2 (feeds the error back for self-correction); the same scripts exit 1 when run from the CLI
with file-path arguments. `record_token_usage.py` runs after Write/Edit/Agent in the background
(`async`) and, waiting, at Stop/SubagentStop — `claude -p` kills a background hook at teardown, and
the turn-end firing is the one that flushes the pending bucket.

## Checks that own these rules

`tools/docs_consistency.test.py` (frontmatter keys, description length and listing budget, the
`Shared files:` anchor and every `@`-path, the 500-line ceiling, `allowed-tools` entries,
`argument-hint` restated in the body), `skills/common/subagent-model.test.py` (every sub-agent call
names `model`), `hooks/hooks.test.py` (the matchers and the once-per-call guard). The per-suite
reference is `docs/test-suites.md`.
