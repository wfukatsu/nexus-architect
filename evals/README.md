# Behavioural evals

The contract suites (`bash tools/run-tests.sh`) check what a skill *says*. These cases check what
Claude *does* with it: given a request in a user's own words, naming no command, is the right entry
point chosen — and is none chosen for a request the toolkit has nothing to do with.

```bash
claude plugin eval . --ablation none        # every case, three runs each
claude plugin eval . --case architect-start # one case
```

`--ablation none` because every grader here asks whether a skill fired, which a no-plugin baseline
cannot pass by construction; the comparison would cost twice as much and say nothing.

Each run is a full Claude session on your own credential. The four cases at three runs each cost
about USD 3.5 on Opus (measured 2026-10-08, Claude Code v2.1.294); `--model sonnet` and `--runs 1`
make an iteration loop cheaper. That is why this is **not** in CI: it needs a credential and it
spends money on every push. Run it when a `description` changes — that field is what decides
whether a skill is chosen.

## What a path target loads

`claude plugin eval .` loads this repository as one inline plugin named `nexus-architect`, with the
skills directly under `skills/` — the architect and scalardb skills, 101 of them. It does not read
`marketplace.json`, so the skills nested under `skills/product/` and `skills/infra/` are not loaded
and skill names carry the prefix `nexus-architect:` rather than `architect:` / `scalardb:`. Hence:

- graders match the skill name with any prefix (`(?:[\w-]+:)?start`), so the same case holds
  against an installed plugin;
- there is no case for `/product:start` or `/infra:start` yet. Those need an installed target
  (`claude plugin eval product@nexus-architect`), which reads the cases from the installed copy —
  possible only from the first release that ships this directory.

## Writing a case

One directory per case under `triggers/`: `prompt.md` (the request, plus run limits in frontmatter)
and `graders/*.md`. Phrase the prompt as a user would, never naming the skill. A specific request
may rightly reach a more specific skill than the router — "move our Oracle database" goes to
`migrate-oracle`, not `migrate-database` — so grade the skill the request *should* reach.

`evals/evals.test.py` (run by `tools/run-tests.sh`, no model involved) keeps the cases loadable:
every case has a prompt and a grader, and every skill a grader names exists.

Results are written to `evals/results/`, which is git-ignored.
