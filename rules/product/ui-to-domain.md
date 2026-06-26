# Rules: UI → Feature → Data Derivation (generate-ui-mock, define-features, define-data-model)

Reference for the Phase 3 chain that turns journeys into screens, screens into features, and
features into a data model. The spine is **Domain Storytelling**: the UI is a concrete story from
which features and entities are read out, so each layer traces to the one above it.

## generate-ui-mock — solution exploration, then render

**Mitigate the "first sketch locks the design" risk.** Before drawing, for each *priority job*:

1. Sketch **2–3 solution approaches** in one or two lines each.
2. Compare them briefly (against the job, journey opportunities, positioning).
3. **Select one with an explicit rationale.**

Then enumerate the screens the chosen approach needs, **ordered by the domain story's numbered
activities** (one activity ≈ one screen step), lay out the elements, and render each screen as a
**self-contained HTML file with inline CSS** under `ui-mocks/`. Annotate each screen with the
`STORY-` activity / `JNY-` opportunity / `JOB-` it serves.

- **Wire the story into a clickable flow.** The activity order is the click path: each screen's
  flow-advancing action is a real `<a href>` to the next activity's screen, with a back link to the
  previous screen and a `step N of M` indicator. File names encode the story and step
  (`{STORY}-NN-{slug}.html`) so links are deterministic. A per-story `{STORY}-index.html` lists the
  activity sequence and links to step 1. A missing step is a disabled `TBD` link, never a dead end;
  branches link to their target screens. The reader must be able to **click through the whole story
  end to end**.
- **Fidelity rule**: optimize for *"a reader can tell what function and what data each screen
  involves"*, not visual polish. Low-fi is fine; ambiguous is not.
- Each mock is "a rendering of a selected solution", not a random first draft.

## define-features — Action → Command

Read each screen's interactive elements:

- Each **user action** → a **Command** (a candidate feature). Name it verb-first.
- **Reconcile with scope** — drop anything in Out-of-Scope (`SCP-` Won't); defer Should/Could.
- **Merge duplicates** across screens; assign **MoSCoW** priority.
- Each feature (`FEAT-`) records: name, description, screen(s), and rationale tracing to
  `JOB-`/`JNY-`/`NSM-`.

**Empty-input guard**: if `ui-mocks/` is empty, **stop and report** — never emit an empty feature
list (prevents empty propagation downstream).

## define-data-model — two passes

**Pass 1 — explicit entities (from UI + features):**
- screen/concept name → candidate concept
- form fields → attributes
- action results → state / events
- an aggregate that **receives a Command and emits an Event** → an entity

**Pass 2 — implicit entities (feature × entity CRUD matrix):**
- Build a CRUD matrix (features × entities). Gaps and crossings reveal implicit concepts:
  **many-to-many join, history/versioning, audit log, state-machine/status** entities.
- Add them — and **record the functional-relationship rationale** for each addition.

**Entity criteria**: a concept becomes an entity only if it is **persisted**, has **identity/key**,
and **receives multiple operations**. Avoid over-normalization (don't promote every attribute to an
entity). Produce a **Mermaid ER diagram** of the final model (explicit + implicit).

## ID convention

`FEAT-` for features, `ENT-` for entities; ui-mocks annotate `JNY-`/`JOB-`. Append all to
`work/traceability.json` with Upstream references (`JNY-`/`JOB-`/`SCP-`/`NSM-` → `FEAT-` → `ENT-`).

## Sources

- Stefan Hofer / Henning Schwentner — Domain Storytelling
- Event Storming (Brandolini) — Command → Aggregate → Event derivation
