# Rules: EventStorming (map-domains, create-domain-story)

Reference for the `--mode=event-storming` facilitation that `map-domains` and both
`create-domain-story` skills offer. By default those skills **derive** their model from the
artifacts — features and entities in, contexts out; personas and journeys in, a story out. That is
the right move when the artifacts are trustworthy. EventStorming (Alberto Brandolini, 2013) is the
move for when they are not yet: the boundaries are found by walking the business's *events* with
the people who live them, and the artifacts are written from what the walk revealed.

The mode changes **how the model is found, not what is written**. `map-domains` still emits
`domain-map.md`, `bounded-contexts.md` and `ubiquitous-language.md` with `CTX-` IDs;
`create-domain-story` still emits a domain story with `STORY-` IDs. Two artifacts, two IDs, no
second registry of contexts — the session's own record is an additional file (§4), never a
competing one.

## 1. The notation

EventStorming's sticky notes, and the element in this repository each becomes:

| Note | Definition | Becomes |
|------|-----------|---------|
| **Domain event** (orange) | Something that happened, in the past tense, that the business cares about — `Order Placed`, `Payment Declined` | An event in the ubiquitous language; a state-machine event or transition target; a `Domain event` on the aggregate |
| **Command** (blue) | The intent that caused the event — `Place Order` | An activity in the domain story; a `FEAT-` command; an aggregate command |
| **Actor** (yellow) | Who issued the command — a persona, a role, a system | A story actor; the command's actor on the aggregate and the state machine |
| **Policy** (lilac) | "Whenever *event*, then *command*" — the automation or the rule that reacts | A guard on the state machine; a saga step; a reaction between aggregates (`rules/aggregate-design.md` §4) |
| **Read model** (green) | The information the actor needed to decide on the command | A screen in the UI mocks; a query on the API |
| **External system** (pink) | A system outside the boundary that emits or consumes events | A context-map relationship (ACL, Published Language) or an integration event source |
| **Aggregate** (large yellow) | The thing the command acts on and the event is about | An aggregate candidate for `design-aggregate` |
| **Hotspot** (red / rotated) | A disagreement, an unknown, a "we never decided that" | An `OQ-` entry in the shared store, never a note left on the wall |
| **Pivotal event** (marked) | An event after which the language, the actors or the pace change | A bounded-context boundary candidate |

Events are named **in the past tense**, in the business's words, and one event per note. `Order`
is not an event; `Order Placed` is. `Order Processed` is a smell — it hides several events the
business can tell apart.

## 2. The three formats

| Format | Question it answers | Which skill runs it | Output it feeds |
|--------|--------------------|---------------------|-----------------|
| **Big Picture** | What happens, end to end, across the whole business? | `/product:map-domains --mode=event-storming` | Pivotal events → context boundaries; swimlanes → actors per context; hotspots → `OQ-` |
| **Process Modeling** | For one flow, what exactly happens — who commands, what policy reacts, what is read? | `/product:create-domain-story --mode=event-storming`, `/architect:create-domain-story --mode=event-storming` | Command / actor / policy / read model per activity → the story plus its Process Model section; policies → guard candidates |
| **Software Design** | Which aggregate handles which command and emits which event? | Not a separate mode — `/architect:design-aggregate` takes the Process Modeling output as its command and event candidates | Aggregate roots, commands, events |

The Big Picture session comes first when the domain is unfamiliar; Process Modeling is per flow and
is the format a single story session can run in under an hour. Software Design is what
`design-aggregate` already does once it has events and commands to work from.

## 3. Running the session in a dialogue

There is no wall and no room; the facilitation is a dialogue, one chunk at a time, with the
candidates the artifacts already contain offered first (@rules/open-questions.md §1).

**Big Picture** (`map-domains`):

1. **Seed the timeline.** Harvest event candidates: every `FEAT-` verb as its past-tense event,
   every journey stage's outcome, every domain story's activity result, every status value in the
   data model. Present them as an ordered timeline and ask what is missing, what is wrong, and
   what happens between two events that look far apart.
2. **Walk it forwards and backwards.** Forwards: "after *Order Placed*, what happens next?"
   Backwards from the end: "what had to have happened for *Goods Delivered*?" The backwards walk
   is what finds the events everyone forgot.
