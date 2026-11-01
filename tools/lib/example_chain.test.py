#!/usr/bin/env python3
"""Contract test for `example_chain.py` — the DDD → BDD → TDD chain. A scratch project with every
link whole must pass with no error and no warning; each defect the module exists to catch is then
introduced on its own and must be reported under its code. Exit 1 on any failure."""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import example_chain as C  # noqa: E402

checks = failures = 0


def check(label, condition, detail=""):
    global checks, failures
    checks += 1
    if condition:
        print("  ok    %s" % label)
    else:
        failures += 1
        print("  FAIL  %s%s" % (label, (" — %s" % detail) if detail else ""))


MAP = """---
title: "Example Map: Place order"
schema_version: 1
skill: example-map
feature: FEAT-001
---

## Rules

| ID | Rule | Source | Examples |
|----|------|--------|----------|
| RULE-001 | An order has at least one line | data-model.md ENT-004 | EX-001, EX-002 |
| RULE-002 | Quantity is between 1 and 99 | scope-definition.md CON-002 | EX-003, EX-004 |

## Examples

| ID | Rule | Kind | Given | When | Then |
|----|------|------|-------|------|------|
| EX-001 | RULE-001 | positive | cart with one line | place order | order placed |
| EX-002 | RULE-001 | negative | empty cart | place order | rejected: order-empty |
| EX-003 | RULE-002 | positive | cart with quantity 99 | place order | order placed |
| EX-004 | RULE-002 | negative | cart with quantity 100 | place order | rejected: quantity-out-of-range |
"""

FEATURE = """# language: en
@service=order-service
Feature: Place an order

  Background:
    Given a customer is signed in

  @RULE-001
  Rule: An order has at least one line

    @EX-001 @example=AGG-001.INV-1.positive
    Scenario: an order with one line is placed
      When they place an order with one line
      Then the order is placed

    @EX-002 @example=AGG-001.INV-1.negative
    Scenario: an empty cart is rejected
      When they place an order with no lines
      Then the order is rejected

  @RULE-002
  Rule: Quantity is between 1 and 99

    @EX-003
    Scenario Outline: the boundary quantity is accepted
      When they order <qty> items
      Then the order is placed

      @EX-004
      Examples:
        | qty |
        | 99  |
"""

AGGREGATES = {"schema_version": 1, "aggregates": [{"id": "AGG-001", "invariants": [
    {"id": "INV-1", "statement": "at least one line",
     "examples": [{"kind": "positive"}, {"kind": "negative"}]},
    {"id": "INV-2", "statement": "quantity 1..99",
     "examples": [{"kind": "positive"}, {"kind": "negative"}]}]}]}

PROPERTIES = """| Invariant | Aggregate | Property |
|-----------|-----------|----------|
| INV-1 at least one line | AGG-001 | PT-001-INV1 |
| INV-2 quantity 1..99 | AGG-001 | PT-001-INV2 |
"""

COVERAGE = "Reached: RULE-001 (EX-001, EX-002), RULE-002 (EX-003, EX-004)\n"

GRAPH = {"schema_version": 1, "nodes": [
    {"id": "RULE-001", "upstream": ["FEAT-001"]}, {"id": "RULE-002", "upstream": ["FEAT-001"]},
    {"id": "EX-001", "upstream": ["RULE-001"]}, {"id": "EX-002", "upstream": ["RULE-001"]},
    {"id": "EX-003", "upstream": ["RULE-002"]}, {"id": "EX-004", "upstream": ["RULE-002"]}]}

GATE = {"schema_version": 1, "stages": [{"stage": "unit", "status": "passed", "test_first": {
    "units": {"test-first": 2, "test-after": 0, "refactor-only": 0, "exempt": 0},
    "outer_loop": "bdd:@EX-002", "outer_loop_went_red": True}}]}


def write(root, relative, content):
    path = os.path.join(root, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content if isinstance(content, str) else json.dumps(content))


