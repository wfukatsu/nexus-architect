---
description: |
  Report the actual token cost the agent recorded while running, straight from the ledger.
  /architect:report-token-cost [--once] [--follow] [--session=ID] [--since=7d] [--breakdown=cost] [--ascii] [--md] [--json] [--lang=ja|en] to invoke.
  Renders work/token-usage.json + work/token-usage.jsonl on the terminal — totals, per-phase
  and per-model cost (in / out / cache-read / cache-write columns), daily timeline, per-session
  cost with session names, and recent events. On a terminal it defaults to an interactive
  two-pane dashboard (select a phase/model/session/day/event above, read its detail — for a
  session, its transcript log — below) that re-checks the ledger every 10s; --follow streams
  events instead, and --session=ID prints one session with its log non-interactively. Reports
  measured actuals only; use /architect:estimate-token-cost for a-priori estimates of a run
  that has not happened yet.
model: haiku
user_invocable: true
disable-model-invocation: true
---

# Token Cost Report (recorded actuals)

## Desired Outcome

The user sees what the agent actually spent in this project — recorded by the
`record_token_usage.py` hook during real runs — as a readable terminal report, without
re-deriving any numbers by hand.

## Inputs

Written automatically by the hook (@rules/token-pricing.md); never edited manually:

| File | Content |
|------|---------|
| `work/token-usage.json` | Aggregated per-phase / per-model billed tokens and USD (`token-usage-v2`) |
| `work/token-usage.jsonl` | Append-only audit log — one record per hook firing (timeline, sessions, events) |
| `skills/common/references/model-pricing.json` | Prices — per-model cost is **recomputed** from this file, so the report tracks pricing updates |

If `work/token-usage.json` does not exist, the project was never initialized
(`/architect:init-output`) or no run has been recorded yet — say so instead of estimating.

## Execution

One script does the whole job: `${CLAUDE_PLUGIN_ROOT}/tools/token-cost-report.sh`.

| Invocation | Command | Effect |
|------------|---------|--------|
| `/architect:report-token-cost` | `tools/token-cost-report.sh --once` | Render the report once (summary, per-phase, per-model, daily timeline, top sessions, recent events) |
| `… --session=ID` | `--session=ID` | Print one session — cost, models, phases, and its transcript log (`ID` may be a prefix; `--log-tail=N` trims the log) |
| `… --since=7d` | `--since=7d` | Limit timeline / sessions / events to a window (`24h`, `7d`, `30d`, `2026-07-01`, `all`) |
| `… --breakdown=cost` | `--breakdown=cost` | Per-model in/out/cache-read/cache-write columns hold cost instead of token counts |
| `… --md` | `--md` | Also write `reports/05_estimate/token-cost-actuals.md` (frontmatter per @rules/output-conventions.md) |
| `… --json` | `--json` | Emit the aggregate as JSON for further processing |
| `… --lang=ja` | `--lang=ja` | Force display language (default: `options.output_language`, else `en`) |
| `… --currency=jpy --fx=155` | same | Show money in JPY at the given rate |
| `… --top=N` | `--top=N` | Rows per table (default 10) |
| `… --ascii` | `--ascii` | Draw the bars, rules and separators with `# . - \| ->` instead of Unicode (`--glyphs=unicode` forces them back on) |

## When the bars look garbled

The report's drawing characters — `█ ░ ─ · → ● Σ` — are almost all East Asian **ambiguous**
width, which breaks two ways: a terminal or font without the glyphs prints replacement boxes,
and a terminal told to render ambiguous characters double-width (the usual setting in Japanese
environments) draws each one twice as wide as the layout counts, so the bars overrun their
column. `--ascii` avoids both — ASCII is unambiguously one column wide and always present.
Non-UTF-8 output is detected and switched to ASCII automatically; the double-width case cannot
be detected, so it is the user's call.

Always pass `--once` when running it yourself: with no mode flag the script starts its live
dashboard on a terminal, which never exits on its own. `--session` and the export flags are
already non-interactive.

**Live modes belong in the user's own terminal, not in an in-session tool call.** When the
user asks to watch cost live, do not run these yourself — tell them to run, prefixing with
`!` inside Claude Code:

- `tools/token-cost-report.sh` — interactive two-pane dashboard: the upper pane lists phases / models / sessions / days / events (`←→`, `Tab`, or `1`–`5` to switch view, `↑↓`/`j k` to select), the lower pane shows that row's detail — for a session, its transcript log including extended thinking. Re-checks the ledger every 10s and re-renders on change (`--watch=SEC` for another interval); `b` toggles the token/cost breakdown, `r` refreshes, `q` quits
- `tools/token-cost-report.sh --follow` — one line per recorded event as it is appended (`--follow=N` seeds with the last N, default 8)

## Session names and logs

The per-session table names each session from its transcript (the summary if the transcript
carries one, else that session's first real user prompt). Sessions whose transcript is no
longer on disk show `-` — report them by id rather than guessing what they were.

The transcript is also what the session log renders (`--session=ID`, or the dashboard's
session view): user prompts, assistant text and thinking, tool calls and results, each with
its timestamp and the assistant turn's cost. Sessions with no transcript on disk show the
cost breakdown only.

## Reporting Back

Relay the rendered output, then add:
1. Where the cost concentrated (top phase / model / day) and the cache-read share — the
   single biggest lever on cost
2. The attribution caveat: per-phase figures mean "billed while this phase was active",
   not "caused by this phase alone"
3. The billing caveat: USD assumes per-token API/Console billing; under a Claude
   subscription the token counts are the real signal and USD is reference-only

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:estimate-token-cost | Sibling — a-priori estimate before/mid-run; consumes the same ledger to calibrate |
| /architect:estimate-cost | Sibling — infrastructure / license / operational cost, not agent cost |
| /architect:init-output | Creates `work/`, which is what enables the recorder hook |
