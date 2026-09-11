---
description: |
  Evaluate the user experience of an existing UI from its inventory: Nielsen's heuristics, WCAG 2.2 accessibility, task efficiency and input burden, consistency, and navigation, as a UX index (UXI) with source-cited findings. Static expert review by default; --base-url adds runtime evidence from the rendered pages.
  /architect:evaluate-ux [--base-url=<url>] [--storage-state=<path>] [--confirm-versions|--no-confirm-versions] [--auto] to invoke.
  Requires analyze-ui output. Optional evaluation phase; can run in parallel with evaluate-mmi and evaluate-ddd.
model: sonnet
user_invocable: true
---

# UX Evaluation

## Desired Outcome

A UX evaluation of the existing UI that a migration decision can rest on:

1. **Findings** — each one citing a screen, component, feature or token, a criterion (a Nielsen
   heuristic or a WCAG 2.2 success criterion), a severity and a concrete recommendation.
2. **Five axis scores and the UXI** — Heuristics, Accessibility, Efficiency, Consistency,
   Navigation, combined by the formula of @rules/ux-evaluation.md §3 into one index and a band that
   says whether to carry the UI over or redesign it.
3. **An honest method statement** — static expert review from code, plus runtime evidence where it
   was captured; never presented as a usability test with real users.

## Decision Criteria

- **Measure, do not estimate** (@rules/ux-evaluation.md §1). Every count, ratio and contrast value
  comes from `tools/lib/ui_metrics.py`. Findings and scores are judgement; numbers are not.
- **The metrics cap the scores** (§2). A sub-agent may score an axis below its cap, never above.
- **The parent computes the UXI**, after every axis evaluator has returned — a sub-agent returns a
  score and findings, never the index.
- **Findings before scores.** The report leads with what costs users most; the index summarizes.
- **Static is the default and is labelled as such.** Runtime evidence confirms, refines or
  withdraws a static finding; it is recorded as `runtime` only when a rendered page backs it.

## Prerequisites

| Input | Required/Recommended | Source | If missing |
|-------|---------------------|--------|------------|
| `reports/before/{project}/ui-inventory.json` + `ui-design-tokens.json` | Required | `/architect:analyze-ui` | Stop: "run /architect:analyze-ui first" |
| `reports/01_analysis/actors-roles-permissions.md` | Recommended | `/architect:analyze` | Judge tasks per role from `access.roles` alone |
| `reports/01_ux/personas.md`, `reports/01_ux/journey-maps.md` | Optional (read-only) | `/product:*` | No persona weighting; say so in the method statement |
| A running instance of the UI | Optional | User (`--base-url`) | Static evaluation only |

## Invocation

```
/architect:evaluate-ux [--base-url=<url>] [--storage-state=<path>] [--confirm-versions|--no-confirm-versions] [--auto]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--base-url=<url>` | Optional | A running instance (`http://localhost:8080`). Adds runtime evidence: a screenshot and an accessibility check per screen route |
| `--storage-state=<path>` | Optional | A Playwright storage-state file with an authenticated session, for screens behind a login. Credentials are never asked for, stored or written into a report |
| `--confirm-versions` / `--no-confirm-versions` | Optional | Whether to confirm the resolved Playwright / axe-core versions before installing them for the runtime pass (@rules/dependency-versions.md §4) |
| `--auto` | Optional | Ask nothing: all features count as primary tasks, and runtime capture is skipped unless `--base-url` is given. `/architect:pipeline` invokes it this way, static only |

## Execution

Write each step's output as soon as it completes; intermediate files go under `work/ux-evaluation/`.

### Step 0: Register the phase

Stamp `evaluate-ux` `in_progress` with `"plugin": "architect"` and `started_at` in
`work/pipeline-progress.json` (@skills/common/progress-registry.md).

### Step 1: Load the model

Locate `reports/before/*/ui-inventory.json` (one per project; pick `project_name`'s when there are
several). Validate it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ui_inventory.py" <project_dir>
```

A non-zero exit stops the skill — an evaluation of an inventory that is not well-formed would carry
its defects into every score. Read the actor matrix and, when they exist, the product personas and
journeys (read-only; never write under `reports/01_ux/`).

### Step 2: Compute the metrics

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ui_metrics.py" <project_dir> > work/ux-evaluation/metrics.json
```

This is the `metrics` block of the evaluation, embedded verbatim. Its `caps` are the ceiling of each
axis score.

### Step 3: Primary tasks

