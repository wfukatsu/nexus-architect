# ec-monolith — reference DDD document set

What the DDD-relevant skills of nexus-architect produce on `samples/ec-monolith`, committed here
because the real output tree (`reports/`) is git-ignored. The set exists so that "the toolkit
produces a complete DDD document set" can be **seen** rather than inferred from
`docs/ddd-coverage.md`; that table links here, and `reference-set.test.py` (run by
`tools/run-tests.sh`) keeps the two in step and keeps every manifest valid.

| Path | Skill | Technique |
|------|-------|-----------|
| `01_analysis/ubiquitous-language.md` | `/architect:analyze` | Ubiquitous Language |
| `02_spec/examples/example-map-place-order.md` | `/product:example-map` | Example Mapping (`RULE-` / `EX-`) |
| `03_design/bounded-contexts-redesign.md` | `/architect:redesign` | Bounded Context Canvas |
| `03_design/context-map.md` | `/architect:redesign` | Context Mapping |
| `03_design/adr/` | `/architect:redesign`, `/architect:design-microservices` | Architecture Decision Records (`ADR-`) |
| `03_design/aggregates/` | `/architect:design-aggregate` | Aggregates, invariants with examples, commands, events (`AGG-`) |
| `03_design/domain-event-catalog.json` / `.md` | `/architect:design-aggregate`, `/architect:design-microservices` | Published Language / event contracts |
| `03_design/state-machines/` | `/architect:design-state-machine` | State transition model, state × event matrix (`STM-`) |
| `03_design/scalardb-transaction.md` | `/architect:design-scalardb` | Transaction boundaries, Saga, CQRS / ES decisions |
| `04_stories/domain-story-ordering.md` | `/architect:create-domain-story` | Domain Storytelling |

Report bodies are Japanese (`output_language: ja`, as the sample's README is); identifiers,
frontmatter keys and Mermaid node ids are English, per `rules/output-conventions.md`.

## Regenerating

The machine-readable models (`aggregate-manifest.json`, `state-machine-manifest.json`,
`domain-event-catalog.json`, the ADR frontmatter) are the canonical part; the Markdown is their
projection. Regenerate when a ScalarDB version bump or a skill change alters an artifact's shape:

```bash
cd samples/ec-monolith
/architect:init-output ec-monolith            # once; sets options.output_language = ja
/architect:analyze .                          # ubiquitous-language.md
/architect:redesign                           # bounded-contexts-redesign.md, context-map.md, adr/
/architect:create-domain-story --auto         # 04_stories/
/architect:design-aggregate --auto            # aggregates/, domain-event-catalog.json + .md
/architect:design-state-machine --auto        # state-machines/
/architect:design-microservices               # completes adr/ and the catalog's consumer side
/architect:design-scalardb                    # scalardb-transaction.md
/product:example-map --feature=FEAT-001       # 02_spec/examples/
rsync -a --delete reports/ ../expected-reports-candidate/   # review the diff, then replace this directory
```

Then, from the repository root:

```bash
python3 samples/ec-monolith/reference-set.test.py
```

Keep only the files the table above lists — the test rejects a file at a path
`docs/ddd-coverage.md` does not cite.
