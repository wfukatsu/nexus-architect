# Spring Boot + ScalarDB 統合ガイド

## Gradle依存関係

```groovy
dependencies {
    implementation 'com.scalar-labs:scalardb:3.17.0'
    implementation 'com.scalar-labs:scalardb-sql-spring-data:3.17.0'  // Enterprise
    implementation 'org.springframework.boot:spring-boot-starter:3.2.0'
}
```

## ScalarDBプロパティ設定

```properties
# storage設定
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:postgresql://localhost:5432/scalardb
scalar.db.username=postgres
scalar.db.password=postgres

# トランザクションマネージャ
scalar.db.transaction_manager=consensus-commit

# デフォルトネームスペース
scalar.db.default_namespace_name=app

# Cluster接続（Enterprise）
scalar.db.transaction_manager=cluster
scalar.db.contact_points=indirect:lb.scalardb-cluster.svc.cluster.local
```

## Spring Data統合パターン

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

## トランザクションアノテーション

ScalarDBはSpringの `@Transactional` と直接統合しないため、
明示的なトランザクション管理パターンを使用:

```java
@Service
public class OrderService {
    private final DistributedTransactionManager manager;

    public void placeOrder(OrderRequest request) {
        DistributedTransaction tx = manager.begin();
        try {
            // ビジネスロジック
            tx.commit();
        } catch (CommitConflictException e) {
            tx.rollback();
            throw new RetryableException(e);
        }
    }
}
```