def project(map_dir="reports/02_spec/examples", **overrides):
    files = {
        map_dir + "/example-map-feat-001.md": MAP,
        "reports/07_test-specs/bdd-scenarios/ordering.feature": FEATURE,
        "reports/03_design/aggregates/aggregate-manifest.json": AGGREGATES,
        "reports/07_test-specs/property-test-specs.md": PROPERTIES,
        "reports/07_test-specs/acceptance-test-coverage.md": COVERAGE,
        "work/traceability.json": GRAPH,
        "reports/09_verification/quality-gate.json": GATE,
    }
    files.update(overrides)
    root = tempfile.mkdtemp()
    for relative, content in files.items():
        if content is not None:
            write(root, relative, content)
    return root


def codes(root):
    result = C.check(root)
    return ({e["code"] for e in result.errors}, {w["code"] for w in result.warnings}, result)


def expect(label, code, warning=False, **overrides):
    root = project(**overrides)
    try:
        errors, warnings, result = codes(root)
        bucket = warnings if warning else errors
        check(label, code in bucket, {"errors": result.errors, "warnings": result.warnings})
        if warning:
            check("  …and it is a warning, not an error", not result.errors, result.errors)
    finally:
        shutil.rmtree(root, ignore_errors=True)


print("A whole chain passes")
for location in C.MAP_DIRS:
    root = project(map_dir=location.replace(os.sep, "/"))
    try:
        errors, warnings, result = codes(root)
        check("no error, no warning with the map under %s" % location, not errors and not warnings,
              result.errors + result.warnings)
        s = result.summary
        check("  …and it followed every link", s["rules_in_gherkin"] == 2 and s["examples_in_gherkin"] == 4
              and s["invariants_with_property"] == 2, s)
    finally:
        shutil.rmtree(root, ignore_errors=True)

print("Example maps")
expect("an ID defined twice", "CHAIN-101", **{
    "reports/00_requirements/examples/example-map-fr-001.md": MAP})
expect("an example naming no rule", "CHAIN-102", **{
    "reports/02_spec/examples/example-map-feat-001.md": MAP.replace("| EX-004 | RULE-002 |", "| EX-004 | — |")})
expect("an example citing an undefined rule", "CHAIN-103", **{
    "reports/02_spec/examples/example-map-feat-001.md": MAP.replace("| EX-004 | RULE-002 |", "| EX-004 | RULE-009 |")})
one_sided = MAP.replace("| EX-004 | RULE-002 | negative |", "| EX-004 | RULE-002 | positive |")
expect("a rule with no negative example and no OQ-", "CHAIN-104", **{
    "reports/02_spec/examples/example-map-feat-001.md": one_sided})
expect("the same rule citing an OQ- is only a warning", "CHAIN-104", warning=True, **{
    "reports/02_spec/examples/example-map-feat-001.md": one_sided.replace(
        "CON-002 | EX-003, EX-004 |", "CON-002 | EX-003, EX-004, OQ-007 |")})

print("Traceability graph")
expect("no graph is a warning", "CHAIN-110", warning=True, **{"work/traceability.json": None})
expect("a RULE- missing from the graph", "CHAIN-111", **{"work/traceability.json": {
    "schema_version": 1, "nodes": [n for n in GRAPH["nodes"] if n["id"] != "RULE-002"]}})
expect("an EX- whose upstream lacks its rule", "CHAIN-112", **{"work/traceability.json": {
    "schema_version": 1, "nodes": [dict(n, upstream=["FEAT-001"]) if n["id"] == "EX-003" else n
                                   for n in GRAPH["nodes"]]}})

print("Gherkin")
feature = "reports/07_test-specs/bdd-scenarios/ordering.feature"
expect("a rule with no Rule: block", "CHAIN-121", **{feature: FEATURE.replace("  @RULE-002\n", "")})
expect("an example with no scenario", "CHAIN-122", **{feature: FEATURE.replace("@EX-003\n", "\n")})
expect("a tag naming an ID no map defines", "CHAIN-123", **{feature: FEATURE.replace("@EX-003", "@EX-003 @EX-099")})
expect("an example under the wrong rule", "CHAIN-124", **{
    feature: FEATURE.replace("@EX-002 @example", "@EX-003 @example").replace("    @EX-003\n", "    @EX-002\n")})
