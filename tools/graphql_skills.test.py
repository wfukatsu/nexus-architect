#!/usr/bin/env python3
"""Static contract checks for the Spring for GraphQL skill chain."""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "lib"))
import pipeline_status_data as pipeline  # noqa: E402

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
          and "UnknownTransactionStatusException" in generator_skill)
    normalized_generator = " ".join(generator_skill.lower().split())
    check("generator merges rather than truncates protocol maps",
          "preserve other protocol entries" in normalized_generator
          and "protocol\": \"graphql" in generator_skill)
    check("no skill template placeholders remain",
          "TODO" not in design_skill and "TODO" not in generator_skill)

    print("%d failure(s)" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
