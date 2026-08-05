# Spring Boot + ScalarDB Integration Guide

> **The versions below are a dated example** (snapshot: 2026-07), not the current stable releases.
> Resolve each pin per @rules/dependency-versions.md before writing a `build.gradle`, and check the
> Spring Boot ↔ Java ↔ ScalarDB combination for compatibility — the newest of each is not
> automatically a working set.

## Gradle Dependencies

```groovy
dependencies {
    implementation 'com.scalar-labs:scalardb:3.19.0'
    implementation 'com.scalar-labs:scalardb-sql-spring-data:3.19.0'  // Enterprise
    implementation 'org.springframework.boot:spring-boot-starter:3.2.0'
}
```

## ScalarDB Property Configuration

```properties
# Storage configuration
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:postgresql://localhost:5432/scalardb
scalar.db.username=postgres
scalar.db.password=postgres

# Transaction manager
scalar.db.transaction_manager=consensus-commit

# Default namespace
scalar.db.default_namespace_name=app

# Cluster connection (Enterprise)
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:lb.scalardb-cluster.svc.cluster.local
```

## Spring Data Integration Pattern

```java
@Configuration
public class ScalarDbConfig {
    @Bean
    public TransactionFactory transactionFactory() {
        return TransactionFactory.create("scalardb.properties");
    }

    @Bean
    public DistributedTransactionManager transactionManager(TransactionFactory factory) {
        return factory.getTransactionManager();
    }
}
```

## Transaction Annotations

ScalarDB does not integrate directly with Spring's `@Transactional`, so use an explicit transaction management pattern:

```java
@Service
public class OrderService {
    private final DistributedTransactionManager manager;

    public void placeOrder(OrderRequest request) {
        DistributedTransaction tx = manager.begin();
        try {
            // Business logic
            tx.commit();
        } catch (CommitConflictException e) {
            tx.rollback();
            throw new RetryableException(e);
        }
    }
}
```
