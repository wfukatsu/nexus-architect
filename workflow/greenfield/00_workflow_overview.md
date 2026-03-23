# ScalarDB x Microservices Implementation Planning Workflow

## Overview

This workflow is a guide for systematically developing an implementation plan for a microservices architecture using ScalarDB Cluster, proceeding phase by phase. It takes the deliverables from the investigation phase (`research/` directory) as input and produces an actionable implementation plan as output.

## Overall Flow

```mermaid
flowchart TD
    subgraph Phase1["Phase 1: Requirements & Decisions"]
        W01["01 Requirements Analysis & Applicability Assessment"]
        W02["02 Domain Modeling"]
        W03["03 ScalarDB Scope Decision"]
    end

    subgraph Phase2["Phase 2: Design"]
        W04["04 Data Model Design"]
        W05["05 Transaction Design"]
        W06["06 API & Interface Design"]
    end

    subgraph Phase3["Phase 3: Infrastructure"]
        W07["07 Infrastructure Design"]
        W08["08 Security Design"]
        W09["09 Observability Design"]
        W10["10 Disaster Recovery Design"]
    end

    subgraph Phase4["Phase 4: Execution"]
        W11["11 Implementation Guide"]
        W12["12 Testing Strategy"]
        W13["13 Deployment & Rollout"]
    end

    W01 --> W02 --> W03
    W03 --> W04 --> W05 --> W06
    W06 --> W07
    W07 --> W08
    W07 --> W09
    W07 --> W10
    W08 --> W11
    W09 --> W11
    W10 --> W11
    W11 --> W12 --> W13

    style Phase1 fill:#e8f5e9,stroke:#4caf50
    style Phase2 fill:#e3f2fd,stroke:#2196f3
    style Phase3 fill:#fff3e0,stroke:#ff9800
    style Phase4 fill:#fce4ec,stroke:#e91e63
```

## Phase List

| Phase | Step | File | Input (Research Materials) | Deliverables |
|---------|---------|---------|----------------|--------|
| **Phase 1** | 01 Requirements Analysis & Applicability Assessment | [01_requirements_analysis.md](./01_requirements_analysis.md) | `00_summary`, `02_usecases`, `15_xa` | Requirements list, ScalarDB applicability assessment results |
| | 02 Domain Modeling | [02_domain_modeling.md](./02_domain_modeling.md) | `01_microservice`, `03_logical_data_model` | Bounded context diagram, aggregate design |
| | 03 ScalarDB Scope Decision | [03_scalardb_scope_decision.md](./03_scalardb_scope_decision.md) | `02_usecases`, `07_transaction`, `15_xa` | List of ScalarDB-managed tables |
| **Phase 2** | 04 Data Model Design | [04_data_model_design.md](./04_data_model_design.md) | `03_logical_data_model`, `04_physical_data_model`, `05_db_investigation` | Schema definitions, DB selection results |
| | 05 Transaction Design | [05_transaction_design.md](./05_transaction_design.md) | `07_transaction_model`, `09_batch`, `13_317_deep_dive` | Transaction boundary definitions |
| | 06 API & Interface Design | [06_api_interface_design.md](./06_api_interface_design.md) | `08_transparent_data_access`, `01_microservice` | API specifications, inter-service communication design |
| **Phase 3** | 07 Infrastructure Design | [07_infrastructure_design.md](./07_infrastructure_design.md) | `06_infrastructure`, `13_317_deep_dive` | K8s manifests, Helm values |
| | 08 Security Design | [08_security_design.md](./08_security_design.md) | `10_security` | Security policies, RBAC design |
| | 09 Observability Design | [09_observability_design.md](./09_observability_design.md) | `11_observability` | Dashboard definitions, alert rules |
| | 10 Disaster Recovery Design | [10_disaster_recovery_design.md](./10_disaster_recovery_design.md) | `12_disaster_recovery` | DR plan, backup design |
| **Phase 4** | 11 Implementation Guide | [11_implementation_guide.md](./11_implementation_guide.md) | All design deliverables | Implementation task list, priorities |
| | 12 Testing Strategy | [12_testing_strategy.md](./12_testing_strategy.md) | All design deliverables | Test plan, quality criteria |
| | 13 Deployment & Rollout | [13_deployment_rollout.md](./13_deployment_rollout.md) | `06_infrastructure`, `12_disaster_recovery` | Deployment procedures, canary plan |

## Templates

| Template | File | Purpose |
|------------|---------|------|
| Service Design Document | [templates/service_design_template.md](./templates/service_design_template.md) | Design document template for each microservice |
| Data Model Definition Document | [templates/data_model_template.md](./templates/data_model_template.md) | Table design and schema definition template |
| Review Checklist | [templates/review_checklist.md](./templates/review_checklist.md) | Review items for each phase completion |

## Research Document Mapping

```mermaid
flowchart LR
    subgraph ResearchDocs["Research Documents (research/)"]
        D00["00 Summary Report"]
        D01["01 MSA Architecture"]
        D02["02 Use Cases"]
        D03["03 Logical Data Model"]
        D04["04 Physical Data Model"]
        D05["05 DB Investigation"]
        D06["06 Infrastructure Prerequisites"]
        D07["07 Transaction Model"]
        D08["08 Transparent Data Access"]
        D09["09 Batch Processing"]
        D10["10 Security"]
        D11["11 Observability"]
        D12["12 Disaster Recovery"]
        D13["13 ScalarDB 3.17"]
        D15["15 XA Investigation"]
    end

    subgraph Workflow["Workflow (workflow/)"]
        W01["01 Requirements Analysis"]
        W02["02 Domain"]
        W03["03 Scope"]
        W04["04 Data Model"]
        W05["05 Transaction"]
        W06["06 API Design"]
        W07["07 Infrastructure"]
        W08["08 Security"]
        W09["09 Monitoring"]
        W10["10 DR"]
    end

    D00 --> W01
    D02 --> W01
    D15 --> W01
    D01 --> W02
    D03 --> W02
    D02 --> W03
    D07 --> W03
    D15 --> W03
    D03 --> W04
    D04 --> W04
    D05 --> W04
    D07 --> W05
    D09 --> W05
    D13 --> W05
    D08 --> W06
    D01 --> W06
    D06 --> W07
    D13 --> W07
    D10 --> W08
    D11 --> W09
    D12 --> W10
```

## How to Use

1. **Proceed from Phase 1 in order**: Open each step's workflow file and follow the documented procedures.
2. **Make decisions at decision points**: Use the decision trees and checklists within each step to make and record your decisions.
3. **Use templates**: Copy the templates from `templates/` to create design documents for each service and table.
4. **Review checklists**: Verify quality using the review checklist at the end of each phase.
5. **Check references**: Review the relevant sections of the research materials (`research/` directory) referenced within each step.
