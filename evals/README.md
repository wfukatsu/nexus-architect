# Behavioural evals

The contract suites (`bash tools/run-tests.sh`) check what a skill *says*. These cases check what
Claude *does* with it: given a request in a user's own words, naming no command, is the right entry
point chosen — and is none chosen for a request the toolkit has nothing to do with.

```bash
tools/eval-plugin.sh architect                  # that plugin's cases, three runs each
tools/eval-plugin.sh product --runs 1           # any `claude plugin eval` option follows
tools/eval-plugin.sh architect --case migrate-database --runs 6 -j 6
```

One plugin per run, because a case is a statement about one plugin: with only `product` loaded,
`product:start` is the right answer to a product idea; with all four it would compete with
`architect:start` and the case would be measuring something else.

Each run is a full Claude session on your own credential. All six cases at three runs each cost
about USD 3.3 on Opus (measured 2026-10-08, Claude Code v2.1.294); `--model sonnet` and `--runs 1`
make an iteration loop cheaper. That is why this is **not** in CI: it needs a credential and it
spends money on every push. Run it when a `description` changes — that field is what decides
whether a skill is chosen.

## Why a runner, not `claude plugin eval .`

`claude plugin eval` loads a plugin from a directory holding `.claude-plugin/plugin.json`. This
repository has none: the four plugins are entries in `marketplace.json` that share one source
directory and differ in their `skills` list. Measured on v2.1.294:

- pointed at the repository, the eval loads one plugin named `nexus-architect` with the 101 skills
  directly under `skills/` — no product or infra skill, every name under the wrong prefix;
- pointed at an installed plugin (`product@nexus-architect`), it loads no plugin at all.

`tools/eval-plugin.sh` therefore stages what Claude Code builds at install time: a temporary copy
of the tree with a `plugin.json` carrying the marketplace entry's name and skill list, and with the
other plugins' `SKILL.md` files removed — `skills` in `plugin.json` adds to the default scan of
`skills/` rather than replacing it. Skills are then invoked as `<plugin>:<skill>`, as an installed
user's are. It always passes `--ablation none`: every grader here asks whether a skill fired, which
a no-plugin baseline cannot pass by construction.

## Writing a case

One directory per case under `triggers/`: `prompt.md` (the request, plus run limits and tags in
frontmatter) and `graders/*.md`.

- Tag the case with exactly one plugin name; that is how the runner selects it. Do not set
  `plugins:` — the runner stages the plugin.
- Phrase the prompt as a user would, never naming the skill.
- Grade the skill the request *should* reach, as `<plugin>:<skill>`. A specific request may rightly
  reach a more specific skill than the entry point — "help me work out the vision" goes to
  `product:define-vision`, not `product:start` — so either ask for the whole journey or accept
  the alternatives (`architect:migrate-(?:database|oracle|mysql|postgresql)`).
- Run a new case more than three times before trusting it. The migration case passed 3/3 twice and
  then 2/3: half the time Claude chose `architect:start` for "move our legacy systems to ScalarDB".
  That was the descriptions' fault, not the case's, and it was the descriptions that changed.

`evals/evals.test.py` (run by `tools/run-tests.sh`, no model involved) keeps the cases loadable:
each has a prompt naming no slash command, one plugin tag, a typed grader, and a `skill-fired`
grader naming skills that plugin registers; and every plugin has at least one case.

Results are written to `evals/results/`, which is git-ignored.
