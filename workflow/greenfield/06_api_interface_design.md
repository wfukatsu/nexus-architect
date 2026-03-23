# Phase 2-3: API and Interface Design

## Purpose

Design API specifications and data access patterns for inter-microservice communication. Based on the transaction design developed in Step 05 and the domain model from Step 02, determine inter-service communication methods (gRPC, REST, asynchronous messaging, etc.) and concretize API specifications including access patterns for ScalarDB-managed data.

---

## Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Transaction Design | Step 05 Deliverables | Pattern assignment table, 2PC/Saga design, CDC design |
| Domain Model | Step 02 Deliverables | Bounded context diagram, aggregate design |
| Data Model | Step 04 Deliverables | ScalarDB schema definitions, table list |

## Reference Materials

| Document | Path | Key Sections |
|----------|------|--------------|
| Transparent Data Access | `../research/08_transparent_data_access.md` | ScalarDB Analytics, CDC, Hybrid Patterns |
| Microservice Architecture | `../research/01_microservice_architecture.md` | Inter-service Communication, API Design Principles, BFF Pattern |
| Transaction Model | `../research/07_transaction_model.md` | 2PC Interface, Saga Pattern, Outbox Pattern (2PC coordination design, inter-service transaction patterns) |

---

## Steps

### Step 6.1: API Type Determination

#### 6.1.1 Communication Method Comparison

| Communication Method | Protocol | Latency | Type Safety | Use Case |
|---------------------|----------|---------|-------------|----------|
| **gRPC** | HTTP/2 + Protocol Buffers | Low | High (IDL definition) | Synchronous inter-service communication, 2PC coordination |
| **REST** | HTTP/1.1 or HTTP/2 + JSON | Medium | Medium (OpenAPI) | Externally exposed APIs, web client-facing |
| **GraphQL** | HTTP + JSON | Medium | High (Schema definition) | BFF, flexible data fetching for frontend |
| **Asynchronous Messaging** | Kafka / NATS / RabbitMQ | - (async) | Medium (Avro/Protobuf) | Event-driven, inter-step communication in Saga |
| **ScalarDB SQL API** | JDBC-compatible | Low | High | Data access in SQL format |
| **ScalarDB gRPC API** | gRPC | Low | High | Access from non-Java clients |

#### 6.1.2 API Type Selection Decision Tree

```mermaid
flowchart TD
    A["Who is the API consumer?"] -->|"Internal service"| B{"Is this 2PC/Saga\ncoordination?"}
    A -->|"External client"| C{"What is the\nclient type?"}
    A -->|"Data pipeline"| D["Asynchronous Messaging\n(Kafka + CDC)"]

    B -->|"Yes (2PC)"| E["gRPC\n(Low latency + TxId propagation)"]
    B -->|"No"| F{"Is real-time response\nrequired?"}
    F -->|"Yes"| E
    F -->|"No"| G["Asynchronous Messaging\n(Event-driven)"]

    C -->|"Web browser"| H{"Is the data fetching\npattern complex?"}
    C -->|"Mobile app"| I["GraphQL BFF\n(Bandwidth optimization)"]
    C -->|"External partner"| J["REST\n(Standard, broad compatibility)"]

    H -->|"Yes"| K["GraphQL BFF"]
    H -->|"No"| J

    style E fill:#bbdefb,stroke:#2196f3
    style J fill:#c8e6c9,stroke:#4caf50
    style K fill:#e1bee7,stroke:#9c27b0
    style D fill:#ffe0b2,stroke:#ff9800
    style G fill:#ffe0b2,stroke:#ff9800
    style I fill:#e1bee7,stroke:#9c27b0
```

#### 6.1.3 ScalarDB API Usage Guide

| ScalarDB API | Purpose | Selection Criteria |
|-------------|---------|-------------------|
| **CRUD API (Java)** | Direct access from within a service | Java services requiring fine-grained control |
| **SQL API (JDBC)** | SQL-based access | Leveraging existing SQL skills, complex queries |
| **gRPC API** | Access from non-Java clients | Go, Python, and other non-Java services |
| **Via ScalarDB Cluster** | Recommended configuration for production | Cluster management, load balancing, routing |

