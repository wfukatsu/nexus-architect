---
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

## Dependency Versions

`build.gradle` and the `Dockerfile` pin versions, so follow @rules/dependency-versions.md before
writing them: resolve the current ScalarDB (edition-appropriate), Spring Boot, Java, and base-image
versions from their registries, pick the **stable** ones that are mutually compatible, and never copy
the illustrative numbers out of @rules/spring-boot-integration.md or
`@skills/common/references/code-patterns/` — those are dated examples. Present the version decision
table for confirmation per `--confirm-versions` / `--no-confirm-versions` /
`options.confirm_versions`, and record it in `work/version-decisions.json` plus the run summary —
`/architect:generate-docs` then picks the pins up from the emitted build files when it writes the
service docs, so do not hand-write a competing table inside its marked sections.

## Acceptance Criteria

- Fully compliant with patterns in @rules/scalardb-coding-patterns.md
- Applies configuration patterns from @rules/spring-boot-integration.md
- Proper handling of transaction exceptions (retry, rollback)
- Entities follow immutable design; value objects are immutable
- Every pinned version was looked up (not recalled), is a stable release, and is recorded in the
  version decision table — with the user's confirmation when that is the configured mode

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
| /architect:generate-docs | Downstream — run after generation to write the service READMEs and docs/ for the emitted scaffold |
