# Rules: Naming Frameworks (name-product)

Reference for `/product:name-product`. The house style is the **acronym name**: a short, Latin-letter
name where **every letter is the initial of an English word**, so the name expands into a phrase that
states the product's value.

## The hard constraint

For a name `L1 L2 … Ln`, there must exist English words `W1 W2 … Wn` such that `initial(Wi) == Li`
and `W1 … Wn` reads as a coherent phrase describing the product. Two acceptable readings:

- **Acronym** — the name is pronounced as a word (NEXUS, SCALAR, RADAR). Preferred: most brandable.
- **Initialism** — the name is pronounced letter-by-letter (SDK, ATM). Allowed when short and apt.

A "backronym" is the same object built backward — pick the string first, then fit the words. Both
directions are legitimate here; the deliverable is judged by the *result*, not the path.

## Two construction directions — iterate between them

1. **Forward (initials-first)**: take the product's value words → take their initials → try to
   arrange them into a pronounceable string. Rarely yields a good word on the first pass; use to seed.
2. **Backward (string-first / backronym)**: choose a pronounceable string that fits the domain's
   sound, then fit one English word per letter from the word bank. Best control over both sound and
   meaning. `--seed=<word>` forces this direction on a given base word.

Keep a **word bank**: for every theme keyword from the vision/values/positioning, list strong English
words and index them by initial letter. Expansions are assembled from this bank so every word is
traceable to a real product value, not invented to fill a slot.

## Naming quality criteria (score every candidate)

Adapted from Marty Neumeier's seven tests:

1. **Distinctiveness** — stands out in its category; not a near-copy of a competitor.
2. **Brevity** — short; ≤3 syllables for acronym style. Long expansions are fine; the *name* is short.
3. **Appropriateness** — fits the product, but is not a generic category description. If the expansion
   would describe any product in the space ("Fast Reliable Efficient…"), it fails this test.
4. **Easy spelling & pronunciation** — one obvious reading; no ambiguous vowels or silent letters.
5. **Likability / extendability** — pleasant to say; room to grow beyond the first feature.
6. **Protectability** — *checkable*, not assumed. See below.

Reject any candidate whose per-letter expansion is forced (an off-theme word jammed in to satisfy a
letter) or nonsensical as a phrase — even if the string itself is attractive.

## Never fabricate availability

Do not state that a name, domain, trademark, or handle is available. List the concrete checks as
**Open Questions** for external verification: trademark class(es), `.com` and relevant TLDs,
app-store name, social handles, and collision with known competitors. Availability is cleared by a
human/registry lookup, never by this skill.

## ID convention

Each candidate and the final recommendation gets a `NAM-xxx` ID with an Upstream column citing the
`VIS-`/`POS-` IDs whose value the expansion encodes. Append every `NAM-` node to
`work/traceability.json`.

## Worked shape (illustrative, not a template to copy)

```
Candidate: NEXUS  (acronym, 2 syllables)
  N — Next-generation     (theme: innovation      ← VIS-003)
  E — Extensible          (theme: platform growth ← VIS-005)
  X — eXchange            (theme: interoperability← POS-002)
  U — Unified             (theme: consolidation   ← VIS-001)
  S — System              (theme: category        ← VIS-001)
  Reads as: "a next-generation, extensible exchange that unifies the system."
```

## Sources

- Marty Neumeier — "The Brand Gap" / "Brand" naming criteria
- Alina Wheeler — "Designing Brand Identity" (name types: acronym, descriptive, invented)
