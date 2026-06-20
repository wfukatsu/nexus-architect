# Rules: Vision Frameworks (define-vision)

Reference for `/product:define-vision`. Apply both frameworks; the Vision Board sets the core,
the PR-FAQ pressure-tests it.

## Product Vision Board (Roman Pichler) — 5 elements

1. **Vision** — the ultimate purpose; the change the product creates in the world. One inspiring,
   memorable sentence. Big and ambitious.
2. **Target Group** — who the users and customers are. **Segment it — never "everyone".**
3. **Needs** — the problem solved or benefit delivered; why users would switch.
4. **Product** — the few standout features / key differentiators (not a full feature list).
5. **Business Goals** — how the product benefits the company (revenue, growth, retention).

A good vision is: ambitious, inspiring, shared, concise/memorable.

**Mission vs Vision vs Values**: Vision = the destination (the change in the world). Mission =
how it is pursued (what the product does, for whom, day to day). Values = the decision principles
the team holds when trade-offs arise. Derive Mission and Values from the filled Vision Board.

## Working Backwards — PR-FAQ (Amazon)

Write as if the product already shipped. Truth-seeking, not selling.

**Press release** (≈1 page):
- Heading — product name
- Subheading — target customer + core benefit (one line)
- Summary paragraph — what it is, who it's for, the headline benefit
- Problem paragraph — the customer pain, **in the customer's words**
- Solution paragraph(s) — how the product solves it; the **differentiation**
- Quotes & CTA — an exec quote + a customer quote, and how to get started

**FAQ** (two tiers):
- **External FAQ** — pricing, functionality, how to buy, support
- **Internal FAQ** — market size (TAM/SAM/SOM), competitive landscape, unit economics, operational
  challenges, risks, and **Go/No-Go criteria**

> The Go/No-Go criteria are load-bearing: they are enforced later by
> `/product:validate-assumptions`. Make them concrete and falsifiable (e.g. "Go only if X% of
> interviewed target users rank this problem in their top 3").

## ID convention

Each board element and each major PR-FAQ claim gets a `VIS-xxx` ID with an Upstream column
(empty for the vision root). Append every `VIS-` node to `work/traceability.json`.

## Sources

- Roman Pichler — "The Product Vision Board" / "Product Vision Board Checklist"
- Amazon — "Working Backwards" PR-FAQ process (workingbackwards.com)
