# How the generated files should be used (Oracle AQ migration)

The text the AQ migration report carries for the user, under its own heading: what has to be in
place before the generated files are used, and the steps to integrate them. Write it into the
report as it stands, adjusted to the files and names this migration actually generated.

## Prerequisites

1. **Import the database into ScalarDB first.** ScalarDB consumer code cannot modify the database unless the tables are migrated and managed through ScalarDB. Use the Schema Loader with `--import` to import existing Oracle tables.

2. **Run `aq_setup.sql` against the Oracle database.** This creates the AQ infrastructure (payload types, queues) and replaces the original triggers/SPs with AQ-enabled versions.

3. **Add required JAR files to your project:**
   - `aqapi.jar` — extract from `$ORACLE_HOME/rdbms/jlib/aqapi.jar` inside the Oracle DB container or installation
   - `javax.jms-api-2.0.1.jar` — available from Maven Central or Oracle DB
   - `ojdbc11` — Oracle JDBC driver from Maven Central
   - `scalardb` — ScalarDB from Maven Central

## Integration Steps

1. **Add the generated Java files** to your application's source tree under `com.example.scalardb.aq` (or your preferred package).

2. **Initialize ScalarDB** in your application startup:
   ```java
   TransactionFactory factory = TransactionFactory.create("scalardb.properties");
   DistributedTransactionManager txManager = factory.getTransactionManager();
   ```

3. **Create the AQ JMS consumer loop** in your application's main class or service runner. The generated consumer classes provide `processMessage()` and `parseMessage()` methods — your application provides the JMS connection and dequeue loop:
   ```java
   // Application responsibility: JMS connection, session, receiver
   QueueConnectionFactory qcf = AQjmsFactory.getQueueConnectionFactory(jdbcUrl, props);
   QueueConnection conn = qcf.createQueueConnection(user, pass);
   QueueSession session = conn.createQueueSession(true, Session.SESSION_TRANSACTED);
   Queue queue = ((AQjmsSession) session).getQueue(QUEUE_OWNER, QUEUE_NAME);
   ORADataFactory payloadFactory = (datum, sqlType) -> new AqStructHolder(datum);
   QueueReceiver receiver = ((AQjmsSession) session).createReceiver(queue, null, payloadFactory);

   // Use generated consumer with exception classification
   var consumer = new <QueueName>Consumer(txManager);
   while (!Thread.currentThread().isInterrupted()) {
       Message msg = receiver.receive(10_000);
       if (msg == null) continue;

       // Phase 1: Parse — failure = broken payload, remove immediately
       <PayloadName>Message parsed;
       try {
           parsed = <QueueName>Consumer.parseMessage(msg);
       } catch (Exception e) {
           log.error("Parse failed — removing poison message: {}", e.getMessage(), e);
           session.commit();
           continue;
       }

       // Phase 2: Process — classify the outcome
       try {
           consumer.processMessage(parsed);
           session.commit();   // removes message from AQ
       } catch (Exception e) {
           switch (ExceptionClassifier.classify(e)) {
               case RETRIABLE       -> session.rollback();
               case NON_RETRIABLE   -> { log.error("Poison: {}", e.getMessage(), e); session.commit(); }
               case UNKNOWN_TX_STATE -> { log.error("VERIFY DATA: {}", e.getMessage(), e); session.commit(); }
           }
       }
   }
   ```

4. **The dual-transaction pattern**: ScalarDB commits first, then AQ session commits. If the JVM crashes between the two, AQ redelivers the message and the Upsert handles it idempotently.

5. **Exception classification**: The generated `ExceptionClassifier.java` determines whether a failed message should be retried (`session.rollback()`) or removed as a poison message (`session.commit()`). See `aq-exception-handling-strategy.md` for the full taxonomy.