Ask which features are the primary tasks — one `AskUserQuestion` (`multiSelect: true`) whose options
are up to four candidate `UIF-` features, preferring those with the most steps and inputs, with
"Other" for naming different ones (@rules/open-questions.md §3). The Efficiency evaluator weighs
these first. Under `--auto`, every feature is a primary task and the method statement says so.

### Step 4: Runtime evidence (only with `--base-url`)

Skip this step without `--base-url`, and always under `/architect:pipeline`.

1. **Choose the driver.** Prefer the Playwright MCP tools when the session has them
   (`browser_navigate`, `browser_snapshot`, `browser_take_screenshot`, `browser_evaluate`). Otherwise
   install `playwright` and `@axe-core/playwright` into `work/ux-evaluation/runtime/` with versions
   looked up per @rules/dependency-versions.md (confirmed per `--confirm-versions`), and run a script
   there.
2. **Visit every screen route.** Load `--storage-state` when given. For a route with parameters
   (`/products/detail?id=`), follow a link to it from a page already visited; if none exists, record
   the screen as not captured with the reason. Never submit a destructive action.
3. **Capture per screen** — a full-page screenshot to
   `reports/02_evaluation/ux-evidence/<UIS>.png`, and accessibility results to
   `reports/02_evaluation/ux-evidence/<UIS>.a11y.json`: the axe-core violations when the script
   driver ran, or, with the MCP driver, the accessibility snapshot plus this computed-contrast
   check run through `browser_evaluate`:

   ```js
   () => { const lum = c => { const [r,g,b] = c.match(/\d+(\.\d+)?/g).slice(0,3).map(v => { v /= 255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); }); return 0.2126*r + 0.7152*g + 0.0722*b; };
     const bg = el => { for (let e = el; e; e = e.parentElement) { const c = getComputedStyle(e).backgroundColor; if (!/rgba\(.*,\s*0\)$|transparent/.test(c)) return c; } return 'rgb(255,255,255)'; };
     const out = []; document.querySelectorAll('body *').forEach(el => { if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return;
       const s = getComputedStyle(el); const a = lum(s.color), b = lum(bg(el)); const ratio = (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
       const large = parseFloat(s.fontSize) >= 24 || (parseFloat(s.fontSize) >= 18.66 && parseInt(s.fontWeight) >= 700);
       if (ratio < (large ? 3 : 4.5)) out.push({text: el.textContent.trim().slice(0,40), color: s.color, background: bg(el), ratio: Math.round(ratio*100)/100, large}); });
     return out; }
   ```
4. Record `runtime: {base_url, tool: "playwright-mcp" | "playwright+axe", captured: [{screen, url,
   screenshot, a11y, status}]}` in `work/ux-evaluation/runtime.json`.

### Step 5: Spawn five axis evaluators

In a **single message**, issue five `Task()` calls (`subagent_type: "general-purpose"`), one per axis
of @rules/ux-evaluation.md §2. Each prompt carries:

- the inventory and token paths, and the metrics sections its axis rests on;
- **its cap**, stated as "your score must not exceed <cap>";
- the axis's criteria (the heuristics or WCAG criteria of §4 it owns), and the score bands of §2;
- the primary tasks (Efficiency) and the runtime evidence files (all axes, when captured);
- this return contract:

```
Return ONLY this JSON (no markdown fences, no explanation):
{ "key": "<H|A|E|C|N>", "score": <integer 1..cap>, "rationale": "<2-3 sentences>",
  "findings": [ { "axis": "<key>", "criterion": "<H1..H10 | WCAG x.y.z>",
                  "severity": "critical|major|minor|info",
                  "location": {"screen": "UIS-…"|null, "component": "UIC-…"|null,
                               "feature": "UIF-…"|null, "token": "<dotted path>"|null,
                               "source": "<path:line>"|null},
                  "title": "...", "description": "...", "recommendation": "...",
                  "evidence": "static|runtime", "evidence_ref": "<file>"|null } ] }
Do not compute the UXI. Do not write numbers the metrics already give — cite them.
A score of 3 or lower needs at least one finding.
```

Axis focus:

| Axis | Owns | Reads first |
|------|------|-------------|
| H | H1–H10, except what A owns | messages, destructive actions and confirmations, labels, help |
| A | WCAG criteria of §4 | `label_association`, `images`, `lang`, `color_pairs`, runtime a11y files |
| E | H7, WCAG 3.3.7 | features' steps and inputs, required ratios, `redundant_with`, primary tasks |
| C | H4 | fragmented clusters, label drift, component duplicates, the token file |
| N | H3, H6, H10 | depth, orphans, unreachable screens, dead ends, the transition graph |

