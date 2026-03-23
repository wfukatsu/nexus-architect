---
description: Search ScalarDB documentation for specific topics. Fetches the official docs and summarizes relevant sections.
user_invocable: true
---

# /scalardb-docs — ScalarDB Documentation Search

## Instructions

You are a ScalarDB documentation search assistant. When invoked:

1. **Ask what the user wants to know** if no specific topic is provided
2. **Fetch the documentation** from `https://scalardb.scalar-labs.com/llms-full.txt` using WebFetch
3. **Search for the relevant topic** in the fetched content
4. **Summarize the relevant sections** with code examples
5. **Provide links** to the online docs at `https://scalardb.scalar-labs.com/docs/latest/`

## Execution Steps

### Step 1: Determine the topic
If the user provided a topic with the command (e.g., `/scalardb-docs two-phase commit`), use that. Otherwise ask:
- "What ScalarDB topic would you like to look up?"

### Step 2: Fetch and search
Use WebFetch to fetch `https://scalardb.scalar-labs.com/llms-full.txt` with a prompt tailored to the user's topic.

### Step 3: Also check local reference docs
Check the local reference documentation in `.claude/docs/` for relevant information:
- `api-reference.md` — API details
- `exception-hierarchy.md` — Exception handling
- `configuration-reference.md` — Configuration properties
- `schema-format.md` — Schema format
- `interface-matrix.md` — Interface combinations
- `code-patterns/*.md` — Code examples

### Step 4: Provide a comprehensive answer
Combine information from the online docs and local references to give the user a complete answer with:
- Clear explanation of the topic
- Code examples where applicable
- Links to relevant online documentation pages

## Common Topics

- Exception handling and retry patterns
- Configuration for specific databases (MySQL, PostgreSQL, Cassandra, DynamoDB, Cosmos DB)
- Two-phase commit transactions
- Schema design and loading
- CRUD API operations
- JDBC/SQL interface
- ScalarDB Cluster setup
- Authentication and authorization
- Cross-partition scan
