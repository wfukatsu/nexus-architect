#!/usr/bin/env python3
"""Every governing file in the explain pattern catalogue really covers its pattern.

`/architect:explain` explains a pattern "as the rule states it" when a catalogue row names a
governing file, and as a general Concept when it names none. A row that names a file which never
mentions the pattern makes the skill present general knowledge as this toolkit's rule. Nine rows
shipped that way in 0.45.0 — every file existed, so nothing caught it. This checks the content:
each named file contains the pattern's own vocabulary.

A new row needs an entry in EXPECTED, so it cannot be added without saying what to look for.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CATALOGUE = ROOT / "skills" / "explain" / "reference" / "pattern-catalog.md"

# Row name -> {governing file: what that file must say}. Case-insensitive.
EXPECTED = {
    "Bounded Context / Context Map": {
        "rules/product/ddd-strategic.md": r"bounded context|context map",
        "skills/redesign/SKILL.md": r"bounded context|context map"},
    "Microservices (database per service)": {
        "skills/design-microservices/SKILL.md": r"microservice"},
    "Hexagonal / Ports and Adapters, Clean Architecture": {
        "skills/design-implementation/SKILL.md": r"clean|port",
        "rules/tdd-workflow.md": r"fake.{0,20}port"},
    "Layered (controller → service → repository)": {
        "skills/design-implementation/SKILL.md": r"controller / DTO / mapper / application-service"},
    "API Gateway / Backend for Frontend": {
        "skills/design-api/SKILL.md": r"gateway",
        "rules/product/api-led-connectivity.md": r"experience"},
    "API-led connectivity (System / Process / Experience)": {
        "rules/product/api-led-connectivity.md": r"experience"},
    "Contract-first API": {
        "rules/api-contract-fidelity.md": r"operationId",
        "rules/graphql-contract-fidelity.md": r"\.graphqls"},
    "Event-driven integration, Domain Events": {
        "skills/design-aggregate/SKILL.md": r"domain event catalog"},
    "Saga (orchestration or choreography), TCC": {
        "rules/scalardb-saga-patterns.md": r"orchestrat|choreograph"},
    "Two-phase commit across services": {
        "rules/scalardb-2pc-patterns.md": r"two-phase|2pc"},
    "Shared cluster / Global transaction": {
        "rules/scalardb-2pc-patterns.md": r"shared cluster|global transaction"},
    "Strangler Fig": {
        "skills/generate-characterization-tests/SKILL.md": r"strangl",
        "skills/design-microservices/SKILL.md": r"transformation plan"},
    "HTAP / analytics separation": {
        "skills/design-scalardb-analytics/SKILL.md": r"htap|spark"},
    "GitOps, immutable images": {
        "rules/okf-k8s-tf-bundle.md": r"argo|digest|cosign"},
    "Architecture Decision Records": {
        "rules/architecture-decision-records.md": r"madr"},
    "Aggregate (root, invariants, one transaction per command)": {
        "rules/aggregate-design.md": r"one command, one aggregate"},
    "Entity / Value Object": {
        "rules/aggregate-design.md": r"value object"},
    "Repository": {
        "rules/aggregate-design.md": r"repository"},
    "Domain Service / Application Service": {
        "skills/design-implementation/SKILL.md": r"domain service|application service"},
    "Factory, Specification": {
        "rules/aggregate-design.md": r"factory"},
    "State machine": {
        "rules/state-modeling.md": r"state [x×] event"},
    "Transaction boundary / Unit of Work": {
        "rules/scalardb-crud-patterns.md": r"commit",
        "rules/scalardb-jdbc-patterns.md": r"commit"},
    "Optimistic concurrency and retry": {
        "rules/scalardb-exception-handling.md": r"retry"},
    "Unknown-outcome handling": {
        "rules/scalardb-exception-handling.md": r"UnknownTransactionStatusException",
        "rules/api-error-standard.md": r"UnknownTransactionStatusException"},
    "Idempotency key": {
        "rules/api-contract-fidelity.md": r"idempoten",
        "rules/scalardb-saga-patterns.md": r"idempoten"},
    "Problem Details error responses": {
        "rules/api-error-standard.md": r"9457"},
    "DTO mapping and validation at the edge": {
        "skills/design-implementation/SKILL.md": r"request dto",
        "rules/api-contract-fidelity.md": r"validation"},
    "DataLoader batching": {
        "rules/graphql-security-checks.md": r"dataloader"},
    "Tenant isolation": {
        "rules/api-security-checks.md": r"tenant"},
    "Test-first (Red → Green → Refactor), ATDD": {
        "rules/tdd-workflow.md": r"atdd"},
    "Contract tests, characterization tests": {
        "rules/api-contract-fidelity.md": r"contract test",
        "skills/generate-characterization-tests/SKILL.md": r"characteri"},
    "Quality gate": {
        "rules/ai-code-quality-gate.md": r"eight"},
    "Atomic Design components, Storybook": {
        "rules/product/atomic-react-storybook.md": r"storybook"},
    "Design tokens (DTCG)": {
        "rules/product/design-system.md": r"dtcg"},
    "Transaction Script": {},
    "Anemic domain model": {},
    "God service / shared database": {
        "skills/evaluate-mmi/SKILL.md": r"god-class"},
    "Framework-owned repository": {
        "rules/aggregate-design.md": r"repository"},
    "Product Vision Board, PR-FAQ": {
        "rules/product/vision-frameworks.md": r"vision board"},
    "North Star Metric, input metrics, guardrails": {
        "rules/product/success-metrics.md": r"north star"},
    "TAM / SAM / SOM, Kano": {
        "skills/product/research-landscape/SKILL.md": r"\bTAM\b",
        "rules/product/positioning-kano-hook.md": r"kano"},
    "Lean Canvas, unit economics (LTV/CAC, payback)": {
        "rules/product/revenue-models.md": r"lean canvas"},
    "MoSCoW, RICE": {
        "rules/product/scope-prioritization.md": r"moscow"},
    "Riskiest assumption test, Go/No-Go gate": {
        "rules/product/assumption-validation.md": r"riskiest"},
    "Jobs-to-be-Done, proto-persona": {
        "rules/product/persona-jtbd.md": r"job"},
    "Customer journey map, Moments of Truth": {
        "rules/product/journey-mapping.md": r"moment"},
    "Positioning canvas, Fogg model, Hook model": {
        "rules/product/positioning-kano-hook.md": r"fogg"},
    "Acronym naming": {
        "rules/product/naming-frameworks.md": r"acronym"},
    "Domain Storytelling": {
        "skills/create-domain-story/SKILL.md": r"domain storytelling"},
    "EventStorming": {
        "rules/product/event-storming.md": r"eventstorming"},
    "Example Mapping": {
        "rules/product/example-mapping.md": r"example mapping"},
    "UI-to-domain derivation": {
        "rules/product/ui-to-domain.md": r"mock"},
    "SLI / SLO / SLA, error budget": {
        "rules/product/sla-nfr.md": r"error budget"},
    "Technology fitness (Adopt / Conditional / Reject)": {
        "rules/product/architecture-and-tech-fitness.md": r"adopt"},
    "Change propagation over a traceability graph": {
        "rules/product/adaptation-engine.md": r"traceability"},
}

failures = []
checks = 0


def check(ok, message):
    global checks
    checks += 1
    if not ok:
        failures.append(message)


def rows(text):
    """Yield (row name, governing cell) for every table that has a 'Governing file' column."""
    column = None
    for line in text.splitlines():
        if not line.startswith("|"):
            column = None
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]  # `\|` is a literal pipe
        if "Governing file" in cells:
            column = cells.index("Governing file")
            continue
        if column is None or set(line) <= set("|- "):
            continue
        yield cells[0], cells[column]


seen = set()
for name, cell in rows(CATALOGUE.read_text(encoding="utf-8")):
    seen.add(name)
    named = re.findall(r"`([^`]+\.md)`", cell)
    expected = EXPECTED.get(name)
    check(expected is not None, f"row '{name}': no entry in EXPECTED — say what its files must contain")
    if expected is None:
        continue
    check(set(named) == set(expected),
          f"row '{name}': names {sorted(named)}, EXPECTED lists {sorted(expected)}")
    if not named:
        check(cell.startswith("—"), f"row '{name}': no governing file, so the cell must be '—'")
    for rel in named:
        path = ROOT / rel
        check(path.is_file(), f"row '{name}': {rel} does not exist")
        if path.is_file() and rel in expected:
            check(re.search(expected[rel], path.read_text(encoding="utf-8"), re.I),
                  f"row '{name}': {rel} never says /{expected[rel]}/ — it does not cover the pattern")

check(seen == set(EXPECTED), f"EXPECTED names rows the catalogue lacks: {sorted(set(EXPECTED) - seen)}")

if failures:
    print(f"FAIL: {len(failures)} of {checks} checks")
    for message in failures:
        print(f"  - {message}")
    sys.exit(1)
print(f"PASS: {checks} checks over {len(seen)} catalogue rows")
