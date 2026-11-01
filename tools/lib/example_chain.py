"""Check that the DDD → BDD → TDD chain is unbroken in a project.

Each link of the chain is written by a different skill, and each skill reads the previous link
when it exists and quietly falls back to something else when it does not. A chain that broke
therefore looks like a chain that worked: the scenarios exist, the tests pass, and nothing says
that the scenarios were invented from a manifest instead of the examples the domain expert agreed
to, or that an invariant never reached a property test. This module follows every ID from where
it is minted to where it must arrive and reports each place the trail stops.

| Link | Written by | Checked here |
|------|------------|--------------|
| Example map (`RULE-`, `EX-`) | `/product:example-map`, `/architect:define-requirements` | IDs unique, every example names an existing rule, every rule has a positive and a negative example or cites the `OQ-` that explains why not |
| Traceability graph | the same skills | every `RULE-` / `EX-` is a node; an `EX-` node's `upstream` holds its rule |
| Gherkin (`reports/07_test-specs/bdd-scenarios/`) | `/architect:generate-test-specs` | every `RULE-` tags a `Rule:` block, every `EX-` tags a scenario under its rule, no tag names an ID no map defines, every `@example=<AGG>.<INV>.<kind>` names a declared invariant example |
| Property-test specs | `/architect:generate-test-specs` | every invariant of the aggregate manifest is named (`AGG-…` and `INV-…` on one line) |
| Acceptance coverage record | `/architect:generate-acceptance-tests` | every `RULE-` / `EX-` the scenarios carry is accounted for (warning: out-of-scope features are listed by count) |
| Quality gate | `/architect:verify-implementation --gate` | the unit stage carries a `test_first` record — units, or `not-applicable` with a reason — and its outer loop names a scenario that exists |

A link whose artifact is absent is not checked: a project that has not reached test specs has no
Gherkin to follow. The one exception is reported as a warning — scenarios exist but no example map
does, so nothing the scenarios assert was agreed with anyone.

Usage:  python3 tools/lib/example_chain.py <project_dir> [--json]   (exit 1 on any error)
"""

import glob
import json
import os
import re
import sys

MAP_DIRS = (os.path.join("reports", "02_spec", "examples"),
            os.path.join("reports", "00_requirements", "examples"))
FEATURE_DIR = os.path.join("reports", "07_test-specs", "bdd-scenarios")
AGGREGATES = os.path.join("reports", "03_design", "aggregates", "aggregate-manifest.json")
PROPERTY_SPECS = os.path.join("reports", "07_test-specs", "property-test-specs.md")
ACCEPTANCE = os.path.join("reports", "07_test-specs", "acceptance-test-coverage.md")
GRAPH = os.path.join("work", "traceability.json")
GATE = os.path.join("reports", "09_verification", "quality-gate.json")

ID_RE = re.compile(r"^(RULE|EX)-\d+$")
RULE_TOKEN = re.compile(r"\bRULE-\d+\b")
EX_TOKEN = re.compile(r"\bEX-\d+\b")
OQ_TOKEN = re.compile(r"\bOQ-\d+\b")
KINDS = ("positive", "negative")
EXAMPLE_TAG = re.compile(r"^@example=(AGG-\d+)\.(INV-\d+)\.(positive|negative)$")
SCENARIO_KEYWORDS = ("Scenario:", "Scenario Outline:", "Scenario Template:", "Example:")


class Result:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.summary = {}

    def error(self, code, message):
        self.errors.append({"code": code, "message": message})

    def warn(self, code, message):
        self.warnings.append({"code": code, "message": message})


