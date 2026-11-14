# Learned Rules — the learning loop

A finding the review perspectives raise on one project is raised again on the next unless
something carries it forward. Within backlog delivery that something is
`reports/backlog/shared-context/review-knowledge.md`; across the design pipeline, and across
projects, it is the learned-rules store this rule describes. Read it when a review finds
something that recurs, or when a design skill starts.

## 1. The store

`work/learned-rules.json` — or, when `options.learned_rules_path` in `work/pipeline-progress.json`
names a file, that file, shared by every project that names it (a consultancy accumulates each
lesson once). `tools/lib/learned_rules.py` is the only writer; `work/learned-rules.md` is its
rendered view. Every write is additive: a rule is never deleted, only `rejected`.

| Field | Meaning |
|-------|---------|
| `id` | `LR-###`, allocated `max + 1` over the store |
| `status` | `proposed` → `accepted` \| `rejected`. Only an accepted rule is read by a design skill |
| `scope` | The phases (skill names) the rule applies to — `design-api`, `design-scalardb`, … |
| `category` | `naming` / `api-contract` / `data-model` / `transaction` / `error-handling` / `nfr` / `security` / `testing` / `operations` / `architecture` / `process` — the same vocabulary as `review-knowledge.md` |
| `rule` | The guardrail, imperative, one sentence. The deduplication key: the same sentence proposed again is an occurrence, not a second rule |
| `anti_pattern`, `rationale` | What it prevents and why — optional, but a rule without a rationale is hard to accept |
| `origin` | One entry per proposal: the finding id, the project, the time |
| `occurrences` | How many times it was proposed — what makes a rule worth accepting |
| `proposed_by`, `decided_by`, `decided_at`, `decision_reason` | Who proposed (a skill), who decided (a person), when and why |

## 2. Proposing — `review-synthesizer`

After the verdict (its Step 3b), the synthesizer proposes a rule from each finding that
**recurs**: raised by two or more perspectives, matching a rule already on file, or P0/P1. One
command per finding, after the synthesis is written:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/learned_rules.py" <project_dir> propose rule="<the guardrail, imperative>" scope=<phase,phase> category=<category> anti_pattern="<what it prevents>" rationale="<why>" finding=<SYN-id>
```

The tool deduplicates on the sentence, so phrase the rule as a rule, not as the finding ("every
non-2xx response is a registered problem type", not "confirmOrder returns an ad-hoc 500"). A
proposal is a `RULE_PROPOSED` audit event whose `phase` is the proposing skill (`phase=`,
`review-synthesizer` by default). The one switch is `options.learnings`: when it is `false`
(`--no-learnings` on the orchestrators) the synthesizer proposes nothing and says so; an automated
run proposes as an interactive one does — what differs is who decides (§3).

`review-issue` keeps its own catalogue for the backlog (its Step 3b); a lesson there that
generalizes beyond this backlog — a contract, a data-model or a transaction rule any project
would want — is proposed here as well, with the Issue as `finding=` and `phase=review-issue`.
Writes hold a lock on `<store>.lock`, so parallel proposers — sub-agents, or two projects on one
shared store — never share an id or lose a rule.

## 3. Deciding — a person

A proposed rule is a question for the architect (or the role its category belongs to,
@docs/decision-roles.md). `/architect:start` decides them at two moments — **at the start of a
run**, before the first design phase, for every rule the store holds `proposed` (what an earlier
`/architect:pipeline` run or another project on a shared store left behind), and **after its own
`review-synthesizer` phase**, for the ids that phase returned — with the phase's other questions:
one `AskUserQuestion` per rule, accept or reject, "Other" carrying a rewording; and records each:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/learned_rules.py" <project_dir> list status=proposed format=json
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/learned_rules.py" <project_dir> decide LR-003 accepted by="<name>" reason="<why>"
```

A decision is a `RULE_ACCEPTED` / `RULE_REJECTED` audit event. `/architect:pipeline` has nobody
to ask: its proposals stay `proposed`, its final message lists them, and the next
`/architect:start` on the project (or on any project sharing the store) decides them before it
designs anything — that is what closes the loop for automated runs. A rejected rule proposed
again becomes a new id — the rejection is a decision about that sentence, not a ban on the topic.

## 4. Reading — the design skills

`redesign`, `design-aggregate`, `design-microservices`, `design-api`, `design-scalardb` /
`design-data-layer` and `design-implementation` read the accepted rules for their phase before
deciding anything (each names the store in its Prerequisites):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/lib/learned_rules.py" <project_dir> list scope=<this phase>
```

Each applies every rule listed and **cites its `LR-` in the decision it shaped** (an ADR's
`evidence`, a design document's rationale), so a reader can see which rules were in force. A rule
the skill cannot apply — it contradicts a requirement, or the project's stack has no such thing —
is named in the output with the reason, never silently dropped, and that is a signal to the
person who accepted it.

## 5. What is not a learned rule

A fact about a vendor product belongs in the knowledge bundle (@rules/okf-knowledge-bundle.md),
not here. A decision about this project is an ADR. A rule is what would be true of the next
project too.
