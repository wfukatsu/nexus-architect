# tools/omnigent

Compatibility helpers that let a generic multi-agent orchestrator (**Omnigent**) run the
nexus-architect skills, which are otherwise packaged as Claude Code plugins. See the
repository-root [`OMNIGENT.md`](../../OMNIGENT.md) for the full runtime mapping
(tools, `Task` dispatch, `AskUserQuestion` gating, hooks, pipeline sequencing).

These helpers are **additive and non-invasive** — they read the existing `skills/*/SKILL.md`
files and never modify them, the plugin manifest, or `CLAUDE.md` / `AGENTS.md`.

## `load-skill.sh`

Resolves a Claude-style slash command to the matching `SKILL.md`, prints a short
**translation preamble** (how to interpret Claude-specific constructs under Omnigent),
then prints the full skill body with `${CLAUDE_PLUGIN_ROOT}` expanded to the absolute
repository root.

### Usage

```bash
bash tools/omnigent/load-skill.sh <plugin>:<name>   # architect:investigate, scalardb:model, product:define-vision
bash tools/omnigent/load-skill.sh <name>            # bare name → architect (flat) namespace
bash tools/omnigent/load-skill.sh --list            # enumerate every skill across all 3 plugins
bash tools/omnigent/load-skill.sh --help            # usage
```

### Resolution rules (filesystem-only)

| Input                | Resolves to                       |
|----------------------|-----------------------------------|
| `architect:<name>`   | `skills/<name>/SKILL.md`          |
| `scalardb:<name>`    | `skills/<name>/SKILL.md`          |
| `product:<name>`     | `skills/product/<name>/SKILL.md`  |
| `<name>` (no prefix) | `skills/<name>/SKILL.md`          |

`architect` and `scalardb` share the flat `skills/` directory, so both prefixes resolve
flat skills identically. Nested migration sub-skills are reachable via a `parent/child`
name, e.g. `architect:migrate-oracle/migrate-oracle-to-scalardb`.

The repository root is determined robustly via `git rev-parse --show-toplevel`, falling
back to the script's own location, so the loader works from **any** current directory. It
resolves purely by filesystem and never reads `.claude-plugin/marketplace.json`.

### Exit status

- `0` — skill resolved and printed (or `--list` / `--help` succeeded).
- `1` — skill not found (stderr names exactly what was looked up).
- `2` — usage error (no/extra args, unknown option, or unknown plugin).

## `load-skill.test.sh`

Self-contained test suite. Discovers the real skill set from the filesystem (no hardcoded
counts) and exits non-zero on any failure.

```bash
bash tools/omnigent/load-skill.test.sh
```

It verifies: resolution of an architect, scalardb, and (nested) product skill; the bare-name
default; `${CLAUDE_PLUGIN_ROOT}` substitution (and that no literal token remains);
missing-skill handling (non-zero exit + stderr message); unknown-plugin rejection; that
`--list` returns more than zero entries, exits 0, and enumerates every `SKILL.md` on disk;
and that resolution still works from a non-repo-root CWD.

## Dependencies

POSIX `bash` + coreutils (`find`, `grep`, `sed`, `basename`, `dirname`) and `git` for root
detection (with a non-git fallback). No additional language runtime is required to run the
loader or the tests. The validation hooks referenced by `OMNIGENT.md`
(`hooks/validate-frontmatter.sh`, `hooks/validate-mermaid.sh`) use `python3`/`jq` exactly
as they already do under Claude Code; the loader itself does not.