---

### Step 6.2: Inter-Service Communication Pattern Design

#### 6.2.1 Synchronous Communication: gRPC Calls During 2PC Coordination

Design communication between Coordinator and Participants in 2PC transactions.

```mermaid
sequenceDiagram
    participant Client as External Client (REST)
    participant GW as API Gateway
    participant BFF as BFF Service
    participant Coord as Order Service<br/>(Coordinator)
    participant P1 as Inventory Service<br/>(Participant)
    participant P2 as Payment Service<br/>(Participant)

    Client->>GW: POST /api/v1/orders (REST/JSON)
    GW->>BFF: Forward (Authenticated)
    BFF->>Coord: gRPC: CreateOrder(request)

    Note over Coord,P2: 2PC Transaction (gRPC)
    Coord->>P1: gRPC: ReserveStock(txId, items)
    P1-->>Coord: gRPC: ReserveStockResponse
    Coord->>P2: gRPC: ProcessPayment(txId, amount)
    P2-->>Coord: gRPC: ProcessPaymentResponse

    Coord-->>BFF: gRPC: CreateOrderResponse
    BFF-->>GW: REST/JSON Response
    GW-->>Client: 201 Created
```

**gRPC Service Definition Example:**

```protobuf
// gRPC definition for 2PC coordination
service InventoryService {
    // Stock reservation as a 2PC Participant
    rpc ReserveStock(ReserveStockRequest) returns (ReserveStockResponse);
    // 2PC Prepare
    rpc PrepareTransaction(PrepareRequest) returns (PrepareResponse);
    // 2PC Validate
    rpc ValidateTransaction(ValidateRequest) returns (ValidateResponse);
    // 2PC Commit
    rpc CommitTransaction(CommitRequest) returns (CommitResponse);
    // 2PC Abort
    rpc AbortTransaction(AbortRequest) returns (AbortResponse);
}

message ReserveStockRequest {
    string transaction_id = 1;  // ScalarDB TxId
    repeated StockReservation reservations = 2;
}

message StockReservation {
    string item_id = 1;
    string warehouse_id = 2;
    int32 quantity = 3;
}
```

#### 6.2.2 Asynchronous Communication: Domain Event Propagation

```mermaid
flowchart LR
    subgraph OrderService["Order Service"]
        O1["Order Logic"]
        O2["ScalarDB Tx\n(Outbox Table Write)"]
        O3["CDC / Polling"]
    end

    subgraph Kafka["Kafka"]
        T1["order.events"]
        T2["inventory.events"]
        T3["notification.events"]
    end

    subgraph Consumers["Consumer Services"]
        C1["Inventory Service"]
        C2["Notification Service"]
        C3["Analytics Service"]
    end

    O1 --> O2
    O2 --> O3
    O3 --> T1

    T1 --> C1
    C1 --> T2
    T1 --> C2
    C2 --> T3
    T1 --> C3

    style O2 fill:#bbdefb,stroke:#2196f3
```

**Event Schema Design:**

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string (UUID) | Unique identifier for the event |
| `event_type` | string | Event type (e.g., `OrderCreated`, `OrderConfirmed`) |
| `aggregate_id` | string | ID of the aggregate root |
| `aggregate_type` | string | Type name of the aggregate |
| `payload` | JSON/Protobuf | Event data body |
| `metadata.timestamp` | long | Event occurrence timestamp |
| `metadata.correlation_id` | string | Request tracking ID |
| `metadata.causation_id` | string | Causation event ID |

#### 6.2.3 API Composition Pattern

Design of the API Composition pattern that integrates and returns data from multiple services.

