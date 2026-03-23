---
name: generate-scalardb-code
description: |
  Generate Spring Boot + ScalarDB Java code from design specifications.
  Invoked via /architect:generate-scalardb-code. Dedicated to projects using ScalarDB.
model: opus
user_invocable: true
---

# ScalarDB Code Generation

## Desired Outcome

Generate per-service Java code from design and implementation specifications:
- Entity classes (ScalarDB Result mapping)
- Repository implementations (Get/Put/Scan/Delete operations)
- Domain services (including transaction management)
- Spring Boot configuration (scalardb.properties, Config classes)
- Gradle build configuration (build.gradle)
- Dockerfile

## Acceptance Criteria

- Fully compliant with patterns in @rules/scalardb-coding-patterns.md
- Applies configuration patterns from @rules/spring-boot-integration.md
- Proper handling of transaction exceptions (retry, rollback)
- Entities follow immutable design; value objects are immutable

## Prerequisites

| File | Required/Recommended | Source |
|------|---------------------|--------|
| reports/06_implementation/ | Required | /architect:design-implementation |
| reports/03_design/scalardb-schema.md | Required | /architect:design-scalardb |
| reports/07_test-specs/ | Recommended | /architect:generate-test-specs |

## Output

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

| File | Content |
|------|---------|
| `generated/{service}/src/main/java/` | Java source code |
| `generated/{service}/build.gradle` | Build configuration |
| `generated/{service}/Dockerfile` | Container definition |
| `generated/{service}/scalardb.properties` | ScalarDB configuration |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:design-implementation | Input source |
| /architect:design-scalardb | Input source |
| /architect:review-scalardb | Review target (--mode=code) |