3. **Mark the pivotal events.** Ask where the language changes ("here we stop saying *cart* and
   start saying *order*"), where the actors change, and where the pace changes (seconds to days).
   Each pivotal event is a boundary candidate; the events between two pivots are a context
   candidate.
4. **Add actors and external systems** as swimlanes: who issues the command before each event,
   and which events come from or go to a system outside the business.
5. **Capture hotspots as they appear**, with an owner. Do not resolve them by facilitation.
6. **Read the contexts off the timeline** — each run of events between pivots, with its actors,
   its language and its external systems — and hand them to the skill's normal steps
   (classification, context map, consistency hint, ubiquitous language).

**Process Modeling** (`create-domain-story`):

1. **Pick the flow** — the persona × job (product) or the domain (architect), as the skill already
   selects it.
2. **Per step of the flow**, ask the four questions in order: which **event** happened; which
   **command** caused it and which **actor** issued it; what the actor **read** to decide; and
   whether a **policy** reacts to the event ("whenever *Payment Declined*, then *Notify Customer*").
3. **Chase every policy to its command.** A policy that reacts with nothing is an event nobody
   consumes — record it, it is often a missing feature or a missing context.
4. **Capture hotspots as `OQ-`**, and the alternative paths the policies reveal as the story's
   exception scenarios.
5. **Write the story** as the skill already does, plus the Process Model section (§4).

Batch questions (1–4 per `AskUserQuestion` call), and stop a Big Picture walk after two rounds per
timeline segment — a long interrogation is abandoned, and an abandoned walk is worse than a short
one. Under `--auto` the mode is refused: EventStorming with nobody to storm with is derivation
with a different name, so the skill falls back to its default derivation and says so.

## 4. What is written

**`map-domains --mode=event-storming`** writes its three normal artifacts, and in addition
`reports/03_domain/event-timeline.md` — the Big Picture record: the ordered events, the pivotal
events marked, actors and external systems as swimlanes, the hotspots with their `OQ-` IDs, and
the context boundaries read off it. `bounded-contexts.md` cites the pivotal events each `CTX-`
boundary rests on, so the derivation is auditable. The timeline is a **session record**, not a
second source of contexts: `CTX-` IDs live in `bounded-contexts.md` alone.

**`create-domain-story --mode=event-storming`** writes its normal story, with one additional
section:

```markdown
## Process Model

| # | Event | Command | Actor | Read model | Policy |
|---|-------|---------|-------|------------|--------|
| 1 | Order Placed | Place Order | Shopper | Cart summary | whenever Order Placed → Reserve Stock |
| 2 | Stock Reserved | Reserve Stock | Inventory (policy) | Stock levels | whenever Stock Reserved → Authorize Payment |
| 3 | Payment Declined | Authorize Payment | Payment gateway (external) | — | whenever Payment Declined → Release Stock, Notify Shopper |
```

The `#` is the activity number in the main flow; the row is the activity seen as an event. The
Mermaid diagram stays the story's sequence diagram — a timeline of stickies does not render as
anything a reader can use.

## 5. Discipline

- **Events first, always.** Starting from commands or from data reproduces the artifacts; starting
  from what happened is what surfaces the events nobody modeled.
- **Past tense, business words, one event per note.** Every event name goes into the ubiquitous
  language or is proposed for it.
- **Pivotal events are asked, not computed.** The language change is something only the people
  who use the language can hear.
- **A hotspot is never resolved by the facilitator.** It is recorded with an owner and its options,
  and the artifact carries `TBD (OQ-###)` where the answer would go.
- **No new registry.** Contexts are `CTX-` in `bounded-contexts.md`; stories are `STORY-`;
  aggregates are `AGG-`; the session records cite them and mint nothing of their own.
- **Derivation is the fallback, not the failure.** A project whose artifacts are sound gets the
  same `CTX-` set either way; the mode exists for the project whose artifacts are not yet.

## 6. Sources

- Alberto Brandolini — *Introducing EventStorming* (Leanpub), and eventstorming.com
- Vaughn Vernon — *Domain-Driven Design Distilled*, ch. 7 (EventStorming as the entry into
  strategic and tactical design)