```mermaid
flowchart TD
    Client["Client"] --> Composer["API Composer / BFF"]

    Composer -->|"1. gRPC"| OrderSvc["Order Service"]
    Composer -->|"2. gRPC"| CustomerSvc["Customer Service"]
    Composer -->|"3. gRPC"| InventorySvc["Inventory Service"]

    OrderSvc -->|"ScalarDB"| OrderDB["Order DB"]
    CustomerSvc -->|"ScalarDB"| CustomerDB["Customer DB"]
    InventorySvc -->|"ScalarDB"| InventoryDB["Inventory DB"]

    Composer -->|"Join & Format"| Response["Integrated Response"]
    Response --> Client

    style Composer fill:#fff9c4,stroke:#ffc107
```

**API Composition Design Template:**

| Composition API | Target Services | Parallelizable | Timeout | Fallback |
|----------------|-----------------|----------------|---------|----------|
| GET /orders/{id}/detail | Order, Customer, Inventory | Order -> (Customer, Inventory in parallel) | 3s | Return basic info only when Customer is unavailable |
| GET /dashboard | Order, Payment, Analytics | All parallel | 5s | Independent fallback per service |

#### 6.2.4 BFF Pattern (Web/Mobile Variants)

| BFF | Target Client | Technology | Optimization Focus |
|-----|---------------|------------|-------------------|
| **Web BFF** | Web browser | GraphQL / REST | Page-level data aggregation, SSR support |
| **Mobile BFF** | iOS/Android | GraphQL / REST | Bandwidth optimization, offline support, push notification integration |
| **Admin BFF** | Admin panel | REST | Bulk operations, CSV export, dashboard aggregation |

---

### Step 6.3: Data Access Pattern Design

#### 6.3.1 Access to ScalarDB-Managed Data

| Access Pattern | Method | Purpose |
|---------------|--------|---------|
| **Intra-service CRUD** | ScalarDB CRUD API / SQL API | Own service data operations |
| **Inter-service reads** | Via gRPC API (query to data owner service) | Reference to other service data |
| **Inter-service writes** | Via 2PC Interface | Data updates across multiple services |
| **Analytical queries** | ScalarDB Analytics (Spark / PostgreSQL) | Cross-service analytics and reporting |

#### 6.3.2 Integration with Non-ScalarDB-Managed Data

Refer to `08_transparent_data_access.md` to design integration patterns with non-ScalarDB-managed data.

```mermaid
flowchart TD
    subgraph ScalarDBManaged["ScalarDB-Managed"]
        T1["orders\n(Cassandra)"]
        T2["accounts\n(MySQL)"]
        T3["stocks\n(DynamoDB)"]
    end

    subgraph NonManaged["Non-ScalarDB-Managed"]
        E1["Search Index\n(Elasticsearch)"]
        E2["Cache\n(Redis)"]
        E3["File Storage\n(S3)"]
        E4["External API\n(Payment Gateway)"]
    end

    subgraph Integration["Integration Patterns"]
        I1["CDC\n(ScalarDB -> Elasticsearch)"]
        I2["Cache-Aside\n(ScalarDB + Redis)"]
        I3["API Composition\n(ScalarDB + External API)"]
        I4["ScalarDB Analytics\n(Cross-DB Analysis)"]
    end

    T1 -->|"CDC"| I1 --> E1
    T2 -->|"Read-through"| I2 --> E2
    T3 -->|"Composition"| I3 --> E4
    T1 & T2 & T3 -->|"Analytics"| I4

    style ScalarDBManaged fill:#e3f2fd,stroke:#2196f3
    style NonManaged fill:#f3e5f5,stroke:#9c27b0
    style Integration fill:#fff3e0,stroke:#ff9800
```

| Integration Pattern | Target | Data Flow | Consistency |
|--------------------|--------|-----------|-------------|
| **CDC** | Search index, analytics DB | ScalarDB -> Kafka -> Elasticsearch, etc. | Eventual consistency (seconds to minutes) |
| **Cache-Aside** | Cache | App -> Redis (read from ScalarDB on miss) | TTL-based eventual consistency |
| **API Composition** | External services | App -> ScalarDB + External API -> Join | Request-time consistency |
| **ScalarDB Analytics** | Analytics and reporting | Direct analytical queries on ScalarDB-managed data | Snapshot consistency |
| **Outbox + CDC** | Event-driven | Write to Outbox within ScalarDB Tx -> CDC -> Kafka | ACID within Outbox, eventual consistency downstream |

