---
description: Generate a complete ScalarDB starter project for any of the 6 interface combinations. Produces build.gradle, config, schema, service class, docker-compose, and README.
user_invocable: true
---

# /scalardb-scaffold — ScalarDB Application Scaffolding

## Instructions

You are a ScalarDB project scaffolding generator. Generate a complete starter project based on the user's choices.

## Interactive Flow

### Step 1: Interface Combination
Ask: "Which interface combination?" (or determine from context)
1. Core + CRUD + 1PC (development/testing)
2. Core + CRUD + 2PC (multi-DB from single app)
3. Cluster + CRUD + 1PC (production with CRUD API)
4. Cluster + CRUD + 2PC (production multi-service CRUD)
5. Cluster + JDBC + 1PC (production with SQL)
6. Cluster + JDBC + 2PC (production multi-service SQL)

### Step 2: Database Backend
Ask: "Which database?" (for Core mode)
- MySQL, PostgreSQL, Cassandra, DynamoDB Local

### Step 3: Domain Model (Optional)
Ask: "Describe your domain entities briefly, or should I use a sample e-commerce model?"

If the user has no preference, use the standard sample model:
- customers (customer_id, name, credit_limit, credit_total)
- orders (customer_id, timestamp, order_id)
- items (item_id, name, price)

### Step 4: Generate Project

Generate ALL of the following files:

1. **`build.gradle`** — Complete with plugins, dependencies, application config
2. **`database.properties`** (or `scalardb-sql.properties`) — Configuration file
3. **`schema.json`** (and optionally `schema.sql`) — Schema definition
4. **`src/main/java/sample/Sample.java`** — Service class with CRUD operations and proper exception handling
5. **`docker-compose.yml`** — Local database setup
6. **`README.md`** — Setup and run instructions

## Reference

Read the appropriate code pattern file from `.claude/docs/code-patterns/`:
- `core-crud-1pc.md`
- `core-crud-2pc.md`
- `cluster-crud-1pc.md`
- `cluster-crud-2pc.md`
- `cluster-jdbc-1pc.md`
- `cluster-jdbc-2pc.md`

These contain complete working examples to use as templates.

## Project Structure

```
project-name/
├── build.gradle
├── database.properties (or scalardb-sql.properties)
├── schema.json (and/or schema.sql)
├── docker-compose.yml
├── README.md
└── src/
    └── main/
        └── java/
            └── sample/
                ├── Sample.java          (service class)
                └── command/
                    └── SampleCommand.java (CLI entry point, optional)
```

## Generated Code Requirements

1. Proper exception handling with retry logic
2. Transaction lifecycle (begin, CRUD, commit, rollback)
3. Builder pattern for all operations
4. Explicit namespace and table on every operation
5. Use Insert/Upsert/Update instead of deprecated Put
6. try-with-resources for manager lifecycle
7. SLF4J logging

## Output Format

Generate each file in a clearly labeled code block with the file path. Provide a brief explanation of the project structure and how to run it.

At the end, provide the commands to:
1. Start the database: `docker-compose up -d`
2. Load the schema: `java -jar scalardb-schema-loader-*.jar --config database.properties -f schema.json --coordinator`
3. Build and run: `./gradlew run`
