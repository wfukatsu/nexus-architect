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

A UX evaluation of the existing UI that a migration decision can rest on, and that a second run on
the same UI would reproduce:

1. **Findings** — each one a defect from the vocabulary of @rules/ux-evaluation.md §5, on the axis
   that owns it, citing a screen, action, input, component, feature or token, a criterion, a
   calibrated severity and a concrete recommendation.
2. **Five axis scores and the UXI** — Heuristics, Accessibility, Efficiency, Consistency,
   Navigation, each bounded by its metrics and by its own findings' severity, combined by the
   formula of §3 into one index and a band that says whether to carry the UI over or redesign it.
3. **An honest method statement** — static expert review from code, plus runtime evidence where it
   was captured; never presented as a usability test with real users.

## Decision Criteria

- **Measure, do not estimate** (@rules/ux-evaluation.md §1). Every count, ratio and contrast value
  comes from `tools/lib/ui_metrics.py`; findings quote it as `metrics.<path>` with its value.
- **One defect, one finding, on the axis that owns it** (§2, §5). A redundant e-mail field is one
  `redundant-input` on E — not also an H8, an H6 and an H4.
- **Scores are fenced twice** (§2): by the metric cap and by the worst severity among the axis's own
  findings. Judgement moves a score inside the fence, never outside it.
- **The parent computes the UXI**, after every axis evaluator has returned.
- **Findings before scores.** The report leads with what costs users most; the index summarizes.
- **Security and architecture are routed, not scored** — view-only authorization, client-only
  validation and view-layer business logic belong to `/architect:investigate-security` and the
  redesign (§1 Out of scope).

## Prerequisites

| Input | Required/Recommended | Source | If missing |
|-------|---------------------|--------|------------|
| `reports/before/{project}/ui-inventory.json` + `ui-design-tokens.json` | Required | `/architect:analyze-ui` | Stop: "run /architect:analyze-ui first" |
| `reports/01_analysis/actors-roles-permissions.md` | Recommended (the pipeline runs `analyze` first) | `/architect:analyze` | Judge per role from `access.roles` alone |
| `reports/02_evaluation/ux-evaluation.json` | Optional | A previous run of this skill | No baseline: every finding is judged fresh |
| `reports/01_ux/personas.md`, `reports/01_ux/journey-maps.md` | Optional (read-only) | `/product:*` | No persona weighting; say so in the method statement |
| A running instance of the UI | Optional | User (`--base-url`) | Static evaluation only |

## Invocation

```
/architect:evaluate-ux [--base-url=<url>] [--storage-state=<path>] [--confirm-versions|--no-confirm-versions] [--auto]
```

| Argument/Flag | Required | Description |
|---------------|----------|-------------|
| `--base-url=<url>` | Optional | A running instance (`http://localhost:8080`). Adds runtime evidence per screen route (Step 4) |
| `--storage-state=<path>` | Optional | A Playwright storage-state file holding an authenticated session. Repeatable; write `<role>=<path>` to capture role-guarded screens with that role's session (`--storage-state=admin=work/ux-evaluation/runtime/admin.json`). Credentials are never asked for or written into a report |
| `--confirm-versions` / `--no-confirm-versions` | Optional | Whether to confirm the resolved Playwright / axe-core versions before installing them for the runtime pass (@rules/dependency-versions.md §4) |
| `--auto` | Optional | Ask nothing: every task is a primary task, carried-forward Open Questions stay open, and runtime capture runs only if `--base-url` is given. `/architect:pipeline` invokes it this way, static only |

## Execution

Write each step's output as soon as it completes; intermediate files go under `work/ux-evaluation/`.

### Step 0: Register the phase

Stamp `evaluate-ux` `in_progress` with `"plugin": "architect"` and `started_at` in
`work/pipeline-progress.json` (@skills/common/progress-registry.md).

### Step 1: Load the model, the baseline and the open questions

1. Locate `reports/before/*/ui-inventory.json` (one per project; `project_name`'s when there are
   several) and validate it:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ui_inventory.py" <project_dir>
   ```
   A non-zero exit stops the skill — an evaluation of an inventory that is not well-formed carries
   its defects into every score.
2. If `reports/02_evaluation/ux-evaluation.json` exists, it is the **baseline**: copy it to
   `work/ux-evaluation/baseline.json`. Evaluators receive it (Step 5) and keep a baseline judgement
   for an unchanged subject unless new evidence contradicts it.
3. Read the actor matrix and, when they exist, the product personas and journeys (read-only; never
   write under `reports/01_ux/`).
4. Read the Open Questions store (`work/context.md` § Open Questions) and pick up every `deferred` /
   `unasked` entry whose impact names this skill or the UX of a screen (@rules/open-questions.md §7).

### Step 2: Compute the metrics

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ui_metrics.py" <project_dir> > work/ux-evaluation/metrics.json
```

