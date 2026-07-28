---
description: Generate docker-compose.yml and setup commands for a local ScalarDB development environment. Use when the user wants to run or test ScalarDB locally, set up a dev backend (PostgreSQL/MySQL/Cassandra/DynamoDB local), or asks "how do I try ScalarDB on my machine".
model: sonnet
user_invocable: true
---

# /scalardb:local-env — Local Environment Setup

## Instructions

You are a ScalarDB local environment setup assistant. Generate Docker Compose files and setup commands for local development.

**Knowledge grounding**: when the answer depends on version-specific behavior (API signatures, config keys, exception retryability, edition-gated features), consult the version-pinned OKF knowledge bundle per `rules/okf-knowledge-bundle.md` and cite the concept's `resource` URL — do not rely on memory.

## Interactive Flow

### Step 1: Database Backend
Ask: "Which database backend(s) do you need?"
- MySQL
- PostgreSQL
- Cassandra
- DynamoDB Local
- Multiple (for multi-storage or 2PC testing)

### Step 2: Generate Files

Generate:
1. **`docker-compose.yml`** — Database service(s)
2. **Schema loading commands**
3. **Troubleshooting tips** for common issues

## Dependency Versions

The image tags and JAR versions below are a **dated example** (snapshot: 2026-07), not the current
stable releases. Before emitting a compose file or a download command, resolve each one per
`rules/dependency-versions.md`: read the registry's tag list
(`curl -s "https://hub.docker.com/v2/repositories/<ns>/<image>/tags?page_size=25&ordering=last_updated"`,
`library` as `<ns>` for official images) and the ScalarDB release list
(`gh release list -R scalar-labs/scalardb`), pick the newest **stable** tag of a supported line
(`endoflife.date` for the database's support window), and **never leave a moving `:latest` tag in a
compose file** — resolve it to a concrete version so the environment is reproducible. The
schema-loader JAR must match the ScalarDB version the application pins. Confirm the chosen set with
the user unless the project opted out (`options.confirm_versions` / `--no-confirm-versions`).

## Docker Compose Templates

### MySQL

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: mysql
    ports:
      - "3306:3306"
    volumes:
      - mysql-data:/var/lib/mysql
    healthcheck:
      test: mysqladmin ping -h localhost -u root -pmysql
      interval: 5s
      timeout: 10s
      retries: 10

volumes:
  mysql-data:
```

Properties:
```properties
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:mysql://localhost:3306/
scalar.db.username=root
scalar.db.password=mysql
```

### PostgreSQL

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: pg_isready -U postgres
      interval: 5s
      timeout: 10s
      retries: 10

volumes:
  postgres-data:
```

Properties:
```properties
scalar.db.storage=jdbc
scalar.db.contact_points=jdbc:postgresql://localhost:5432/
scalar.db.username=postgres
scalar.db.password=postgres
```

### Cassandra

```yaml
services:
  cassandra:
    image: cassandra:3.11
    ports:
      - "9042:9042"
    environment:
      CASSANDRA_CLUSTER_NAME: test
    volumes:
      - cassandra-data:/var/lib/cassandra
    healthcheck:
      test: cqlsh -e 'describe cluster'
      interval: 10s
      timeout: 10s
      retries: 20

volumes:
  cassandra-data:
```

Properties:
```properties
scalar.db.storage=cassandra
scalar.db.contact_points=localhost
scalar.db.username=cassandra
scalar.db.password=cassandra
```

**Note**: Cassandra takes 30-60 seconds to start. Wait for the healthcheck to pass before loading schemas.

### DynamoDB Local

```yaml
services:
  dynamodb:
    image: amazon/dynamodb-local:<resolved-tag>   # resolve a concrete tag; never :latest
    ports:
      - "8000:8000"
    command: -jar DynamoDBLocal.jar -sharedDb
```

Properties:
```properties
scalar.db.storage=dynamo
scalar.db.contact_points=sample
scalar.db.username=sample
scalar.db.password=sample
scalar.db.dynamo.endpoint_override=http://localhost:8000
```

### Multi-Storage (MySQL + Cassandra)

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: mysql
    ports:
      - "3306:3306"
    healthcheck:
      test: mysqladmin ping -h localhost -u root -pmysql
      interval: 5s
      timeout: 10s
      retries: 10

  cassandra:
    image: cassandra:3.11
    ports:
      - "9042:9042"
    environment:
      CASSANDRA_CLUSTER_NAME: test
    healthcheck:
      test: cqlsh -e 'describe cluster'
      interval: 10s
      timeout: 10s
      retries: 20

networks:
  default:
    name: sample-network
```

## Schema Loading Commands

Resolve `<version>` first (`gh release list -R scalar-labs/scalardb --limit 10` → newest non-prerelease)
and use the same version the application pins:

```bash
# Download schema loader (if not already available)
curl -OL https://github.com/scalar-labs/scalardb/releases/download/v<version>/scalardb-schema-loader-<version>.jar

# Create tables
java -jar scalardb-schema-loader-<version>.jar \
  --config database.properties -f schema.json --coordinator

# Delete tables (for cleanup)
java -jar scalardb-schema-loader-<version>.jar \
  --config database.properties -f schema.json -D --coordinator
```

## Troubleshooting

### Database not ready
- Cassandra: Wait 30-60 seconds after container starts
- MySQL: Check healthcheck with `docker-compose ps`
- Use `docker-compose logs <service>` to check for errors

### Connection refused
- Verify port mapping in docker-compose.yml
- Verify contact_points in properties file
- For MySQL: use `jdbc:mysql://localhost:3306/` (with trailing slash)

### Schema loading fails
- Ensure coordinator tables are created: `--coordinator` flag
- Verify database is running: `docker-compose ps`
- Check credentials match between docker-compose and properties file

### Port conflict
- Change the host port mapping: `"3307:3306"` and update contact_points accordingly
