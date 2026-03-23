# Sub-Agent Pattern Library

Eight reusable patterns for sub-agents invoked via the Task tool during skill execution.

## Pattern 1: Codebase Exploration

Used for surveying the structure of large codebases.

```
Task(subagent_type="Explore",
  prompt="Explore the package structure of {target_path},
    and compile a list of major modules and their dependencies in JSON format.",
  description="Codebase structure survey")
```

## Pattern 2: Previous Phase Output Ingestion

Summarize previous phase outputs via a sub-agent to protect the context window.

```
Task(subagent_type="Explore",
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
  prompt="Consolidate the following analysis results into an integrated report:
    {file_list}
    Eliminate duplicates and organize by priority.",
  description="Analysis result integration")
```

## Pattern 8: Constraint Satisfaction Verification

Feasibility verification of a design.

```
Task(subagent_type="general-purpose",
  prompt="Verify whether the following design satisfies the constraint conditions:
    Design: {design_file}
    Constraints: 2PC max 3 services, OCC conflict rate below 5%, latency under 100ms
    Report any violations and suggest alternatives.",
  description="Constraint satisfaction verification")
```
