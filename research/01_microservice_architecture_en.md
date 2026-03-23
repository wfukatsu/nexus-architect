# Microservice Architecture Research

## 1. Requirements Each Microservice Must Fulfill

### Fundamental Principles

| Principle | Description |
|-----------|-------------|
| **Single Responsibility** | Each service handles only one clearly defined responsibility within the business domain |
| **Autonomy** | Independently deployable, not dependent on the operational status of other services |
| **Loose Coupling** | Communicates only through clearly defined APIs; changes to internal implementation do not affect other services |
| **High Cohesion** | Related functionality is consolidated within the same service; data and logic are co-located |
| **Independent Deployment** | Can be released independently without redeploying other services |
| **Technology Diversity** | Each service can choose the optimal technology stack |
| **Fault Isolation** | A failure in one service does not cascade to the entire system |
| **Observability** | Internal state of a service can be understood from the outside |
| **Security** | Inter-service authentication and authorization based on zero-trust principles |

### Service Boundary Design Principles

- **DDD (Domain-Driven Design)**: Bounded Contexts are the most important guideline for service boundary design
- **Decomposition by Business Capability**: Decompose by business function units rather than technical layers
- **Context Mapping**: Clearly define relationships between boundaries (Upstream/Downstream, Customer/Supplier, Anti-Corruption Layer, etc.)
- **Event Storming**: Discover service boundaries through domain-event-centric workshops

#### Context Mapping When Using ScalarDB 2PC