expect("an invariant tag naming no declared invariant", "CHAIN-125", **{
    feature: FEATURE.replace("AGG-001.INV-1.negative", "AGG-001.INV-7.negative")})
expect("a malformed invariant tag", "CHAIN-125", **{
    feature: FEATURE.replace("@example=AGG-001.INV-1.negative", "@example=INV-1")})
expect("scenarios with no example map are a warning", "CHAIN-126", warning=True, **{
    "reports/02_spec/examples/example-map-feat-001.md": None, "work/traceability.json": None,
    feature: FEATURE.replace("@RULE-001", "").replace("@RULE-002", "").replace("@EX-001", "")
    .replace("@EX-002", "").replace("@EX-003", "").replace("@EX-004", ""),
    "reports/09_verification/quality-gate.json": None})

print("Property tests, acceptance record, quality gate")
expect("an invariant no property names", "CHAIN-131", **{
    "reports/07_test-specs/property-test-specs.md": PROPERTIES.replace("| INV-2 quantity 1..99 | AGG-001 | PT-001-INV2 |\n", "")})
root = project(**{"reports/07_test-specs/property-test-specs.md": "| INV-10 | AGG-001 |\n| INV-2 | AGG-001 |\n"})
try:
    errors, _, result = codes(root)
    check("INV-10 does not count as INV-1", any("INV-1 " in e["message"] for e in result.errors), result.errors)
finally:
    shutil.rmtree(root, ignore_errors=True)
expect("an ID the acceptance record does not mention", "CHAIN-141", warning=True, **{
    "reports/07_test-specs/acceptance-test-coverage.md": COVERAGE.replace(", EX-004", "")})
no_record = {"schema_version": 1, "stages": [{"stage": "unit", "status": "passed"}]}
expect("a unit stage with no test_first record", "CHAIN-151", **{
    "reports/09_verification/quality-gate.json": no_record})
bare = {"schema_version": 1, "stages": [{"stage": "unit", "test_first": {"status": "not-applicable"}}]}
expect("not-applicable without its reason", "CHAIN-151", **{"reports/09_verification/quality-gate.json": bare})
na = {"schema_version": 1, "stages": [{"stage": "unit", "test_first": {
    "status": "not-applicable", "reason": "generated/ scaffolding, no work item"}}]}
root = project(**{"reports/09_verification/quality-gate.json": na})
try:
    errors, _, result = codes(root)
    check("not-applicable with a reason is accepted", "CHAIN-151" not in errors, result.errors)
finally:
    shutil.rmtree(root, ignore_errors=True)
stray = json.loads(json.dumps(GATE))
stray["stages"][0]["test_first"]["outer_loop"] = "bdd:@EX-050"
expect("an outer loop naming no scenario", "CHAIN-152", **{"reports/09_verification/quality-gate.json": stray})

print("CLI")
root = project()
try:
    ok = subprocess.run([sys.executable, os.path.join(HERE, "example_chain.py"), root], capture_output=True, text=True)
    check("a whole chain exits 0", ok.returncode == 0, ok.stdout + ok.stderr)
    write(root, feature, FEATURE.replace("  @RULE-002\n", ""))
    bad = subprocess.run([sys.executable, os.path.join(HERE, "example_chain.py"), root, "--json"],
                         capture_output=True, text=True)
    check("a broken chain exits 1", bad.returncode == 1, bad.stdout + bad.stderr)
    check("  …and --json is parseable with the error in it",
          any(e["code"] == "CHAIN-121" for e in json.loads(bad.stdout)["errors"]), bad.stdout)
    usage = subprocess.run([sys.executable, os.path.join(HERE, "example_chain.py")], capture_output=True, text=True)
    check("no project is a usage error (exit 2)", usage.returncode == 2, usage.returncode)
finally:
    shutil.rmtree(root, ignore_errors=True)
empty = tempfile.mkdtemp()
try:
    errors, warnings, result = codes(empty)
    check("an empty project has nothing to break", not errors and not warnings, result.errors + result.warnings)
finally:
    shutil.rmtree(empty, ignore_errors=True)

print()
print("%d check(s), %d failure(s)" % (checks, failures))
sys.exit(1 if failures else 0)
