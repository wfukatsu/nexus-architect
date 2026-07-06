# workflow/ — Legacy Workflow Documents

**Status: legacy / superseded.** These numbered workflow documents predate the
skills system. The current representation of the greenfield and legacy sequences
is the skill dependency manifest (`skills/common/skill-dependencies.yaml`) plus
the per-skill `SKILL.md` files — see `CLAUDE.md` for the command reference.

The one file still referenced by an active skill is
`greenfield/01_requirements_analysis.md`, which
`/architect:define-requirements` uses as its requirements-elicitation decision
tree. Do not delete it without updating `skills/define-requirements/SKILL.md`.

Everything else here (`greenfield/00`, `greenfield/02`–`13`, `legacy/`,
`templates/`) is retained for historical reference only and is not read by any
skill or orchestrator. Do not extend these documents; extend the skills instead.
