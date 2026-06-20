# Rules: Personas & Jobs-to-be-Done (generate-persona)

Reference for `/product:generate-persona`. Build personas around **Jobs-to-be-Done**, not around
demographics. An AI-generated persona is a **scaffold** (a proto-persona) to be promoted to a
research-based persona as real evidence arrives — it is not a substitute for talking to users.

## Jobs-to-be-Done (JTBD)

People "hire" a product to make progress in a situation. Capture the job, not the user attribute.

- **Job Story format**: *When [situation], I want to [motivation], so I can [expected outcome].*
- Cover the three dimensions of a job: **functional** (the task), **emotional** (how they want to
  feel), **social** (how they want to be perceived).
- A job is solution-agnostic and stable; features are not. Anchor personas to jobs so they survive
  product pivots.

Each job story gets a `JOB-xxx` ID.

## Persona card

For each persona, record:

- **Name / archetype** and a one-line summary (a role, never "everyone")
- **Context & behaviors** — relevant situation, not vanity demographics
- **Jobs (JTBD)** — the `JOB-` ids this persona pursues
- **Pains** — obstacles, frictions, risks in getting the job done
- **Gains** — desired outcomes and benefits
- **Verbatim quote** — in the user's own words (from research, or marked **[proto / unvalidated]**)

Each persona gets a `PER-xxx` ID.

## Proto vs research-based (be honest about confidence)

- **Proto-persona** — assembled from assumptions/desk research. Mark every unvalidated claim
  **[proto]**. AI is good at the scaffold but weak on *emotional validity* — do not present
  invented feelings or quotes as fact.
- **Research-based** — backed by interviews/data (`--input`). Promote proto → research-based by
  replacing assumptions with cited evidence.

**Never fabricate demographics or quotes.** Unknowns are `TBD` in Open Questions. Prefer research
data over generation whenever it exists.

## Prioritize

Identify the **primary persona** (the one the product is optimized for) vs secondary/served/
anti-personas. Downstream skills (`map-journey`, `define-features`) focus on the primary first.

## ID convention

`JOB-` for job stories, `PER-` for persona cards; append to `work/traceability.json` with Upstream
`VIS-` (target group) references.

## Sources

- Clayton Christensen / Tony Ulwick — Jobs-to-be-Done
- Alan Cooper — personas (primary/secondary/served/negative)
- Roman Pichler / Jeff Gothelf — proto-personas