def _read(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


def _cells(line):
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    return [cell.strip().strip("`*") for cell in stripped.strip("|").split("|")]


# --- Example maps ----------------------------------------------------------------------------

def load_maps(project_dir, result):
    """{'rules': {id: {...}}, 'examples': {id: {...}}, 'files': [...]} over both map locations."""
    rules, examples, files = {}, {}, []
    for directory in MAP_DIRS:
        for path in sorted(glob.glob(os.path.join(project_dir, directory, "example-map-*.md"))):
            relative = os.path.relpath(path, project_dir)
            text = _read(path)
            if text is None:
                result.error("CHAIN-100", "%s: unreadable" % relative)
                continue
            files.append(relative)
            for number, line in enumerate(text.splitlines(), 1):
                cells = _cells(line)
                if not cells or not ID_RE.match(cells[0]):
                    continue
                ident = cells[0]
                where = "%s:%d" % (relative, number)
                table = rules if ident.startswith("RULE-") else examples
                if ident in table:
                    result.error("CHAIN-101", "%s: %s is defined twice (also %s) — one ID, one meaning"
                                 % (where, ident, table[ident]["where"]))
                    continue
                if ident.startswith("RULE-"):
                    rest = " ".join(cells[1:])
                    rules[ident] = {"where": where, "cited_oq": OQ_TOKEN.findall(rest)}
                else:
                    cited = RULE_TOKEN.findall(cells[1]) if len(cells) > 1 else []
                    kind = cells[2] if len(cells) > 2 and cells[2] in KINDS else None
                    examples[ident] = {"where": where, "rules": cited, "kind": kind}
    return {"rules": rules, "examples": examples, "files": files}


def check_maps(maps, result):
    rules, examples = maps["rules"], maps["examples"]
    sides = {rule: set() for rule in rules}
    for ident, example in sorted(examples.items()):
        if not example["rules"]:
            result.error("CHAIN-102", "%s: %s names no rule — an example that illustrates no rule "
                         "is an unwritten rule" % (example["where"], ident))
        for rule in example["rules"]:
            if rule not in rules:
                result.error("CHAIN-103", "%s: %s cites %s, which no example map defines"
                             % (example["where"], ident, rule))
            elif example["kind"] and len(example["rules"]) == 1:
                sides[rule].add(example["kind"])
    for rule, seen in sorted(sides.items()):
        missing = [kind for kind in KINDS if kind not in seen]
        if not missing:
            continue
        message = "%s: %s has no %s example" % (rules[rule]["where"], rule, " or ".join(missing))
        if rules[rule]["cited_oq"]:
            result.warn("CHAIN-104", "%s (open: %s)" % (message, ", ".join(rules[rule]["cited_oq"])))
        else:
            result.error("CHAIN-104", message + " and cites no OQ- saying why — the boundary the "
                         "rule draws was never located")


def check_graph(project_dir, maps, result):
    path = os.path.join(project_dir, GRAPH)
    if not maps["rules"] and not maps["examples"]:
        return
    if not os.path.isfile(path):
        result.warn("CHAIN-110", "%s is absent — the RULE-/EX- nodes cannot be followed (a staged "
                    "reference set carries no work/; a real run always writes the graph)" % GRAPH)
        return
    try:
        graph = json.loads(_read(path) or "")
    except ValueError as exc:
        result.error("CHAIN-110", "%s: unreadable — %s" % (GRAPH, exc))
        return
    nodes = {}
    for node in graph.get("nodes", []) if isinstance(graph, dict) else []:
        if isinstance(node, dict) and isinstance(node.get("id"), str):
            nodes[node["id"]] = node
    for ident in sorted(list(maps["rules"]) + list(maps["examples"])):
        if ident not in nodes:
            result.error("CHAIN-111", "%s is in an example map but not a node in %s" % (ident, GRAPH))
    for ident, example in sorted(maps["examples"].items()):
        node = nodes.get(ident)
        upstream = node.get("upstream") if node else None
        if node and isinstance(upstream, list):
            for rule in example["rules"]:
                if rule not in upstream:
                    result.error("CHAIN-112", "%s node's upstream lacks %s" % (ident, rule))


# --- Gherkin ---------------------------------------------------------------------------------

def load_features(project_dir, result):
    """[{'file', 'line', 'name', 'tags', 'rule_tags'}] — one entry per scenario."""
    scenarios = []
    files = sorted(glob.glob(os.path.join(project_dir, FEATURE_DIR, "**", "*.feature"), recursive=True))
    for path in files:
        relative = os.path.relpath(path, project_dir)
        text = _read(path)
        if text is None:
            result.error("CHAIN-120", "%s: unreadable" % relative)
            continue
        pending, rule_tags = [], []
        for number, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("@"):
                pending.extend(token for token in line.split() if token.startswith("@"))
                continue
            if line.startswith("Feature:"):
                rule_tags, pending = [], []
            elif line.startswith("Rule:"):
                rule_tags, pending = pending, []
            elif line.startswith(SCENARIO_KEYWORDS):
                scenarios.append({"file": relative, "line": number, "name": line,
                                  "tags": pending, "rule_tags": rule_tags})
                pending = []
            elif line.startswith(("Examples:", "Scenarios:")):
                if scenarios and scenarios[-1]["file"] == relative:
                    scenarios[-1]["tags"] = scenarios[-1]["tags"] + pending
                pending = []
            else:
                pending = [] if not line.startswith("|") else pending
    return files, scenarios


def check_features(project_dir, maps, scenarios, result):
    rules, examples = maps["rules"], maps["examples"]
    tagged_rules, tagged_examples = set(), set()
    for scenario in scenarios:
        where = "%s:%d" % (scenario["file"], scenario["line"])
        own = [tag[1:] for tag in scenario["tags"]]
        enclosing = [tag[1:] for tag in scenario["rule_tags"]]
        for ident in own + enclosing:
            if ident.startswith("RULE-") and RULE_TOKEN.fullmatch(ident):
                tagged_rules.add(ident)
                if ident not in rules:
                    result.error("CHAIN-123", "%s: @%s names a rule no example map defines" % (where, ident))
        for ident in own:
            if not (ident.startswith("EX-") and EX_TOKEN.fullmatch(ident)):
                continue
            tagged_examples.add(ident)
            example = examples.get(ident)
            if example is None:
                result.error("CHAIN-123", "%s: @%s names an example no example map defines" % (where, ident))
            elif len(example["rules"]) == 1 and example["rules"][0] not in own + enclosing:
                result.error("CHAIN-124", "%s: @%s illustrates %s but its scenario is not under that rule"
                             % (where, ident, example["rules"][0]))
    for rule in sorted(set(rules) - tagged_rules):
        result.error("CHAIN-121", "%s has no tagged Rule: block in %s" % (rule, FEATURE_DIR))
    for ident in sorted(set(examples) - tagged_examples):
        result.error("CHAIN-122", "%s has no tagged scenario in %s" % (ident, FEATURE_DIR))
    return tagged_rules, tagged_examples


def load_invariants(project_dir, result):
    path = os.path.join(project_dir, AGGREGATES)
    if not os.path.isfile(path):
        return None
    try:
        manifest = json.loads(_read(path) or "")
    except ValueError as exc:
        result.error("CHAIN-130", "%s: unreadable — %s" % (AGGREGATES, exc))
        return None
    invariants = {}
    for aggregate in manifest.get("aggregates", []) if isinstance(manifest, dict) else []:
        if not isinstance(aggregate, dict):
            continue
        for invariant in aggregate.get("invariants", []) or []:
            if isinstance(invariant, dict) and isinstance(invariant.get("id"), str):
                kinds = {example.get("kind") for example in invariant.get("examples", []) or []
                         if isinstance(example, dict)}
                invariants[(aggregate.get("id"), invariant["id"])] = kinds
    return invariants


def check_invariant_tags(scenarios, invariants, result):
    for scenario in scenarios:
        for tag in scenario["tags"]:
            match = EXAMPLE_TAG.match(tag)
            if tag.startswith("@example=") and not match:
                result.error("CHAIN-125", "%s:%d: %s is not @example=<AGG-…>.<INV-…>.<positive|negative>"
                             % (scenario["file"], scenario["line"], tag))
            elif match and invariants is not None:
                key = (match.group(1), match.group(2))
                if key not in invariants:
                    result.error("CHAIN-125", "%s:%d: %s names an invariant the aggregate manifest does "
                                 "not declare" % (scenario["file"], scenario["line"], tag))
                elif match.group(3) not in invariants[key]:
                    result.error("CHAIN-125", "%s:%d: %s names a %s example the invariant does not have"
                                 % (scenario["file"], scenario["line"], tag, match.group(3)))


def check_properties(project_dir, invariants, result):
    path = os.path.join(project_dir, PROPERTY_SPECS)
    if invariants is None or not os.path.isfile(path):
        return None
    lines = (_read(path) or "").splitlines()
    missing = []
    for aggregate, invariant in sorted(invariants):
        inv = re.compile(r"\b%s(?!\d)" % re.escape(invariant))
        if not any(aggregate in line and inv.search(line) for line in lines):
            missing.append("%s/%s" % (aggregate, invariant))
    for name in missing:
        result.error("CHAIN-131", "%s is not named in %s — an invariant with no property test is "
                     "covered by examples alone" % (name, PROPERTY_SPECS))
    return len(invariants) - len(missing)


def check_acceptance(project_dir, tagged_rules, tagged_examples, result):
    text = _read(os.path.join(project_dir, ACCEPTANCE))
    if text is None:
        return
    mentioned = set(RULE_TOKEN.findall(text)) | set(EX_TOKEN.findall(text))
    unaccounted = sorted((tagged_rules | tagged_examples) - mentioned)
    if unaccounted:
        result.warn("CHAIN-141", "%s does not mention %s — bound, out of scope or undefined, the "
                    "record should say which" % (ACCEPTANCE, ", ".join(unaccounted)))


def check_gate(project_dir, scenarios, result):
    path = os.path.join(project_dir, GATE)
    if not os.path.isfile(path):
        return
    try:
        gate = json.loads(_read(path) or "")
    except ValueError as exc:
        result.error("CHAIN-150", "%s: unreadable — %s" % (GATE, exc))
        return
    stages = gate.get("stages", []) if isinstance(gate, dict) else []
    unit = next((s for s in stages if isinstance(s, dict) and s.get("stage") == "unit"), None)
    if unit is None:
        return
    record = unit.get("test_first")
    if not isinstance(record, dict):
        result.error("CHAIN-151", "%s: the unit stage has no test_first record — it is units by "
                     "sequence, or not-applicable with its reason, never absent" % GATE)
        return
    if "units" not in record and not (record.get("status") == "not-applicable" and record.get("reason")):
        result.error("CHAIN-151", "%s: test_first carries neither units nor not-applicable with a reason" % GATE)
    outer = record.get("outer_loop")
    if isinstance(outer, str) and outer.startswith("bdd:@") and scenarios:
        tag = outer[len("bdd:"):]
        if not any(tag in s["tags"] or tag in s["rule_tags"] for s in scenarios):
            result.error("CHAIN-152", "%s: the outer loop names %s, which no scenario carries" % (GATE, tag))


def check(project_dir):
    result = Result()
    maps = load_maps(project_dir, result)
    check_maps(maps, result)
    check_graph(project_dir, maps, result)
    feature_files, scenarios = load_features(project_dir, result)
    tagged_rules, tagged_examples = set(), set()
    if feature_files:
        if maps["files"]:
            tagged_rules, tagged_examples = check_features(project_dir, maps, scenarios, result)
        else:
            result.warn("CHAIN-126", "%d scenario(s) in %s but no example map — they derive from the "
                        "design manifests, not from examples anyone agreed to; run "
                        "/architect:define-requirements or /product:example-map"
                        % (len(scenarios), FEATURE_DIR))
    invariants = load_invariants(project_dir, result)
    check_invariant_tags(scenarios, invariants, result)
    covered = check_properties(project_dir, invariants, result)
    if feature_files:
        check_acceptance(project_dir, tagged_rules, tagged_examples, result)
    check_gate(project_dir, scenarios, result)
    result.summary = {
        "example_maps": len(maps["files"]), "rules": len(maps["rules"]),
        "examples": len(maps["examples"]), "feature_files": len(feature_files),
        "scenarios": len(scenarios), "rules_in_gherkin": len(tagged_rules),
        "examples_in_gherkin": len(tagged_examples),
        "invariants": None if invariants is None else len(invariants),
        "invariants_with_property": covered,
    }
    return result


def main(argv):
    args = [arg for arg in argv[1:] if arg != "--json"]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print("usage: example_chain.py <project_dir> [--json]", file=sys.stderr)
        return 2
    result = check(args[0])
    if "--json" in argv:
        print(json.dumps({"summary": result.summary, "errors": result.errors,
                          "warnings": result.warnings}, ensure_ascii=False, indent=2))
    else:
        for item in result.errors:
            print("ERROR %s %s" % (item["code"], item["message"]))
        for item in result.warnings:
            print("WARN  %s %s" % (item["code"], item["message"]))
        print("chain: %s" % ", ".join("%s=%s" % pair for pair in result.summary.items()))
        print("%d error(s), %d warning(s)" % (len(result.errors), len(result.warnings)))
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
