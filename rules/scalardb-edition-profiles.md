# ScalarDB Edition Profiles

## Edition Comparison

| Feature | OSS | Enterprise Standard | Enterprise Premium |
|---------|-----|--------------------|--------------------|
| Consensus Commit | Yes | Yes | Yes |
| JDBC-compatible DBs | Yes | Yes | Yes |
| NoSQL Support | Cassandra, DynamoDB, CosmosDB | Same | Same |
| Two-Phase Commit | Yes | Yes | Yes |
| ScalarDB Cluster | No | Yes | Yes |
| SQL Interface | No | Yes | Yes |
| GraphQL | No | Yes | Yes |
| Spring Data Integration | Basic | Full | Full |
| ScalarDB Analytics | No | No | Yes |
| Multi-Region | No | No | Yes |
| SLA | Community | 99.9% | 99.99% |
| Support | Community | Business Hours | 24/7 |

## Deployment Modes

### Core (OSS)
- Embedded in the application
- Used directly as a library
- No gRPC server required

### Cluster (Enterprise)
- Independent gRPC server cluster
- Deployed on Kubernetes
- Applications connect via gRPC client
- Supports horizontal scaling

## Selection Criteria

| Requirement | Recommended Edition |
|-------------|---------------------|
| Single-DB transactions | OSS |
| Multi-DB transactions | OSS or Enterprise |
| SQL interface needed | Enterprise Standard+ |
| Analytical queries needed | Enterprise Premium |
| 99.99% SLA | Enterprise Premium |
| 2PC across 5+ services | Enterprise Standard+ (Cluster recommended) |