#### 6.3.3 Hybrid Patterns

Hybrid patterns combining ScalarDB-managed and non-managed data.

| Pattern | Description | Implementation Method |
|---------|-------------|----------------------|
| **Write: ScalarDB / Read: Elasticsearch** | ACID writes + full-text search | Sync to Elasticsearch via CDC |
| **Write: ScalarDB / Read: Redis Cache** | ACID writes + low-latency reads | Cache-Aside or Write-Through |
| **Write: ScalarDB / Analytics: Spark** | ACID writes + batch analytics | ScalarDB Analytics with Spark |
| **Command: ScalarDB / Query: PostgreSQL** | CQRS pattern | Sync to read model via CDC |

#### 6.3.4 Positioning in Data Mesh

| Data Mesh Principle | ScalarDB-Related Design Guideline |
|--------------------|------------------------------------|
| **Domain Ownership** | Each microservice owns and manages its own domain's ScalarDB tables |
| **Data as a Product** | Expose service APIs as data products (gRPC/REST) |
| **Self-Service Platform** | Provide ScalarDB Cluster as a self-service data platform |
| **Federated Governance** | Standardize namespace naming conventions and schema compatibility rules across all teams |

---

### Step 6.4: API Specification Definition

#### 6.4.1 Endpoint List Template

| # | Method | Path | Service | Description | Authentication | Rate Limit |
|---|--------|------|---------|-------------|----------------|------------|
| 1 | POST | /api/v1/orders | Order | Create order | Bearer Token | 100 req/s |
| 2 | GET | /api/v1/orders/{id} | Order | Get order details | Bearer Token | 500 req/s |
| 3 | POST | /api/v1/orders/{id}/confirm | Order | Confirm order (triggers 2PC) | Bearer Token | 50 req/s |
| 4 | GET | /api/v1/orders?customer_id={id} | Order (BFF) | List customer orders | Bearer Token | 200 req/s |

#### 6.4.2 Request/Response Definition Template

```json
// POST /api/v1/orders - Request
{
    "customer_id": "cust-001",
    "items": [
        {
            "item_id": "item-001",
            "quantity": 2
        }
    ],
    "payment_method": "credit_card",
    "idempotency_key": "req-uuid-001"
}

// POST /api/v1/orders - Response (201 Created)
{
    "order_id": "ord-001",
    "status": "PENDING",
    "total_amount": 5000,
    "created_at": "2026-02-17T10:00:00Z",
    "links": {
        "self": "/api/v1/orders/ord-001",
        "confirm": "/api/v1/orders/ord-001/confirm"
    }
}
```

#### 6.4.3 Error Handling (Mapping ScalarDB Transaction Exceptions)

Map ScalarDB internal exceptions to HTTP status codes and gRPC status codes.

| ScalarDB Exception | Cause | HTTP Status | gRPC Status | Client Action |
|-------------------|-------|-------------|-------------|---------------|
| `CrudConflictException` | OCC conflict | 409 Conflict | ABORTED | Retry (exponential backoff) |
| `CommitConflictException` | OCC conflict at Commit | 409 Conflict | ABORTED | Retry (exponential backoff) |
| `UncommittedRecordException` | Pending record from previous Tx | 503 Service Unavailable | UNAVAILABLE | Retry (after short wait) |
| `PreparationConflictException` | Conflict at 2PC Prepare | 409 Conflict | ABORTED | Retry |
| `ValidationConflictException` | Conflict at 2PC Validation | 409 Conflict | ABORTED | Retry |
| `CommitException` (unknown error) | Commit result unknown | 500 Internal Server Error | INTERNAL | Verify transaction state then retry |
| `TransactionNotFoundException` | Transaction ID not found (occurs during 2PC join) | 404 Not Found | NOT_FOUND | Verify transaction ID and resend |
| `TransactionConflictException` | Generic transaction conflict | 409 Conflict | ABORTED | Retry (exponential backoff) |
| `UnsatisfiedConditionException` | Condition not met for conditional operation | 412 Precondition Failed | FAILED_PRECONDITION | Verify condition and resend |

