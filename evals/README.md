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

Each run is a full Claude session on your own credential. All seven cases at three runs each cost
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

## Outcome evals

The trigger cases above ask whether the right skill fired. The outcome evals ask what a run
left behind, and read the project directory only — never the transcript — so a run of this
toolkit, a rerun after a skill change, and a run of another toolkit on the same brief are
scored by one yardstick.

```bash
tools/eval-outcomes.sh list                                   # the tasks
tools/eval-outcomes.sh grade <project_dir> [<task>]           # free: score a project that already ran
tools/eval-outcomes.sh compare <a> <b> [<task>]               # free: two scorecards or projects side by side
tools/eval-outcomes.sh run ec-monolith-legacy --permission-mode bypassPermissions   # paid
tools/eval-outcomes.sh run greenfield-brief --permission-mode bypassPermissions --model opus
```

A headless `claude -p` run stops at its first permission prompt, so `run` needs
`--permission-mode bypassPermissions` (or `--dangerously-skip-permissions`) after the task name;
the scratch project under `evals/results/` is the only thing the run writes to, and it is its own
git repository (one commit holding the input), so a skill that reads `git log` or `git status` —
`verify-implementation`'s test-first record, `implement-backlog`'s git-ignore gate — sees the
project and not this toolkit's history. Every other
`claude -p` option passes through the same way, and `run` records them in the scorecard as
`claude_options`. `--max-budget-usd` caps each session, not the run: the full pipeline alone costs
about USD 65 on `samples/ec-monolith` at list price, and under a lower cap it degrades its method
to fit — narrower reviewer reads, no per-axis sub-agents — and says so under `warnings` in the
registry (the 2026-11-15 reference run of `ec-monolith-implementation` did, at USD 60), so give
the pipeline session USD 100 or more.

A task is `outcomes/<task>/`: `task.json` (the input directory, its `input_sha256` — the
fingerprint `tools/lib/outcome_graders.py fingerprint <dir>` prints, so a changed input is
noticed: `run` warns and records both hashes in the scorecard, `evals/evals.test.py` fails until
the pin is updated — the commands, the thresholds file), `task.md` (the brief, what each threshold
means, the reference run's numbers), `expected.json` (`{"<metric>.<field>": {"min" | "max" | "in" |
"equals": …, "required": true|false}}`) and, once a run exists, `reference-scorecard.json` — the
committed example of a scorecard. Three ship: `ec-monolith-legacy` (the sample monolith through
`--profile=full`; its reference scorecard grades the 2026-11-01 run, which was driven phase by
phase by hand rather than by `run` — `reference_run.not_from_runner` says so, and its cost and
duration are not a `run` baseline), `ec-monolith-implementation`
(the same input through the pipeline, the codegen chain and `verify-implementation --gate` — the
task that measures `quality_gate` and `test_results`; its reference scorecard grades the
2026-11-15 `run`: eight sessions, 4 h 43 min, USD 187 at list price) and
`greenfield-brief` (a one-page brief through `define-requirements` and `--profile=poc`; its
reference scorecard grades the 2026-11-15 `run`: two sessions, 40 min, USD 21 at list price).

The graders are `tools/lib/outcome_graders.py`, one per question a reader of the run would ask:

| metric | reads | answers |
|--------|-------|---------|
| `requirement_coverage` | `work/traceability.json` | the share of `FR-`/`NFR-` nodes a **design-tier** node cites — a `RULE-`/`EX-` example citing its `FR-` is requirements work, not coverage, and is listed apart as `cited_only_by_requirement_tier` — the uncovered ones, dangling upstream ids |
| `open_questions` | `work/context.md` § Open Questions | rows by status; `unasked` is what the run never asked |
| `adrs` | `reports/03_design/adr/` | records, validator errors, accepted records naming an approver |
| `report_validity` | `reports/**/*.md` | failures of the two output validators (frontmatter and ELI5, Mermaid) |
| `quality_gate` | `reports/09_verification/quality-gate.json` | verdict, stages by status, unit tests, mutation score, blocking ids |
| `test_results` | `generated/**/test-results/<suite>/*.xml` | pass rate per JUnit suite (`test`, `contractTest`, `acceptanceTest`, …) |
| `phase_completion` | `work/pipeline-progress.json` | phases by status, the profile, warnings |
| `cost` | `work/token-usage.json` | USD total and per phase (the hook records them) |
| `duration` | the registry's stamps | wall clock from the first `started_at` to the last `completed_at`, phase time summed |
| `human_effort` | `work/audit/events.jsonl` | questions asked / answered / deferred, gates rejected, phases revised — the review rounds |

An input that does not exist is **not measured**, never a zero that reads as a result. A
threshold over an unmeasured metric **fails** — the run was expected to produce that artifact —
unless the rule says `"required": false`, which lists it as unmeasured and moves on (the
pipeline-only task marks `quality_gate.verdict` so, since no codegen runs there). A thresholds
file with a misspelled key, a non-numeric bound or no comparison is refused before anything is
graded (`validate_expected`, exit 2), and a value its rule cannot compare is a failed check
carrying the error, never a traceback. The verdict is PASS when no check fails. `grade` exits 0 on
PASS, 1 on FAIL, 2 on a usage error.

### Comparing with another toolkit (the AI-DLC protocol)

1. **Same brief, same model, same harness.** Give the other toolkit `greenfield-brief/brief.md`
   (or the sample monolith) and ask it for the same deliverables the task's commands ask for:
   requirements, architecture, API contract, review. Run both on the same model and the same
   Claude Code version; record them in the write-up.
2. **Same yardstick.** Grade both output directories with `tools/eval-outcomes.sh grade <dir>
   <task>`, then put them side by side with `tools/eval-outcomes.sh compare <a> <b> <task>` (a
   scorecard JSON or a project directory on each side): one row per headline field and per
   threshold, with `not comparable` on every row one side did not measure. The graders read the
   shapes this toolkit writes; another toolkit's output is comparable on a metric only when it
   holds that shape — `cost`, `duration` and `test_results` need only a token ledger, timestamps
   and JUnit XML; `requirement_coverage`, `open_questions` and `adrs` need the traceability graph,
   the store and the ADR directory. A metric the other run cannot be measured on is **reported as
   not comparable**, not scored against it.
3. **Say which numbers are comparable.** The write-up carries the scorecards side by side, the
   list of comparable metrics, and what was converted (a toolkit that records questions in
   another shape and was mapped onto the store by hand says so).
4. **Run more than once.** A single run is a sample; the trigger cases taught that (3/3, 3/3,
   then 2/3). Three runs per side before a claim.

Results of `run` land under `evals/results/outcomes-<task>-<timestamp>/` with the scratch project,
the transcript, `scorecard.json` and `scorecard.txt`; the directory is git-ignored. A run worth
keeping as the task's reference is copied to `outcomes/<task>/reference-scorecard.json` with its
`project` path made relative and a `reference_run` note on how it was produced (the one
`ec-monolith-legacy` ships was graded from a by-hand run, not from `run`; the first runner run
replaces it).