### Step 6: Merge, score, compute

1. Collect the five results. Deduplicate findings with the same location and criterion, keeping the
   higher severity.
2. Assign ids `UX-001…` ordered by severity (`critical` first), then axis (`H A E C N`), then
   location; set each axis's `finding_ids`.
3. A score above its cap is lowered to the cap and its rationale says "capped by metrics".
4. Compute the index and the band by the formula — this is the parent's job, not a sub-agent's:
   `UXI = (0.30 × H + 0.25 × A + 0.20 × E + 0.15 × C + 0.10 × N) / 5 × 100`, rounded to 0.1.

### Step 7: Write and validate the evaluation

Write `reports/02_evaluation/ux-evaluation.json`:

```json
{ "schema_version": 1, "generated_at": "<ISO-8601>",
  "inventory": "reports/before/<project>/ui-inventory.json",
  "mode": "static | static+runtime",
  "primary_tasks": ["UIF-…"],
  "metrics": { "…": "the ui_metrics.py output, verbatim" },
  "axes": [ { "key": "H", "name": "Heuristic usability", "weight": 0.30, "score": 3,
              "rationale": "…", "finding_ids": ["UX-002"] } ],
  "uxi": 56.0, "band": "needs-improvement",
  "findings": [ { "id": "UX-001", "axis": "A", "criterion": "WCAG 1.3.1", "severity": "major",
                  "location": { "screen": "UIS-003", "component": null, "feature": null,
                                "token": null, "source": "src/main/webapp/WEB-INF/jsp/product/search.jsp:18" },
                  "title": "…", "description": "…", "recommendation": "…",
                  "evidence": "static", "evidence_ref": null } ],
  "runtime": { "base_url": null, "tool": null, "captured": [] } }
```

Then run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ux_evaluation.py" <project_dir>
```

It asserts the nine rules of @rules/ux-evaluation.md §6 — among them that the UXI is the formula's
value, the metrics are exactly what `ui_metrics.py` computes now, and no score exceeds its cap. Fix
the evaluation until it exits 0.

### Step 8: Write the report

`reports/02_evaluation/ux-evaluation.md` — frontmatter per @rules/output-conventions.md
(`phase: "Phase 2: Evaluation"`, `skill: evaluate-ux`, `input_files` naming the inventory, the token
file and the evaluation JSON), headings from `##`, in the configured `output_language`:

- `## Summary` — UXI and band with its reading (§3), the mode, and an axis table (score, cap,
  weight, finding count).
- `## Top Findings` — every `critical` and `major` finding: what, where (screen name and source),
  who it affects, the fix.
- `## Findings by Axis` — the rest, grouped by axis and criterion.
- `## Screen Heatmap` — screens × axes, the number of findings in each cell.
- `## Key Metrics` — the figures the scores rest on, quoted from the metrics.
- `## Improvement Priorities` — short term (fix while porting) and long term (redesign), in the
  terms `/architect:integrate-evaluations` merges.
- `## Method and Limits` — static expert review from code; which screens have runtime evidence and
  which do not, and why; primary tasks and whether personas were available; that no user was
  observed.

### Step 9: Complete the phase

Stamp `evaluate-ux` `completed` with `outputs` and a one-line `summary` (UXI, band, finding counts by
severity).

## Output

| File | Content |
|------|---------|
| `reports/02_evaluation/ux-evaluation.json` | Canonical evaluation: metrics, axis scores, UXI, band, findings, runtime capture |
| `reports/02_evaluation/ux-evaluation.md` | Summary, top findings, findings by axis, screen heatmap, priorities, method and limits |
| `reports/02_evaluation/ux-evidence/` | Screenshots and accessibility results per screen (runtime mode only) |

## Completion

1. Both outputs are written, and `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ux_evaluation.py"
   <project_dir>` exits 0.
2. Every axis scored 3 or lower names its findings; no score exceeds its cap.
3. The method statement says what was static and what was observed at runtime.
4. The phase is stamped `completed`.
5. Report the UXI, the band and the top findings to the user.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze-ui | Upstream — the inventory and token file |
| /architect:analyze | Upstream — the actor matrix |
| /architect:integrate-evaluations | Downstream — the UX track of the unified improvement plan |
| /architect:evaluate-mmi, /architect:evaluate-ddd | Parallel evaluations |
| /product:design-system | Downstream — consistency findings as the consolidation list |
