# Cluster + CRUD API + Microservice Transaction (one-phase across services)

A transaction that spans microservices on ScalarDB Cluster 3.19+, written with the **Microservice
Transaction API** (`GlobalTransactionManager` / `GlobalTransaction` / `BranchTransaction`). The
application code is one-phase and **identical** for the shared-cluster and the separated-cluster
patterns; only the properties files differ. On separated clusters the Transaction Coordinator node
drives two-phase commit underneath. This replaces `cluster-crud-2pc.md`, whose interface is
deprecated as of 3.19. Rules: `rules/scalardb-2pc-patterns.md`.

> **Versions in this file are a dated example** (snapshot: 2026-10, grounded on the bundle's
> `products/scalardb/3.20/scalardb-cluster/api-guide.md` § Microservice Transaction API and
> `scalardb-samples/microservice-transaction-sample-with-cluster/`), not the current stable
> release. Resolve each pin per `rules/dependency-versions.md`. A project pinned to 3.19 finds this
> API only in that line's release notes — say so in the design.

## build.gradle

```groovy
dependencies {
    implementation 'com.scalar-labs:scalardb-cluster-java-client-sdk:3.20.0'
}
```

## Properties — shared-cluster pattern (every service)

```properties
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:scalardb-cluster-node
scalar.db.cluster.client.transaction_coordinator.enabled=false
```

## Properties — separated-cluster pattern

```properties
# order-service.properties (each service: its own cluster + the Coordinator)
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:order-cluster
scalar.db.cluster.id=order-cluster
scalar.db.cluster.client.transaction_coordinator.enabled=true
scalar.db.cluster.client.transaction_coordinator.contact_points=indirect:transaction-coordinator
scalar.db.cluster.client.transaction_coordinator.contact_port=60055

# order-cluster node properties (in addition to storage, licensing, …)
scalar.db.cluster.node.transaction_participant.enabled=true
scalar.db.cluster.id=order-cluster

# transaction-coordinator.properties
scalar.db.cluster.transaction_coordinator.standalone_mode.enabled=true
scalar.db.cluster.transaction_coordinator.clusters=customer-cluster,order-cluster
scalar.db.cluster.transaction_coordinator.clusters.customer-cluster.contact_points=indirect:customer-cluster
scalar.db.cluster.transaction_coordinator.clusters.customer-cluster.contact_port=60053
scalar.db.cluster.transaction_coordinator.clusters.order-cluster.contact_points=indirect:order-cluster
scalar.db.cluster.transaction_coordinator.clusters.order-cluster.contact_port=60053
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:postgresql://postgres:5432/postgres   # the Coordinator table's database
scalar.db.username=postgres
scalar.db.password=postgres
```

Every cluster maps the `coordinator` namespace to that same database (multi-storage
`namespace_mapping=coordinator:coordinatordb`), because an instance that meets a record left by an
unfinished transaction looks its state up there.

## Orchestrating service (begins, runs its own branch, commits)

```java
public class OrderService {
  private final GlobalTransactionManager manager;   // factory.getGlobalTransactionManager()
  private final CustomerServiceClient customerService;

  public String placeOrder(int customerId, int amount) throws TransactionException {
    for (int attempt = 1; ; attempt++) {
      GlobalTransaction global = manager.begin();
      BranchTransaction branch = null;
      try {
        branch = manager.beginBranch(global.getId());
        String orderId = UUID.randomUUID().toString();
        branch.insert(Insert.newBuilder().namespace("order_service").table("orders")
            .partitionKey(Key.ofInt("customer_id", customerId))
            .clusteringKey(Key.ofText("order_id", orderId))
            .intValue("amount", amount).build());
        branch.end(BranchTransaction.Status.SUCCESS);

        // The participant runs its own branch of the same transaction and reports back.
        customerService.charge(global.getId(), customerId, amount);   // RPC carries the ID

        global.commit();                       // only after every branch ended SUCCESS
        return orderId;
      } catch (CommitConflictException | CrudConflictException e) {
        endFailure(branch, e);
        global.rollback();
        if (attempt >= 3) throw e;
        sleep(100);                            // retry the WHOLE global transaction
      } catch (UnknownTransactionStatusException e) {
        endFailure(branch, e);
        throw e;                               // do not rollback; outcome unknown — see api-error-standard
      } catch (Exception e) {
        endFailure(branch, e);
        global.rollback();                     // discards every branch's writes; no-op after a commit
        throw e;
      }
    }
  }

  private static void endFailure(BranchTransaction branch, Exception cause) {
    if (branch == null) return;
    try { branch.end(BranchTransaction.Status.FAILURE); }   // no-op if already ended SUCCESS
    catch (RuntimeException | CrudException suppressed) { cause.addSuppressed(suppressed); }
  }
}
```

## Participant service (runs a branch, never commits)

```java
public class CustomerService {
  private final GlobalTransactionManager manager;   // its own cluster's client; same code either pattern

  public void charge(String transactionId, int customerId, int amount) throws TransactionException {
    BranchTransaction branch = manager.beginBranch(transactionId);   // TransactionNotFoundException if expired
    try {
      Optional<Result> customer = branch.get(Get.newBuilder().namespace("customer_service")
          .table("customers").partitionKey(Key.ofInt("customer_id", customerId)).build());
      int total = customer.orElseThrow().getInt("credit_total") + amount;
      if (total > customer.get().getInt("credit_limit")) {
        throw new CreditLimitExceededException(customerId);          // business failure → orchestrator rolls back
      }
      branch.update(Update.newBuilder().namespace("customer_service").table("customers")
          .partitionKey(Key.ofInt("customer_id", customerId)).intValue("credit_total", total).build());
      branch.end(BranchTransaction.Status.SUCCESS);
    } catch (Exception e) {
      try { branch.end(BranchTransaction.Status.FAILURE); }
      catch (RuntimeException | CrudException suppressed) { e.addSuppressed(suppressed); }
      throw e;
    }
  }
}
```

## What the test must prove

- A participant failure after the orchestrator's branch ended `SUCCESS` leaves **no** order row
  (rollback discards all branches).
- A `TransactionNotFoundException` on `beginBranch` (expired ID) is mapped to 404
  `transaction-not-found` and the orchestrator rolls back.
- The same two services, re-pointed from the shared-cluster properties to the separated-cluster
  properties, pass the same tests with no code change.