**Error Response Format:**

```json
{
    "error": {
        "code": "TRANSACTION_CONFLICT",
        "message": "The operation conflicted with another transaction. Please retry.",
        "details": {
            "retry_after_ms": 100,
            "max_retries": 5
        },
        "request_id": "req-uuid-001",
        "timestamp": "2026-02-17T10:00:00Z"
    }
}
```

#### 6.4.4 Retry Strategy

| Error Type | Retryable | Strategy | Max Retries | Initial Wait | Max Wait |
|-----------|-----------|----------|-------------|--------------|----------|
| OCC conflict (409) | Yes | Exponential backoff + jitter | 5 | 100ms | 5s |
| Transient failure (503) | Yes | Fixed interval | 3 | 500ms | 500ms |
| Unknown commit (500) | Conditional | Safe retry with idempotency key | 3 | 1s | 10s |
| Validation error (400) | No | - | - | - | - |
| Authentication error (401/403) | No | - | - | - | - |

**Exponential Backoff + Jitter Implementation Guidelines:**

```
wait_time = min(max_wait, initial_wait * 2^(attempt - 1)) + random(0, jitter)
jitter = wait_time * 0.1  // 10% random jitter
```

---

### Step 6.5: API Gateway Design

#### 6.5.1 API Gateway Functional Requirements

| Feature | Description | Priority |
|---------|-------------|----------|
| **Routing** | Path-based, header-based service routing | Required |
| **Authentication** | JWT verification, OAuth2/OIDC integration | Required |
| **Rate Limiting** | Per service, per endpoint, per user | Required |
| **Load Balancing** | Load balancing to service instances | Required |
| **Circuit Breaker** | Request blocking to failed services | Recommended |
| **Request Logging** | Access logs, audit logs | Required |
| **CORS** | Cross-origin request control | Required for Web APIs |
| **TLS Termination** | HTTPS to HTTP conversion | Required |
| **Request Transformation** | Header addition, path rewriting | Recommended |
| **Health Check** | Backend service health verification | Required |

#### 6.5.2 API Gateway Selection

| Product | Features | Use Case |
|---------|----------|----------|
| **Kong** | Plugin ecosystem, declarative configuration | General purpose, emphasis on plugin extensibility |
| **Envoy + Istio** | Service mesh integration, L7 proxy | Kubernetes environments, mTLS required |
| **AWS API Gateway** | Managed service, Lambda integration | AWS environments, serverless architecture |
| **NGINX / OpenResty** | High performance, Lua extension | High throughput requirements |
| **Traefik** | Auto-discovery, K8s Ingress | Small to medium scale, simple configuration |

#### 6.5.3 Overall Communication Architecture

