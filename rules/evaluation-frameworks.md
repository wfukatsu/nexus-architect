# Evaluation Frameworks

## MMI (Modularity Maturity Index) - 4-Axis Qualitative Evaluation

### Evaluation Axes and Weights

| Axis | Weight | Evaluation Criteria |
|------|--------|---------------------|
| Cohesion | 30% | Functional coherence within a module |
| Coupling | 30% | Low degree of inter-module dependencies |
| Independence | 20% | Ability to deploy and test independently |
| Reusability | 20% | Component reusability |

### Scoring (1-5)

| Score | Level | Description |
|-------|-------|-------------|
| 5 | Exemplary | No issues, follows best practices |
| 4 | Good | Only minor improvements needed |
| 3 | Acceptable | Some issues present |
| 2 | Concerning | Significant issues present |
| 1 | Critical | Fundamental problems exist |

### Formula

```
MMI = (0.3 × Cohesion + 0.3 × Coupling + 0.2 × Independence + 0.2 × Reusability) / 5 × 100
```

### Maturity Levels

| MMI | Level | Verdict |
|-----|-------|---------|
| 80-100 | Mature | Ready for microservices migration |
| 60-80 | Moderate | Migration possible after partial refactoring |
| 40-60 | Needs Improvement | Major refactoring required |
| 0-40 | Immature | Fundamental redesign required |

---

## DDD Evaluation - 12 Criteria, 3 Layers

### Strategic Design (30%)

| # | Criterion | Evaluation Criteria |
|---|-----------|---------------------|
| 1 | Ubiquitous Language | Consistency of domain terminology, correspondence with code |
| 2 | Bounded Context | Clarity of context boundaries, separation of responsibilities |
| 3 | Subdomain Classification | Identification of Core/Supporting/Generic and investment allocation |

### Tactical Design (45%)

| # | Criterion | Evaluation Criteria |
|---|-----------|---------------------|
| 4 | Value Objects | Immutability, equality, encapsulation of domain rules |
| 5 | Entities | Identifiers, lifecycle management |
| 6 | Aggregates | Transaction boundaries, consistency guarantees |
| 7 | Repositories | Persistence abstraction, collection semantics |
| 8 | Domain Services | Stateless operations, coordination across multiple aggregates |
| 9 | Domain Events | Event-driven design, state change notifications |

### Architecture (25%)

| # | Criterion | Evaluation Criteria |
|---|-----------|---------------------|
| 10 | Layering | Clarity of layer structure, dependency direction |
| 11 | Dependency Direction | Inward dependencies, application of DIP |
| 12 | Ports & Adapters | Abstraction of connections to external systems |

### DDD Composite Score Calculation

```
DDD Score = (0.30 × Strategic_Avg + 0.45 × Tactical_Avg + 0.25 × Architecture_Avg) / 5 × 100
```
