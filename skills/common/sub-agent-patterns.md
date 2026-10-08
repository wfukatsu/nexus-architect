# Sub-Agent Pattern Library

Eight reusable patterns for sub-agents invoked via the Task tool during skill execution.

## Always pass `model`

A sub-agent does not run on the model of the skill that spawned it, and it does not pick up the
`model` of a skill it invokes: with no `model` on the call it runs on the sub-agent default, which
depends on the user's settings. Measured on Claude Code v2.1.293, sub-agents spawned without a
`model` ran on opus under a haiku session and under a sonnet session alike, while a call that
passed `model: "haiku"` ran on haiku.

So every call names its tier. `{phase_model}` in the patterns below is the calling skill's own
`model` (`opus` | `sonnet` | `haiku`) — a phase's sub-agents run at the phase's tier unless the
skill states a different one and why. `skills/common/subagent-model.test.py` fails a call that
omits it.

## A phase run by an orchestrator is a sub-agent

The same measurement has a second consequence. A skill's own `model` takes effect only when the
user types its command; invoked by another skill in the same turn it runs on the invoking skill's
model. An orchestrator that ran its phases inline would therefore run all of them on its own tier.
`/architect:pipeline` instead starts each phase in a sub-agent with the manifest's `model` on the
call, and that sub-agent invokes the phase's skill (`skills/pipeline/SKILL.md` § Phase Execution).
Measured on v2.1.294: a `sonnet` orchestrator, a phase sub-agent called with `model: "opus"`
invoking a skill whose frontmatter said `haiku`, and that skill's own sub-agent called with
`model: "haiku"` ran on sonnet, opus and haiku respectively.

Sub-agents nest up to three layers below the main conversation, so a phase run this way can still
use the patterns below. It cannot ask the user — `AskUserQuestion` is withheld from every
sub-agent — which is why only the automated orchestrator does this for every phase.

## Pattern 1: Codebase Exploration

Used for surveying the structure of large codebases.

```
Task(subagent_type="Explore",
  model="{phase_model}",
  prompt="Explore the package structure of {target_path},
    and compile a list of major modules and their dependencies in JSON format.",
  description="Codebase structure survey")
```

## Pattern 2: Previous Phase Output Ingestion

Summarize previous phase outputs via a sub-agent to protect the context window.

```
Task(subagent_type="Explore",
  model="{phase_model}",
  prompt="Read the following files and extract the information needed for {current_skill}:
    Required: reports/02_evaluation/mmi-overview.md
    Items to extract: 1. MMI scores by module 2. BC candidates 3. Key improvement areas
    Return the results in Markdown format.",
  description="Previous phase output ingestion")
```

## Pattern 3: Architecture Analysis

Detection and evaluation of microservice patterns.

```
Task(subagent_type="general-purpose",
  model="{phase_model}",
  prompt="Analyze the architecture patterns of the target system:
    - Communication patterns (synchronous/asynchronous)
    - Data ownership patterns
    - Failure propagation paths",
  description="Architecture pattern analysis")
```

## Pattern 4: Code Generation

Code synthesis from design specifications.

```
Task(subagent_type="general-purpose",
  model="{phase_model}",
  prompt="Generate Spring Boot + ScalarDB code based on the following design specification:
    - Entities: {entities}
    - Repositories: {repositories}
    Refer to @rules/scalardb-coding-patterns.md",
  description="ScalarDB code generation")
```

## Pattern 5: Entity Extraction

Automatic identification of domain models.

```
Task(subagent_type="Explore",
  model="{phase_model}",
  prompt="Extract domain entities from {target_path}:
    - Class names, attributes, and relationships
    - Business rules (validations)
    Return the results in table format.",
  description="Entity extraction")
```

## Pattern 6: Comparative Analysis

Cross-cutting comparison of multiple documents.

```
Task(subagent_type="general-purpose",
  model="{phase_model}",
  prompt="Perform a comparative analysis of the following two design proposals:
    - Proposal A: {file_a}
    - Proposal B: {file_b}
    Comparison axes: performance, maintainability, migration cost, risk",
  description="Design proposal comparison")
```

## Pattern 7: Multi-Document Integration

Consolidate multiple analysis results into a single report.

```
Task(subagent_type="general-purpose",
  model="{phase_model}",
  prompt="Consolidate the following analysis results into an integrated report:
    {file_list}
    Eliminate duplicates and organize by priority.",
  description="Analysis result integration")
```

## Pattern 8: Constraint Satisfaction Verification

Feasibility verification of a design.

```
Task(subagent_type="general-purpose",
  model="{phase_model}",
  prompt="Verify whether the following design satisfies the constraint conditions:
    Design: {design_file}
    Constraints: 2PC max 3 services, OCC conflict rate below 5%, latency under 100ms
    Report any violations and suggest alternatives.",
  description="Constraint satisfaction verification")
```