```mermaid
flowchart TD
    subgraph External["External"]
        Web["Web Browser"]
        Mobile["Mobile App"]
        Partner["External Partner"]
    end

    subgraph Gateway["API Gateway Layer"]
        GW["API Gateway\n(Kong / Envoy)"]
    end

    subgraph BFFLayer["BFF Layer"]
        WebBFF["Web BFF\n(GraphQL)"]
        MobileBFF["Mobile BFF\n(GraphQL)"]
    end

    subgraph Services["Microservices (gRPC)"]
        OrderSvc["Order Service"]
        InventorySvc["Inventory Service"]
        PaymentSvc["Payment Service"]
        CustomerSvc["Customer Service"]
        NotifySvc["Notification Service"]
    end

    subgraph Data["Data Layer"]
        ScalarDB["ScalarDB Cluster"]
        Kafka["Kafka"]
        Redis["Redis Cache"]
        ES["Elasticsearch"]
    end

    Web -->|"HTTPS"| GW
    Mobile -->|"HTTPS"| GW
    Partner -->|"HTTPS/REST"| GW

    GW -->|"REST/GraphQL"| WebBFF
    GW -->|"REST/GraphQL"| MobileBFF
    GW -->|"REST"| OrderSvc

    WebBFF -->|"gRPC"| OrderSvc
    WebBFF -->|"gRPC"| CustomerSvc
    MobileBFF -->|"gRPC"| OrderSvc
    MobileBFF -->|"gRPC"| CustomerSvc

    OrderSvc -->|"gRPC (2PC)"| InventorySvc
    OrderSvc -->|"gRPC (2PC)"| PaymentSvc
    OrderSvc -->|"Event"| Kafka

    Kafka --> NotifySvc
    Kafka --> ES

    OrderSvc -->|"ScalarDB API"| ScalarDB
    InventorySvc -->|"ScalarDB API"| ScalarDB
    PaymentSvc -->|"ScalarDB API"| ScalarDB
    CustomerSvc -->|"ScalarDB API"| ScalarDB

    OrderSvc -->|"Cache"| Redis

    style Gateway fill:#e8f5e9,stroke:#4caf50
    style BFFLayer fill:#e3f2fd,stroke:#2196f3
    style Services fill:#fff3e0,stroke:#ff9800
    style Data fill:#fce4ec,stroke:#e91e63
```

---

## Deliverables

| Deliverable | Format | Content |
|-------------|--------|---------|
| **API Specification** | OpenAPI 3.0 (REST) / Protobuf (gRPC) / GraphQL Schema | Endpoint definitions, request/response, error codes |
| **Inter-Service Communication Design Document** | Design document + Mermaid diagrams | Synchronous/asynchronous communication patterns, 2PC coordination, event design |
| **Data Access Pattern Definition** | Design document | Access methods for ScalarDB-managed/non-managed data, integration patterns |
| **API Gateway Configuration** | Configuration file (Kong declarative config, etc.) | Routing, authentication, rate limiting configuration |
| **Error Handling Specification** | Design document | ScalarDB exception mapping, retry strategy |
| **Event Schema Definition** | Avro / Protobuf / JSON Schema | Domain event schema definitions |

---

## Completion Criteria Checklist

### API Types and Communication Methods

- [ ] Communication methods (gRPC/REST/async) are determined for all inter-service communication
- [ ] Communication methods for externally exposed APIs are determined
- [ ] Need for BFF configuration has been evaluated
- [ ] ScalarDB API usage (CRUD/SQL/gRPC) is determined

### Inter-Service Communication

- [ ] gRPC service definitions for 2PC transactions are complete
- [ ] TxId propagation method is defined (gRPC metadata, etc.)
- [ ] Event schemas for asynchronous communication are defined
- [ ] Outbox pattern implementation method is defined (if applicable)
- [ ] API Composition targets and parallelization are defined

### Data Access Patterns

- [ ] Access patterns for ScalarDB-managed data are defined for all operations
- [ ] Integration patterns with non-ScalarDB-managed data are designed
- [ ] CDC data sync destinations and sync methods are defined
- [ ] Cache strategy (Cache-Aside, etc.) is designed (if applicable)

### API Specifications

- [ ] HTTP methods, paths, request/response are defined for all endpoints
- [ ] ScalarDB exception HTTP/gRPC status code mapping is defined
- [ ] Retry strategy (exponential backoff, max retries, idempotency keys) is defined
- [ ] Error response JSON format is standardized
- [ ] API versioning strategy is defined

### API Gateway

- [ ] API Gateway product is selected
- [ ] Routing rules are defined
- [ ] Authentication method (JWT verification, OAuth2, etc.) is configured
- [ ] Rate limiting is configured per endpoint
- [ ] Circuit breaker thresholds are configured

### Non-Functional Requirements

- [ ] Latency requirements are defined for each API
- [ ] Throughput requirements are defined for each API
- [ ] API Composition timeouts and fallbacks are designed
- [ ] CORS policy is defined (Web APIs)
