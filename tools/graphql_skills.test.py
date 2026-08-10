#!/usr/bin/env python3
"""Static contract checks for the Spring for GraphQL skill chain."""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "lib"))
import pipeline_status_data as pipeline  # noqa: E402
from api_style_decisions import validate_document  # noqa: E402

failures = 0


def check(label, condition, detail=""):
    global failures
    print("  [%s] %s%s" % (
        "ok" if condition else "FAIL",
        label,
        " — " + str(detail) if detail and not condition else "",
    ))
    if not condition:
        failures += 1


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def main():
    print("GraphQL skill discovery and dependency contract")
    phases = pipeline.load_phase_manifest("architect")
    design = phases["design-graphql"]
    generator = phases["generate-graphql-code"]
    check("design is conditionally downstream of design-api",
          design["depends_on"] == ["design-api"]
          and design["conditions"] == ["api_style_graphql"], design)
    check("generator waits for implementation and GraphQL design",
          generator["depends_on"] == ["design-implementation", "design-graphql"],
          generator)
    check("generator is shown in the codegen view",
          "generate-graphql-code" in pipeline.CODEGEN_PHASES["architect"])

    marketplace = json.loads(read(".claude-plugin/marketplace.json"))
    architect = next(item for item in marketplace["plugins"]
                     if item["name"] == "architect")
    check("Claude plugin exposes both skills",
          {"./skills/design-graphql", "./skills/generate-graphql-code"}
          <= set(architect["skills"]))

    print("GraphQL design safety contract")
    design_skill = read("skills/design-graphql/SKILL.md")
    generator_skill = read("skills/generate-graphql-code/SKILL.md")
    selection_rule = read("rules/api-style-selection.md")
    contract_rule = read("rules/graphql-contract-fidelity.md")
    security_rule = read("rules/graphql-security-checks.md")
    error_rule = read("rules/api-error-standard.md")
    design_api_skill = read("skills/design-api/SKILL.md")
    security_review = read("skills/review-api-security/SKILL.md")

    check("database does not select GraphQL",
          "Never select GraphQL merely because ScalarDB is selected" in design_skill
          and "The database does not select the API style" in selection_rule)
    check("Spring facade and native ScalarDB GraphQL stay distinct",
          "Spring for GraphQL application API" in selection_rule
          and "ScalarDB native GraphQL interface" in selection_rule)
    check("field coordinate is the stable resolver join key",
          "<parentType>.<fieldName>" in design_skill
          and "<parentType>.<fieldName>" in contract_rule)
    check("tenant-safe loading is mandatory",
          "DataLoader" in design_skill and "tenant" in security_rule
          and "cache" in security_rule)
    check("query denial-of-service budgets are mandatory",
          all(term in security_rule for term in
              ("depth", "complexity", "aliases", "page size", "timeout")))
    check("unknown transaction status has a dedicated path",
          "UnknownTransactionStatusException" in design_skill
          and "UnknownTransactionStatusException" in generator_skill
          and "GraphQL execution override" in error_rule)
    check("unknown-status execution contract separates retry from reconcile",
          all(term in error_rule for term in
              ('HTTP 200', 'retryable: true', 'retry_after_ms',
               'idempotency_key_reuse: "required"', 'retryable: false',
               'reconcile_required: true', 'raw transaction ID')))
    required_native_fields = (
        "graphql_provider", "native_exposure", "approval", "pinned_product",
        "pinned_release", "contracted_edition", "control_evidence", "rationale")
    check("ScalarDB native exposure uses a structured decision contract",
          all(term in selection_rule and term in design_api_skill
              for term in required_native_fields))
    check("native exposure without approval and controls is critical",
          "critical" in security_review.lower()
          and "approved:<decision-id>" in security_review
          and all(control in security_review for control in
                  ("authentication", "authorization", "audit", "query limits",
                   "network isolation")))
    spring_surface = {"surfaces": [{
        "surface_id": "customer-api", "scalardb_backed": True,
        "graphql_provider": "spring-for-graphql", "native_exposure": "none",
        "approval": "not-required", "pinned_product": "ScalarDB",
        "pinned_release": "verified-release", "contracted_edition": "verified-edition",
        "control_evidence": {}, "rationale": "application security boundary",
    }]}
    check("Spring facade decision fixture validates",
          validate_document(spring_surface) == [], validate_document(spring_surface))
    approved_native = {"surfaces": [{
        "surface_id": "admin-api", "scalardb_backed": True,
        "graphql_provider": "scalardb-native", "native_exposure": "internal",
        "approval": "approved:ADR-042", "pinned_product": "ScalarDB",
        "pinned_release": "verified-release", "contracted_edition": "verified-edition",
        "control_evidence": {
            "authentication": "SEC-1", "authorization": "SEC-2", "audit": "SEC-3",
            "query_limits": "SEC-4", "network_isolation": "SEC-5"},
        "rationale": "approved internal administration",
    }]}
    check("approved internal native decision fixture validates",
          validate_document(approved_native) == [], validate_document(approved_native))
    unsafe_external = {"surfaces": [{
        "surface_id": "public-api", "scalardb_backed": True,
        "graphql_provider": "scalardb-native", "native_exposure": "external",
        "approval": "not-required", "pinned_product": "ScalarDB",
        "pinned_release": "verified-release", "contracted_edition": "verified-edition",
        "control_evidence": {}, "rationale": "convenience",
    }]}
    unsafe_errors = validate_document(unsafe_external)
    check("unapproved external native decision fixture is rejected",
          any("approval" in error for error in unsafe_errors)
          and all(any(control in error for error in unsafe_errors)
                  for control in ("authentication", "authorization", "audit",
                                  "query_limits", "network_isolation")), unsafe_errors)
    normalized_generator = " ".join(generator_skill.lower().split())
    check("generator merges rather than truncates protocol maps",
          "preserve other protocol entries" in normalized_generator
          and "protocol\": \"graphql" in generator_skill)
    check("generator owns unique completion evidence",
          "graphql-code-generation.md" in generator_skill
          and generator["outputs"] == [
              "reports/06_implementation/graphql-code-generation.md"])
    check("no skill template placeholders remain",
          "TODO" not in design_skill and "TODO" not in generator_skill)

    print("%d failure(s)" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
