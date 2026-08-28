# Rules: Example Mapping (example-map)

Reference for the step between a feature and its acceptance tests. `define-features` names
**what** the product does (`FEAT-`); `generate-test-specs` writes Gherkin that asserts it. Between
the two sits the conversation that decides what the feature actually means — which business rules
it obeys, which concrete cases prove each rule, and which questions nobody can answer yet. Example
Mapping (Matt Wynne, 2015) is that conversation, structured so that its output is machine-usable:
rules become invariants, examples become scenarios, questions become `OQ-` entries.

## The four cards

| Card | What it is | ID | Becomes |
|------|-----------|----|---------|
| **Story** | The feature under discussion, as its `FEAT-` | `FEAT-` (existing) | The `Feature:` line of the `.feature` file |
| **Rule** | A business rule the story must obey — a constraint, a policy, an acceptance criterion stated as a general truth | `RULE-` | An aggregate invariant or command guard (`design-aggregate`), a `Rule:` block in Gherkin, an acceptance criterion on the backlog Issue |
| **Example** | One concrete case that illustrates exactly one rule — real values, one action, one observable outcome | `EX-` | A `Scenario:` (or `Example:`) under its rule; a concrete example on the invariant it maps to; a unit-test case |
| **Question** | Something the conversation could not settle | `OQ-` (the shared store) | An Open Questions entry, `deferred` or `unasked`, with an owner |

A **Rule with no Example is a rule nobody has tested against a case** — it is the classic way an
acceptance criterion turns out to mean two different things to two people. An **Example that
illustrates no Rule** is either a rule nobody wrote down (write it) or noise (drop it). Both
conditions are checked before the map is written.

## What an example looks like

Concrete, not schematic. `Given a customer with a 20 EUR credit, When they order 25 EUR of goods,
Then the order is rejected with insufficient-credit` — not `Given an order over the credit limit,
Then it is rejected`. The schematic version restates the rule; the concrete one can be wrong, which
is the point: a domain expert can say "no — we allow a 10% overdraft", and a rule the whole room
had agreed on turns out to be false.

Each example records:

- `given` — the state before, with values
- `when` — one action, by one actor
- `then` — the observable outcome: a state, an event, an error by name
- `rule` — the `RULE-` it illustrates (exactly one)
- `kind` — `positive` (the rule holds and the action succeeds) or `negative` (the rule rejects the
  action). Every rule needs at least one of each, or the boundary it draws was never located.

## Where rules come from

Before asking, harvest the candidates the artifacts already contain — asking for what a document
already states is a defect (@rules/open-questions.md §1):

| Source | Yields |
|--------|--------|
| `feature-list.md` — the feature's description, its screen, its MoSCoW rationale | The story, and often the first rule stated as prose |
| `ui-mocks/` — form validation, disabled buttons, error messages on the screen | Rules the UI already enforces (and must not be the only place enforcing) |
| `scope-definition.md`, `constraints.md` | Rules imposed from outside: regulation, policy, a `CON-` |
| `domain-stories/` — the exception scenarios | Negative examples the story already wrote |
| `data-model.md` — cardinalities, required attributes, enumerations | Structural rules (`an order has at least one line`) |
| `journey-maps.md` — pains at the Moment of Truth | The rule a pain implies (`a refund is decided within 48h`) |
| `work/context.md` § Open Questions | Questions already recorded — reuse their `OQ-` rather than minting a second |

## Running the session

The session is per feature, and short — the practice's own heuristic is that a story whose map
needs more than about 25 minutes is too big, and that is a finding: split the feature or record it
as one. Per story:

1. **Present the harvested candidates** — rules and examples the artifacts already imply — and ask
   which hold, which are wrong, and what is missing. `AskUserQuestion` with the candidates as
   options; free text carries the rules the options could not anticipate.
2. **For every rule, ask for the example that breaks it.** The negative case locates the boundary.
   When the user cannot name one, the rule is a preference or a question — reclassify it.
3. **For every example, name its rule.** An example the user gives that illustrates no listed rule
   is a rule they had not stated; add it.
4. **Record the questions.** What could not be settled goes into the shared store with an owner
   and the options that were on the table; the map cites the `OQ-` where the rule would have been.
5. **Size verdict.** Note the rule count and whether the session overran. More than roughly 6–8
   rules on one story is a story that should be split, and the map says so rather than pretending
   the feature is one thing.

Under `--auto`, steps 1–3 run against the artifacts alone: every harvested rule is recorded with
`source` naming the artifact, every rule with no harvestable example gets an `OQ-` entry recorded
`unasked` with the question that would have been asked, and no example is invented.

## Discipline

- **One rule per example, one example per row.** An example that needs two rules to explain is two
  examples.
- **Rules are general; examples are specific.** A rule containing a literal value (`orders over
  100 EUR`) is fine when the value is the policy; an example containing a variable (`an order over
  the limit`) is not an example.
- **Never rewrite the feature.** The map may reveal that a `FEAT-` is two features or is
  mis-scoped; record it as a finding for `define-features` / `adapt-change`, do not edit
  `feature-list.md` from here.
- **Questions are never resolved by guessing.** A rule the room could not agree on is a question,
  not the facilitator's best reading.
- **Rules that are really state transitions are still rules here.** `an order can be cancelled only
  before it ships` is a rule with examples; `design-state-machine` turns it into a matrix cell.
  Record it once here, and let the downstream skill cite the `RULE-`.

## ID convention

`RULE-` for rules, `EX-` for examples, both allocated `max + 1` over `work/traceability.json` per
prefix (@docs/design.md §1.5). Append each as a node: a `RULE-` with `upstream: [FEAT-…]` (plus the
`CON-` / `SCP-` / `ENT-` it derives from), an `EX-` with `upstream: [RULE-…]`. Questions are `OQ-`
entries in `work/context.md` and are not graph nodes.

## Sources

- Matt Wynne — *Introducing Example Mapping* (Cucumber blog, 2015)
- Gojko Adzic — *Specification by Example* (Manning, 2011)
- Cucumber documentation — Example Mapping, the `Rule:` keyword in Gherkin 6+