This is the `metrics` block of the evaluation, embedded verbatim. Its `caps` are the ceiling of each
axis score.

### Step 3: Primary tasks and carried-forward questions

In one `AskUserQuestion` batch (at most four questions, @rules/open-questions.md §3):

- **Which tasks are primary** — `multiSelect: true`, up to four candidate tasks from
  `metrics.tasks`, ranked by `steps`, then by `required_inputs`; "Other" names different ones. No
  option is marked recommended: which tasks matter most is the user's call. The Efficiency evaluator
  weighs these first.
- **The carried-forward Open Questions** of Step 1, re-asked with their recorded options; answers
  are written back to the store under the same `OQ-` id.

Under `--auto`, every task is primary and the carried-forward questions stay as they are; the method
statement says both.

### Step 4: Runtime evidence (only with `--base-url`)

Skip this step without `--base-url`, and always under `/architect:pipeline`.

1. **Driver.** Prefer the Playwright MCP tools when the session has them; otherwise install
   `playwright` and `@axe-core/playwright` into `work/ux-evaluation/runtime/` with versions looked
   up per @rules/dependency-versions.md (confirmed per `--confirm-versions`) and run a script there.
   With the MCP there is no axe-core: its accessibility snapshot and the checks below take its place,
   and the method statement says so. If its screenshot tool cannot write under the project, take the
   screenshot through its run-code tool (`page.screenshot({ path })`); results that tool returns are
   written to their files by the parent. Pass scripts to it as functions, not as strings — a string
   silently returns nothing.
