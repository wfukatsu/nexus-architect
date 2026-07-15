# Token Pricing & Usage Tracking

How the toolkit prices LLM token usage and records actual consumption per phase. Read
this when estimating the cost of running the pipeline (`/architect:estimate-token-cost`)
or interpreting the recorded ledger.

## Single source of truth for prices

`skills/common/references/model-pricing.json` holds all prices (USD per 1M tokens),
cache multipliers, server-tool pricing, and a-priori estimation heuristics. **Update
`version` and the family prices there when Anthropic pricing changes** — both the
recorder hook and the estimation skill read this one file, so there is nothing else to
keep in sync.

- Cache economics (relative to a model's input price): cache **read** ≈ 0.1×, 5-minute
  cache **write** ≈ 1.25×, 1-hour cache **write** ≈ 2.0×.
- **Introductory pricing** is honored automatically: a family with
  `intro_input`/`intro_output`/`intro_until` is priced at the intro rate while
  today ≤ `intro_until` (e.g. Sonnet 5 at $2/$10 through 2026-08-31).
- Web search requests are priced per 1k requests (`server_tools.web_search_per_1k`).

## Automatic per-phase recording

The `record_token_usage.py` hook (wired in `hooks/hooks.json` as `PostToolUse` on
`Write|Edit|MultiEdit|Task|Agent`, plus `Stop` and `SubagentStop`) runs during
execution:

1. **Activates only inside an initialized project** (`work/pipeline-progress.json` must
   exist — created by `/architect:init-output`). It stays inert everywhere else.
2. Reads the session transcript **incrementally** (byte-offset per transcript file) and
   sums billed tokens per model from each assistant turn (`input`, `output`,
   `cache_read`, the 5m/1h `cache_creation` split, and `web_search_requests`).
   Message ids are deduped **across chunk boundaries** (a single API response spans
   multiple transcript lines sharing one `message.id`). Subagent turns land in the same
   transcript and are captured.
3. **Attribution** (in priority order):
   1. Phases marked `in_progress` in `pipeline-progress.json` (parallel phases joined
      with `+`) — the pipeline-orchestrated case.
   2. Phases that **newly transitioned to `completed`** since the last checkpoint —
      they receive the pending bucket plus the current delta. This covers the standard
      single-skill flow, where skills only write `"completed"` at the end: tokens spent
      while the phase was still `pending` accumulate in the pending bucket and are
      swept into the phase the moment it completes.
   3. Otherwise the delta accumulates in a **pending bucket**; if a turn ends
      (`Stop`/`SubagentStop`) with still nothing to attribute to, pending is flushed to
      the permanent `_unassigned` bucket (non-pipeline work in the same repo).
   On the very first firing, phases already completed before tracking started are
   baselined and never credited retroactively.
4. Maintains two artifacts (both git-ignored, under `work/`):
   - `work/token-usage.json` — aggregated per-phase / per-model tokens + USD cost.
   - `work/token-usage.jsonl` — append-only audit log (one record per firing that
     observed usage), including what was attributed where and why.

Concurrent firings (parallel subagents) are serialized with an `flock` lockfile
(`work/.token-usage.lock`); offsets only advance under the lock, so a firing that loses
the lock race simply leaves the bytes for the next firing.

The hook is **fail-safe**: any error exits 0 without disturbing the session. Set
`NEXUS_TOKEN_DEBUG=1` to append tracebacks to `work/token-usage.err`. It requires
`python3` on PATH — if missing, recording is **silently disabled** (nothing else
breaks); check for `work/token-usage.json` after a run to confirm recording worked.

### Attribution semantics (caveat)

Per-phase figures mean "**billed while this phase was active**", not "caused by this
phase alone": later phases re-transmit earlier context as input (mitigated by cache
reads at 0.1×), and setup/coordination tokens between phases are swept into the next
completed phase. Treat per-phase numbers as calibration data for estimates, not as an
exact causal decomposition.

### `work/token-usage.json` schema (`token-usage-v2`)

```json
{
  "$schema": "token-usage-v2",
  "project_name": "demo",
  "pricing_version": "2026-06-24",
  "phases": {
    "investigate": {
      "by_model": { "sonnet": { "input_tokens": 0, "output_tokens": 0,
        "cache_read_input_tokens": 0, "cache_creation_5m": 0, "cache_creation_1h": 0,
        "web_search_requests": 0 } },
      "usage": { "…": "sum over by_model" },
      "cost_usd": 0.0
    },
    "_unassigned": { "…": "non-pipeline work recorded in the same repo" }
  },
  "pending_usage": { "…": "not yet attributed to any phase" },
  "pending_cost_usd": 0.0,
  "totals": { "…": "phases + pending" },
  "total_cost_usd": 0.0,
  "_pending": { "by_model": {} },
  "_progress": { "completed_seen": ["…"] },
  "_transcripts": { "<path>": { "offset": 0, "recent_ids": ["…"] } }
}
```

Keys starting with `_` are internal bookkeeping; everything else is the reportable
ledger. Parallel phases appear as joined keys (e.g.
`review-consistency+review-risk`).

## Estimation methodology (a-priori)

When no actuals exist yet, `/architect:estimate-token-cost` estimates from lines of code
using `estimation_heuristics` in the pricing file:

```
raw_code_tokens  = LOC × tokens_per_loc            (+ design-doc tokens)
unique_ingested  = raw_code_tokens × code_ingestion_ratio
effective_input  = unique_ingested × effective_input_multiplier   (cache-adjusted)
output_tokens    ≈ output_per_phase_tokens × phase_count
cost             = Σ per-phase (effective_input, output) priced by phase_model_tier
```

**These heuristics are uncalibrated defaults** — expect wide bands until real runs
populate `work/token-usage.json`. Prefer measured actuals: once the ledger has data,
calibrate the estimate against it (extrapolate remaining phases for a partial run;
report actuals directly for a complete run), and state clearly which figures are
measured vs. modeled. After a few real runs, consider updating the heuristic values in
`model-pricing.json` from observed ratios.

## Billing model caveat

The USD figures assume **per-token API/Console billing**. Under a Claude subscription
(Pro/Max), Claude Code usage draws down usage limits rather than per-token charges — in
that case treat token counts as the primary output and USD as reference-only.
