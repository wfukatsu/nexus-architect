# Cluster + CRUD API + One-Phase Commit

Production deployment using ScalarDB Cluster with the native CRUD API.

## build.gradle

```groovy
plugins {
    id 'java'
    id 'application'
}

repositories {
    mavenCentral()
}

dependencies {
    implementation 'com.scalar-labs:scalardb-cluster-java-client-sdk:3.16.0'
    implementation 'info.picocli:picocli:4.7.1'
    runtimeOnly 'org.apache.logging.log4j:log4j-slf4j2-impl:2.20.0'
    runtimeOnly 'org.apache.logging.log4j:log4j-core:2.20.0'
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(8)
    }
}

application {
    mainClass = 'sample.command.SampleCommand'
}
```

## database.properties

```properties
# Cluster connection (via load balancer)
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:localhost

# Alternative: direct Kubernetes connection
#scalar.db.transaction_manager=cluster
#scalar.db.contact_points=direct-kubernetes:scalardb/scalardb-cluster

# Auth (if enabled on server)
#scalar.db.cluster.auth.enabled=true
#scalar.db.username=admin
#scalar.db.password=admin

# TLS (if enabled on server)
#scalar.db.cluster.tls.enabled=true
#scalar.db.cluster.tls.ca_root_cert_path=/path/to/ca.pem
```

## schema.json

```json
{
  "sample.customers": {
    "transaction": true,
    "partition-key": ["customer_id"],
    "columns": {
      "customer_id": "INT",
      "name": "TEXT",
      "credit_limit": "INT",
      "credit_total": "INT"
    }
  },
  "sample.orders": {
    "transaction": true,
    "partition-key": ["customer_id"],
    "clustering-key": ["timestamp"],
    "columns": {
      "customer_id": "INT",
      "timestamp": "BIGINT",
      "order_id": "TEXT"
    },
    "secondary-index": ["order_id"]
  }
}
```

## Service Class

The code is **identical** to Core+CRUD+1PC. The only difference is the configuration file:

```java
package sample;

import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Get;
import com.scalar.db.api.Insert;
import com.scalar.db.api.Result;
import com.scalar.db.api.Scan;
import com.scalar.db.api.Update;
import com.scalar.db.exception.transaction.RollbackException;
import com.scalar.db.exception.transaction.TransactionException;
import com.scalar.db.exception.transaction.UnknownTransactionStatusException;
import com.scalar.db.exception.transaction.UnsatisfiedConditionException;
import com.scalar.db.io.Key;
import com.scalar.db.service.TransactionFactory;
import java.io.Closeable;
import java.io.IOException;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

public class Sample implements Closeable {

  private final DistributedTransactionManager manager;

  public Sample(String configFile) throws TransactionException {
    // Same factory pattern — config determines Core vs Cluster
    TransactionFactory factory = TransactionFactory.create(configFile);
    manager = factory.getTransactionManager();
  }

  public String getCustomerInfo(int customerId) throws TransactionException {
    DistributedTransaction tx = null;
    try {
      tx = manager.begin();

      Optional<Result> result = tx.get(
          Get.newBuilder()
              .namespace("sample")
              .table("customers")
              .partitionKey(Key.ofInt("customer_id", customerId))
              .build());

      tx.commit();

      if (!result.isPresent()) {
        throw new RuntimeException("Customer not found");
      }
      return result.get().getText("name");
    } catch (Exception e) {
      if (tx != null) {
        try { tx.abort(); } catch (Exception ex) { /* log */ }
      }
      throw e;
    }
  }

  @Override
  public void close() throws IOException {
    manager.close();
  }
}
```

## Key Differences from Core Mode

| Aspect | Core | Cluster |
|--------|------|---------|
| Maven artifact | `com.scalar-labs:scalardb` | `com.scalar-labs:scalardb-cluster-java-client-sdk` |
| Config property | `scalar.db.storage=jdbc` | `scalar.db.transaction_manager=cluster` |
| Contact points | Direct DB URL | `indirect:<host>` or `direct-kubernetes:<ns>/<ep>` |
| Java code | Identical | Identical |
| Auth/TLS | N/A | Supported |

## Schema Loading (Cluster)

```bash
# Use cluster schema loader
java -jar scalardb-cluster-schema-loader-<VERSION>-all.jar \
  --config database.properties -f schema.json --coordinator
```

## Contact Points Modes

| Mode | Format | When to Use |
|------|--------|-------------|
| `indirect` | `indirect:<LB_HOST>` | External clients via load balancer |
| `direct-kubernetes` | `direct-kubernetes:<NS>/<EP>` | In-cluster K8s clients (better performance) |