2. **Sessions.** Clear the browser's cookies first, so no earlier session is reused silently. Load
   each `--storage-state` (the MCP route: `context.addCookies` from the file's cookies). A user
   without a state file creates one once — for example, through the MCP's run-code tool: go to the
   login page, fill it, submit, then `context.storageState({ path:
   "work/ux-evaluation/runtime/<role>.json" })`. State files are bearer credentials: they stay under
   `work/` (git-ignored), never under `reports/`, and are deleted when the run ends.
3. **Reach every screen route** with the session of a role its `access.roles` admits:
   - a route with parameters (`/products/detail?id=`) is reached by following a link to it from a
     page already visited;
   - a screen that needs state (a non-empty cart, a filled order form) may be reached by performing
     **non-destructive, session-only** submits with synthetic test data — adding to a cart, filling a
     form to reach the next step — never real personal data;
   - never perform an action that creates, changes or deletes business records (placing an order,
     saving or deleting a product). A screen reachable only through one is `not-captured` with that
     reason.
4. **Capture per screen** into `reports/02_evaluation/ux-evidence/`:
   - `<UIS>.png` — a full-page screenshot;
   - `<UIS>.a11y.json` — `{screen, url, role, driver, violations: [{criterion, target, detail}],
     accessible_names: [...], contrast_failures: [...], small_targets: [...]}`: the axe-core
     violations with the script driver, or the accessibility snapshot's unnamed controls and images
     with the MCP; plus these two checks, run in the page:

   ```js
   () => { const lum = c => { const [r,g,b] = c.match(/\d+(\.\d+)?/g).slice(0,3).map(v => { v /= 255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); }); return 0.2126*r + 0.7152*g + 0.0722*b; };
     const bg = el => { for (let e = el; e; e = e.parentElement) { const c = getComputedStyle(e).backgroundColor; if (!/rgba\(.*,\s*0\)$|transparent/.test(c)) return c; } return 'rgb(255,255,255)'; };
     const contrast = []; document.querySelectorAll('body *').forEach(el => { if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return;
       const s = getComputedStyle(el); const a = lum(s.color), b = lum(bg(el)); const ratio = (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
       const large = parseFloat(s.fontSize) >= 24 || (parseFloat(s.fontSize) >= 18.66 && parseInt(s.fontWeight) >= 700);
       if (ratio < (large ? 3 : 4.5)) contrast.push({text: el.textContent.trim().slice(0,40), color: s.color, background: bg(el), ratio: Math.round(ratio*100)/100, large}); });
     const targets = [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea')].map(el => { const r = el.getBoundingClientRect(); return {text: (el.innerText || el.value || el.name || '').trim().slice(0,40), width: Math.round(r.width), height: Math.round(r.height)}; }).filter(t => t.width && t.height && (t.width < 24 || t.height < 24));
     return {contrast, targets}; }
   ```
   - for a form with required inputs, one **submitted-empty** capture (`<UIS>.error.png`): submitting
     an invalid form changes nothing, and it is the only way to see WCAG 3.3.1 / 3.3.3 at runtime;
   - with the script driver, for a screen whose outputs a script computes, a **JavaScript-disabled**
     capture (`<UIS>.nojs.png`); with the MCP, record that it could not be taken.
5. Record `runtime: {base_url, tool: "playwright-mcp" | "playwright+axe", captured: [{screen, url,
   role, status: captured|partial|not-captured, screenshot, a11y, reason}]}` in
   `work/ux-evaluation/runtime.json`. `partial` is a screen rendered in a reduced state (the role's
   session saw only part of it); `reason` says what was missed. If nothing could be captured, the
   evaluation is `static`, and the method statement lists the attempts.

### Step 5: Spawn five axis evaluators

In a **single message**, issue five `Task()` calls (`subagent_type: "general-purpose"`, sonnet), one
per axis of @rules/ux-evaluation.md §2. Each prompt carries:

- the paths of the inventory, the token file, `work/ux-evaluation/metrics.json`, the baseline if any,
  and the runtime evidence files if any;
- the output language: "write rationale, titles, descriptions and recommendations in
  <OUTPUT_LANGUAGE>; labels and messages stay verbatim";
- **its cap** — "your score must not exceed <cap>" — and the severity bounds and score bands of §2;
- its **defects** (the rows of the §5 vocabulary whose axis it is, with their criteria and default
  severities) and its **metrics**:

| Axis | Criteria it owns | Metrics it reads first |
|------|------------------|------------------------|
| H | H1, H2, H5, H8, H9 | `per_screen.*.destructive_without_confirmation`, `messages` in the inventory |
| A | WCAG criteria of §4 except 3.3.7 | `accessibility`, `per_screen.*.{unlabeled_inputs, images_without_alt, lang_missing, low_contrast_pairs}`, runtime `a11y` files |
| E | H7, WCAG 3.3.7 | `tasks`, `features`, `input_burden`, `per_screen.*.redundant_inputs`, the primary tasks |
| C | H4 | `consistency` (fragmented clusters, label drift, component duplicates, destination label variants), the token file |
| N | H3, H6, H10 | `navigation`, `per_screen.*.depth`, the transition graph |

- the rules every evaluator follows:
  - cite only criteria your axis owns, and file a defect only on its owning axis — a defect another
    axis owns (a redundant input seen from H) is left to that axis;
  - one finding per defect and subject; the subject is the most specific of action, input,
    component, token, feature, screen — set `location.action` / `location.input` when that is what
    the finding is about, and keep `component` / `feature` to ones that belong to the screen;
  - a severity other than the defect's default carries a one-line `severity_reason`;
  - quote numbers as `metrics.<path>` (value); state none the metrics do not give;
  - `runtime` only when the claim is observable in a capture of that screen, with `runtime_outcome`
    `confirmed` / `refined` / `new`; a static finding the capture contradicts goes into `withdrawn`
    with the evidence;
  - with a baseline: keep its judgement for a subject whose code and evidence did not change;
  - do not file security, authorization, client-only validation or view-layer logic as UX findings;
  - do not compute the UXI.
- this return contract: **write** the result to `work/ux-evaluation/axis-<key>.json` and reply with
  one line (score, finding count by severity):

```json
{ "key": "<H|A|E|C|N>", "score": 3, "rationale": "<2-3 sentences>",
  "findings": [ { "axis": "<key>", "defect": "<§5 vocabulary>", "criterion": "<owned criterion>",
                  "severity": "critical|major|minor|info", "severity_reason": null,
                  "location": {"screen": "UIS-…", "action": null, "input": null, "component": null,
                               "feature": null, "token": null, "source": "<path:line>"},
                  "title": "...", "description": "...", "recommendation": "...",
                  "evidence": "static|runtime", "evidence_ref": null, "runtime_outcome": null } ],
  "withdrawn": [ { "title": "...", "reason": "...", "evidence_ref": "..." } ] }
```

### Step 6: Merge, calibrate, compute

1. Read the five `axis-<key>.json` files. Parse the first JSON object in each (a sub-agent that
   wrapped it in a fence or escaped `<` is still parsed); a missing location key is `null`.
2. **Ownership** — a finding whose defect belongs to another axis moves to that axis, unless the
   owner already has the same defect on the same subject, in which case it is dropped.
3. **Deduplicate** by (defect, subject), keeping the higher severity and merging the evidence;
   `other` findings deduplicate by (criterion, subject).
4. **Calibrate** — a severity that differs from the defect's default without a `severity_reason`
   is reset to the default.
5. Assign ids `UX-001…` ordered by severity (`critical` first), then axis (`H A E C N`), then subject;
   set each axis's `finding_ids`.
6. **Score** — each axis takes the lowest of the evaluator's score, its cap, and its severity bound
   (`critical` → 2, `major` → 3, `minor` → 4); a lowered score's rationale says which fence applied.
7. Compute the index and the band by the formula — the parent's job, not a sub-agent's:
   `UXI = (0.30 × H + 0.25 × A + 0.20 × E + 0.15 × C + 0.10 × N) / 5 × 100`, rounded to 0.1.

### Step 7: Write and validate the evaluation

Write `reports/02_evaluation/ux-evaluation.json`:

```json
{ "schema_version": 1, "generated_at": "<ISO-8601>",
  "inventory": "reports/before/<project>/ui-inventory.json",
  "mode": "static | static+runtime",
  "primary_tasks": ["<task name>"],
  "metrics": { "…": "the ui_metrics.py output, verbatim" },
  "axes": [ { "key": "H", "name": "Heuristic usability", "weight": 0.30, "score": 3,
              "rationale": "…", "finding_ids": ["UX-002"] } ],
  "uxi": 56.0, "band": "needs-improvement",
  "findings": [ { "id": "UX-001", "axis": "A", "defect": "unlabeled-input", "criterion": "WCAG 1.3.1",
                  "severity": "critical", "severity_reason": "required input on the checkout task",
                  "location": { "screen": "UIS-006", "action": null, "input": "phone", "component": null,
                                "feature": null, "token": null,
                                "source": "src/main/webapp/WEB-INF/jsp/order/entry.jsp:62" },
                  "title": "…", "description": "…", "recommendation": "…",
                  "evidence": "static", "evidence_ref": null, "runtime_outcome": null } ],
  "withdrawn": [],
  "routed": [ { "to": "/architect:investigate-security", "what": "…", "source": "…" } ],
  "runtime": { "base_url": null, "tool": null, "captured": [] } }
```

Then run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ux_evaluation.py" <project_dir>
```

It asserts the ten rules of @rules/ux-evaluation.md §6 — among them that every finding's defect and
criterion belong to its axis, that locations exist and agree, that no two findings share a defect and
a subject, that every score stays within its cap and its severity bound, that the UXI is the
formula's value and that the metrics are exactly what `ui_metrics.py` computes now. Fix the
evaluation until it exits 0.

### Step 8: Write the report

`reports/02_evaluation/ux-evaluation.md` — frontmatter per @rules/output-conventions.md
(`phase: "Phase 2: Evaluation"`, `skill: evaluate-ux`, `input_files` naming the inventory, the token
file and the evaluation JSON). No `#` heading — the frontmatter title is the title; sections start at
`##`. Written in the configured `output_language`, with the English section name in parentheses in
another language:

- `## Summary` — UXI and band with its reading (§3), the mode, and an axis table (score, cap,
  severity bound, weight, finding count).
- `## Top Findings` — every `critical` and `major` finding: what, where (screen name and source),
  who it affects (the screen's `access.roles`, and for A the user group — screen-reader, low-vision,
  keyboard users), the fix.
- `## Findings by Axis` — the rest, grouped by axis and defect.
- `## Screen Heatmap` — screens × axes with the number of findings per cell, plus one row for
  findings located only on a token or component.
- `## Key Metrics` — the figures the scores rest on, quoted from the metrics.
- `## Improvement Priorities` — in the terms `/architect:integrate-evaluations` merges:
  short-term (quick wins) and medium-to-long-term (structural improvements).
- `## Method and Limits` — static expert review from code; which screens have runtime evidence, in
  which state and role, and which do not and why; primary tasks and whether personas were available;
  what was routed out of scope; that no user was observed.

### Step 9: Complete the phase

Delete the storage-state files under `work/ux-evaluation/runtime/`. Stamp `evaluate-ux` `completed`
with `outputs` and a one-line `summary` (UXI, band, finding counts by severity).

## Output

| File | Content |
|------|---------|
| `reports/02_evaluation/ux-evaluation.json` | Canonical evaluation: metrics, axis scores, UXI, band, findings, withdrawn and routed items, runtime capture |
| `reports/02_evaluation/ux-evaluation.md` | Summary, top findings, findings by axis, screen heatmap, priorities, method and limits |
| `reports/02_evaluation/ux-evidence/` | Screenshots and accessibility results per screen (runtime mode only) |

## Completion

1. Both outputs are written, and `python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/ux_evaluation.py"
   <project_dir>` exits 0.
2. Every axis scored 3 or lower names its findings; no score exceeds its cap or its severity bound.
3. The method statement says what was static, what was observed at runtime, and what was routed.
4. No storage-state file remains; the phase is stamped `completed`.
5. Report the UXI, the band and the top findings to the user.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze-ui | Upstream — the inventory and token file |
| /architect:analyze | Upstream — the actor matrix |
| /architect:integrate-evaluations | Downstream — the UX track of the unified improvement plan |
| /architect:investigate-security | Receives the routed security facts |
| /architect:evaluate-mmi, /architect:evaluate-ddd | Parallel evaluations |
| /product:design-system | Downstream — consistency findings as the consolidation list |
