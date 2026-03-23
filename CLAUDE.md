# CLAUDE.md

Guidance for Claude Code in the **nexus-architect** repository.

## What This Is

Unified system architecture agent (~35 skills, 9 categories). Covers three workflows:
- **Legacy refactoring**: investigate -> analyze -> evaluate -> redesign -> implement
- **Greenfield design**: requirements -> domain modeling -> ScalarDB design -> infra -> deploy
- **Consulting deliverables**: reports, cost estimates, domain stories

Use `/architect` for interactive selection or `/full-pipeline` for automated execution.

## Skill Categories

| Category | Skills | Purpose |
|----------|--------|---------|
| orchestration | 2 | Workflow selection, pipeline execution |
| investigation | 2 | System survey, security analysis |
| analysis | 2 | Domain analysis, data model |
| evaluation | 3 | MMI scoring, DDD assessment, integration |
| design | 7 | DDD, microservices, ScalarDB, API design |
| implementation | 4 | Design, test specs, codegen |
| review | 7 | 5-perspective parallel review + synthesizer |
| infra | 4 | Kubernetes, security, observability, DR |
| reporting | 3 | Reports, Mermaid, cost estimation |

Full reference: @docs/skill-reference.md

## Pipeline Dependencies

```
investigate -> analyze -> [evaluate-mmi, evaluate-ddd] -> integrate-evaluations
  -> ddd-redesign -> design-microservices -> [design-scalardb, design-api]
  -> implementation -> review -> reporting
```

Each skill declares prerequisites and outputs in its SKILL.md.
Pipeline state tracked in `work/pipeline-progress.json`.
Dependency manifest: @.claude/skills/common/skill-dependencies.yaml

## Output Conventions

All outputs are git-ignored. Structure:

```
reports/                    # Analysis and design documents
├── before/{project}/       # Investigation results
├── 01_analysis/            # System analysis
├── 02_evaluation/          # MMI + DDD scores
├── 03_design/              # Architecture designs
├── 06_implementation/      # Implementation specs
├── 07_test-specs/          # Test specifications
├── 08_infrastructure/      # Infrastructure designs
generated/                  # Generated code per service
work/                       # Pipeline state, intermediate files
```

Naming and frontmatter rules: @.claude/rules/output-conventions.md

## Model Assignment

| Model | Use For | Examples |
|-------|---------|----------|
| **opus** | Architecture decisions, tradeoff analysis, risk | review-risk, ddd-redesign, design-microservices |
| **sonnet** | Standard analysis, document generation, reviews | analyze-system, review-consistency, compile-report |
| **haiku** | Template generation, status checks, simple transforms | init-output, render-mermaid |

## Tool Priority

When exploring target codebases, prefer tools in this order:
1. **Serena MCP** (get_symbols_overview, find_symbol) -- structural understanding
2. **Glob/Grep** -- file discovery and pattern search
3. **Read** -- targeted file reading
4. **Task (sub-agent)** -- large-scale exploration across many files

## Rules & References

| Resource | Location | When to Read |
|----------|----------|--------------|
| ScalarDB coding patterns | @.claude/rules/scalardb-coding-patterns.md | Generating ScalarDB code |
| ScalarDB edition profiles | @.claude/rules/scalardb-edition-profiles.md | Edition selection |
| Evaluation frameworks | @.claude/rules/evaluation-frameworks.md | MMI/DDD scoring |
| Mermaid best practices | @.claude/rules/mermaid-best-practices.md | Creating diagrams |
| Spring Boot integration | @.claude/rules/spring-boot-integration.md | Java code generation |
| Output structure contract | @.claude/templates/output-structure.md | File dependencies |
| Sub-agent patterns | @.claude/skills/common/sub-agent-patterns.md | Spawning sub-agents |

## Conventions

- **Language**: All output documents in Japanese
- **File naming**: kebab-case for all generated files
- **Frontmatter**: Every output file must include YAML frontmatter with `schema_version`
- **Diagrams**: All diagrams use Mermaid syntax (validated by hook)
- **Immediate output**: Each skill step writes its output file upon completion
- **ScalarDB-optional**: When ScalarDB is not used, ScalarDB-specific skills are skipped and review-data-integrity replaces review-scalardb
