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

## Outcome evals

The trigger cases above ask whether the right skill fired. The outcome evals ask what a run
left behind, and read the project directory only — never the transcript — so a run of this
toolkit, a rerun after a skill change, and a run of another toolkit on the same brief are
scored by one yardstick.

```bash
tools/eval-outcomes.sh list                                   # the tasks
tools/eval-outcomes.sh grade <project_dir> [<task>]           # free: score a project that already ran
tools/eval-outcomes.sh run ec-monolith-legacy                 # paid: stage, run the pipeline, grade
tools/eval-outcomes.sh run greenfield-brief --model opus      # any `claude -p` option follows
```

A task is `outcomes/<task>/`: `task.json` (the input directory, the commands, the thresholds
file), `task.md` (the brief, what each threshold means, the reference run's numbers) and
`expected.json` (`{"<metric>.<field>": {"min" | "max" | "in" | "equals": …}}`). Two ship:
`ec-monolith-legacy` (the sample monolith through `--profile=full`) and `greenfield-brief` (a
one-page brief through `define-requirements` and `--profile=poc`).

The graders are `tools/lib/outcome_graders.py`, one per question a reader of the run would ask:

| metric | reads | answers |
|--------|-------|---------|
| `requirement_coverage` | `work/traceability.json` | the share of `FR-`/`NFR-` nodes some later node cites, the uncovered ones, dangling upstream ids |
| `open_questions` | `work/context.md` § Open Questions | rows by status; `unasked` is what the run never asked |
| `adrs` | `reports/03_design/adr/` | records, validator errors, accepted records naming an approver |
| `report_validity` | `reports/**/*.md` | failures of the two output validators (frontmatter and ELI5, Mermaid) |
| `quality_gate` | `reports/09_verification/quality-gate.json` | verdict, stages by status, unit tests, mutation score, blocking ids |
| `test_results` | `generated/**/test-results/<suite>/*.xml` | pass rate per JUnit suite (`test`, `contractTest`, `acceptanceTest`, …) |
| `phase_completion` | `work/pipeline-progress.json` | phases by status, the profile, warnings |
| `cost` | `work/token-usage.json` | USD total and per phase (the hook records them) |
| `duration` | the registry's stamps | wall clock from the first `started_at` to the last `completed_at`, phase time summed |
| `human_effort` | `work/audit/events.jsonl` | questions asked / answered / deferred, gates rejected, phases revised — the review rounds |

An input that does not exist is **not measured**, never a zero that reads as a result; a
threshold over an unmeasured metric is listed as unmeasured, and the verdict is PASS when no
measured threshold fails. `grade` exits 0 on PASS, 1 on FAIL, 2 on a usage error.

### Comparing with another toolkit (the AI-DLC protocol)

1. **Same brief, same model, same harness.** Give the other toolkit `greenfield-brief/brief.md`
   (or the sample monolith) and ask it for the same deliverables the task's commands ask for:
   requirements, architecture, API contract, review. Run both on the same model and the same
   Claude Code version; record them in the write-up.
2. **Same yardstick.** Grade both output directories with `tools/eval-outcomes.sh grade <dir>
   <task>`. The graders read the shapes this toolkit writes; another toolkit's output is
   comparable on a metric only when it holds that shape — `cost`, `duration` and `test_results`
   need only a token ledger, timestamps and JUnit XML; `requirement_coverage`, `open_questions`
   and `adrs` need the traceability graph, the store and the ADR directory. A metric the other
   run cannot be measured on is **reported as not comparable**, not scored against it.
3. **Say which numbers are comparable.** The write-up carries the scorecards side by side, the
   list of comparable metrics, and what was converted (a toolkit that records questions in
   another shape and was mapped onto the store by hand says so).
4. **Run more than once.** A single run is a sample; the trigger cases taught that (3/3, 3/3,
   then 2/3). Three runs per side before a claim.

Results of `run` land under `evals/results/outcomes-<task>-<timestamp>/` with the scratch project,
the transcript, `scorecard.json` and `scorecard.txt`; the directory is git-ignored.