- **Coordinator Service** = Upstream (manages the transaction lifecycle)
- **Participant Service** = Downstream (follows the Coordinator's instructions)
- **Anti-Corruption Layer**: Participant services provide an ACL for 2PC participation, preventing Coordinator-specific protocols from penetrating domain logic
- **Data Ownership**: Each data entity has a single owner service (Database per Service pattern)

## 2. Functional and Non-Functional Requirements for Development

### CI/CD Pipeline

The principle is that each service has its own independent pipeline.

```mermaid
flowchart LR
    A["Commit"] --> B["Build"] --> C["Unit Test"] --> D["Static Analysis"] --> E["Container Build"]
    E --> F["Integration Test"] --> G["Security Scan"] --> H["Staging Deploy"]
    H --> I["E2E Test"] --> J["Approval Gate"] --> K["Production Deploy"]
```

**Repository Strategy**:
- Monorepo (Bazel, Nx, Turborepo): Easier dependency management, atomic changes possible
- Polyrepo: Complete independence per service

**Tool Examples**: GitHub Actions, GitLab CI/CD, Jenkins, Argo Workflows, Tekton

### Testing Strategy

| Test Type | Purpose | Tool Examples | Execution Frequency |
|-----------|---------|---------------|---------------------|
| **Unit Test** | Verify behavior of individual classes/functions | JUnit, pytest, Jest | Per commit |
| **Integration Test** | Verify integration with DB, MQ, etc. | Testcontainers, Spring Boot Test | Per commit |
| **Contract Test** | Verify inter-service API compatibility | Pact, Spring Cloud Contract | Per commit |
| **E2E Test** | Verify entire user scenarios | Selenium, Cypress, Playwright | Before deployment |
| **Chaos Test** | Verify resilience during failures | Chaos Monkey, Litmus | Periodic |

**Contract Testing** is one of the most critical tests in microservices. Consumer-Driven Contract Testing allows the consumer side to define and verify the contracts expected from the provider.

### Versioning

| Method | Example | Advantages | Disadvantages |
|--------|---------|------------|---------------|
| URL Path | `/api/v1/orders` | Intuitive, easy to cache | URL changes |
| Header | `Accept: application/vnd.api.v2+json` | Stable URL | Low visibility |
| Query Parameter | `/api/orders?version=2` | Simple implementation | Difficult to cache |

- Adopt SemVer (MAJOR.MINOR.PATCH)
- Maintain backward compatibility with the Tolerant Reader pattern

## 3. Functional and Non-Functional Requirements for Deployment

### Containerization

- **Docker**: Containers are the industry standard for packaging and distribution. Minimize images with multi-stage builds, run as non-root user, security scanning mandatory
- **Kubernetes**: De facto standard for container orchestration. Auto-scaling with HPA/VPA

**Kubernetes Ecosystem**:

| Component | Role | Representative Tools |
|-----------|------|---------------------|
| Service Mesh | Inter-service communication management | Istio, Linkerd |
| Ingress | External traffic control | NGINX Ingress, Traefik, Envoy Gateway |
| Secret Management | Sensitive information management | Vault, Sealed Secrets |
| Package Management | Application packaging | Helm |
| GitOps | Declarative deployment | Argo CD, Flux |

### Deployment Strategies

| Strategy | Description | Advantages | Disadvantages |
|----------|-------------|------------|---------------|
| **Blue-Green** | Switch between 2 environments | Zero downtime, instant rollback | Requires resources for 2 environments |
| **Canary Release** | Gradual traffic migration (5%->100%) | Minimized risk | Complex implementation |
| **Rolling Update** | Gradual Pod replacement | Kubernetes default | Slow rollback |
| **A/B Testing** | User attribute-based | Measurable effectiveness | Complex design |

### Infrastructure as Code

| Tool | Use Case | Features |
|------|----------|----------|
| **Terraform** | General cloud infrastructure | Declarative, multi-cloud support |
| **Pulumi** | Cloud infrastructure | Written in general-purpose programming languages |
| **Helm** | Kubernetes applications | Template-based |
| **Kustomize** | K8s manifest management | Patch-based |

## 4. Functional and Non-Functional Requirements for Operations

### Health Checks (Kubernetes)

| Type | Purpose | Behavior on Failure |
|------|---------|---------------------|
| **Startup Probe** | Confirm startup completion | Disables other probes |
| **Liveness Probe** | Confirm process is alive | Restarts container |
| **Readiness Probe** | Determine request acceptance | Removed from Service |

### Circuit Breaker

State Transition: CLOSED (normal) -> OPEN (blocked) -> HALF-OPEN (trial) -> CLOSED/OPEN

Tool Examples: Resilience4j

### Scaling Strategies

- **Horizontal Scaling**: Increase/decrease Pod count (HPA), optimal for stateless services
- **Vertical Scaling**: Increase/decrease resources (VPA), applicable to stateful services
- **KEDA**: Kubernetes Event-Driven Autoscaling, event-driven scaling

Prioritize horizontal scaling as the default and design services to be stateless.

### Failure Recovery Patterns

| Pattern | Description |
|---------|-------------|
| Retry | Retry with exponential backoff |
| Timeout | Set maximum response time |
| Bulkhead | Isolate resource pools |
| Fallback | Alternative processing (cache, default values) |
| Idempotency | Multiple executions of the same operation yield the same result |

#### Impact Analysis During ScalarDB Cluster Failure

- **Shared-Cluster Failure**: Transaction processing for all services stops. Designing a read-only fallback mode is recommended
- **Network Partition**: ScalarDB's OCC aborts transactions during network partitions. Services should ensure reads from their local cache
- **ScalarDB Cluster Version Upgrade**: Transaction processing continues during rolling updates, but verify compatibility between old and new versions in advance

**Disaster Recovery Strategies**:

| Strategy | RTO | RPO | Cost |
|----------|-----|-----|------|
| Backup & Restore | Hours | Hours | Low |
| Pilot Light | Tens of minutes | Minutes | Medium |
| Warm Standby | Minutes | Seconds to minutes | High |
| Multi-Region Active-Active | Near zero | Near zero | Very high |

## 5. Functional and Non-Functional Requirements for Monitoring

### Three Pillars of Observability

1. **Metrics**: Numerical time-series data (Prometheus + Grafana)
2. **Logs**: Structured/unstructured text events (ELK, Loki)
3. **Traces**: Tracking request flows (OpenTelemetry, Jaeger)

### Metrics (RED/USE Methods)

**RED Method (Service Level)**: Rate, Errors, Duration
**USE Method (Resource Level)**: Utilization, Saturation, Errors

**SLI/SLO/SLA**:
- SLI: Measurement indicator (e.g., p99 latency = 200ms)
- SLO: Internal target (e.g., maintain p99 < 300ms at 99.9%)
- SLA: Customer contract (e.g., 99.95% monthly uptime)

### Distributed Tracing

| Tool | Features |
|------|----------|
| **OpenTelemetry** | Vendor-neutral telemetry standard (CNCF), industry convergence point |
| **Jaeger** | Originated at Uber, CNCF graduated, specialized in distributed tracing |
| **Grafana Tempo** | Integration with Grafana ecosystem |

### Log Aggregation

- **ELK Stack**: Elasticsearch + Logstash + Kibana. Excellent full-text search
- **Grafana Loki**: Same label model as Prometheus, low storage cost, Grafana integration

**Best Practices**: JSON structured logging mandatory, include trace IDs, exclude PII

### Alerting

| Severity | Notification Target | Example |
|----------|---------------------|---------|
| Critical | PagerDuty/Opsgenie | Service down, data loss |
| Warning | Slack | Latency increase, disk space |
| Info | Email/Dashboard | Deployment complete |

## 6. API Types and Characteristics

| API | Features | Use Cases | Limitations |
|-----|----------|-----------|-------------|
| **REST** | HTTP standard, JSON, OpenAPI specification, cache control | External APIs, CRUD services | Over/under-fetching |
| **gRPC** | protobuf binary, HTTP/2, bidirectional streaming, type-safe | Internal inter-service communication, low-latency requirements | Difficult to call directly from browsers |
| **GraphQL** | Client-specified data shape, single endpoint | BFF, mobile apps | N+1 problem, complex caching |
| **Event-Driven** | Asynchronous, loosely coupled, highly extensible, eventual consistency | Asynchronous integration, event sourcing | Difficult to debug, requires idempotency design |
| **WebSocket** | Full-duplex communication, persistent connection, low latency | Chat, real-time notifications | Complex horizontal scaling |

### Event-Driven Tool Comparison

| Characteristic | Apache Kafka | RabbitMQ | Amazon SQS/SNS |
|----------------|-------------|----------|----------------|
| Model | Distributed log | Message broker | Managed queue |
| Ordering Guarantee | Within partition | Within queue | FIFO queue |
| Throughput | Very high | Medium to high | High |
| Persistence | Long-term retention possible | Deleted after consumption | Up to 14 days |

### API Selection Guide

| Requirement | Recommended API | Reason |
|-------------|-----------------|--------|
| External API | REST | Widely understood, rich tooling |
| Internal inter-service communication | gRPC | High performance, type-safe |
| Mobile BFF | GraphQL | Flexible data retrieval |
| Asynchronous processing | Kafka/RabbitMQ | Loosely coupled, high reliability |
| Real-time bidirectional | WebSocket | Low latency |
| Composite pattern | REST+gRPC+Kafka | Use appropriate APIs for each purpose |

---

## 7. Impact of ScalarDB Cluster on Microservice Architecture

### Impact on Architecture Design

Introducing ScalarDB Cluster brings the following changes to microservice architecture design guidelines.

| Traditional Approach | After ScalarDB Introduction |
|---------------------|----------------------------|
| Inter-service transactions use Saga pattern for eventual consistency | Two-Phase Commit interface enables strong consistency as an option |
| DB selection per service is constrained by transaction compatibility | Polyglot persistence can be adopted without constraints |
| DB migration requires big bang or complex parallel operation | Multi-Storage feature enables gradual, zero-downtime migration |
| Cross-service analytical queries require ETL/data warehouse | ScalarDB Analytics can execute cross-database queries directly |

### Deployment Patterns

ScalarDB Cluster provides two deployment patterns (see [official documentation](https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/deployment-patterns-for-microservices/)).

**Shared-Cluster Pattern (Recommended):**
- All microservices share a single ScalarDB Cluster
- Simple implementation with One-Phase Commit interface
- High resource efficiency and easy operational management

#### Risks and Mitigations of the Shared-Cluster Pattern

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Single Point of Failure** | ScalarDB Cluster failure stops all service transactions | HA configuration (minimum 3 nodes), graceful degradation via Circuit Breaker |
| **Noisy Neighbor** | Spikes from one service affect others | Ensure sufficient resources with ResourceQuota, enable Group Commit |
| **Deployment Coupling** | ScalarDB Cluster version upgrade affects all services | Blue-Green deployment, canary release |
| **Ambiguous Data Ownership** | Data from multiple services shares the same infrastructure | Logical separation with Namespace-level RBAC (3.17) |

> **Design Principle**: Shared-Cluster is "sharing database infrastructure," not "sharing data." Each service should only access data within its own Namespace.

**Separated-Cluster Pattern:**
- Each microservice has its own dedicated ScalarDB Cluster
- Inter-service transactions via Two-Phase Commit interface
- Effective when maximizing independence between teams

### Coexistence with Service Mesh

ScalarDB Cluster has built-in group membership and request routing capabilities, operating complementarily with service meshes such as Istio/Linkerd. The service mesh handles mTLS, traffic control, and observability, while ScalarDB Cluster handles transaction management and data routing.

---

## References

- [Sam Newman "Building Microservices" (O'Reilly)](https://www.oreilly.com/library/view/building-microservices-2nd/9781492034018/)
- [Martin Fowler - Microservices](https://martinfowler.com/articles/microservices.html)
- [Microservices.io - Patterns](https://microservices.io/patterns/index.html)
- [ScalarDB Cluster Deployment Patterns for Microservices](https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/deployment-patterns-for-microservices/)
- [The Twelve-Factor App](https://12factor.net/)
- [CNCF Cloud Native Landscape](https://landscape.cncf.io/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
