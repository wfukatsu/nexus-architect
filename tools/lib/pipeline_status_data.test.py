#!/usr/bin/env python3
"""Executable check of the pipeline-status derivation contract.

pipeline_status_data.py encodes how the dashboard reads a project's pipeline state;
this asserts those rules as behaviour, against a scratch project it builds itself:

- the shipped skill-dependencies.yaml files parse with the built-in mini-YAML reader
  (both plugins, including wrapped inline lists and inline maps);
- status precedence: the progress registry wins, the filesystem fills the gap, and the
  two disagreeing raises drift (completed with nothing written / pending with all
  outputs present);
- invalidation: a completed phase whose upstream wrote later is `stale`, staleness
  propagates down the dependency chain, leaves the done fraction, and becomes the
  suggested next command — while an in-run write-ordering gap does not trip it;
- output counting: files, `{project}` globs, and directories (empty = not written);
- exclusion: `options.skip_phases` and `conditions:` against the project options;
- dependency state: blocked_by / runnable / the "next phase to run" pick;
- grouping: the architect extension tier is its own group and stays out of the core
  progress count;
- cost attribution: "a+b" ledger keys split evenly, `_`-prefixed keys are unassigned;
- activity heartbeat from work/token-usage.jsonl;
- the generated slash commands.

    python3 tools/lib/pipeline_status_data.test.py            # scratch fixture project
    python3 tools/lib/pipeline_status_data.test.py <project>  # a real project directory

Exit status 0 = all checks pass, 1 = at least one failed.
"""
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline_status_data as P  # noqa: E402

FAILURES = 0


def check(name, cond, detail=""):
    global FAILURES
    print("  [%s] %s%s" % ("ok" if cond else "FAIL", name,
                           (" — " + str(detail)) if (detail and not cond) else ""))
    if not cond:
        FAILURES += 1


# --------------------------------------------------------------------- fixture project
def write(path, text=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text or "x\n")


def build_fixture(root):
    """An architect project mid-pipeline, with every rule the checks below exercise."""
    proj = "demo"
    # investigate: 4 declared outputs, 2 written -> partial (registry says in_progress)
    for name in ("technology-stack.md", "codebase-structure.md"):
        write(os.path.join(root, "reports", "before", proj, name))
    # analyze: all 4 outputs written but the registry never recorded it -> derived
    for name in ("system-overview.md", "ubiquitous-language.md",
                 "actors-roles-permissions.md", "domain-code-mapping.md"):
        write(os.path.join(root, "reports", "01_analysis", name))
    # design-microservices: 1 of 2 outputs, no registry entry -> derived in_progress
    write(os.path.join(root, "reports", "03_design", "target-architecture.md"))
    # design-implementation (extension tier): 1 of its 4 declared spec files
    write(os.path.join(root, "reports", "06_implementation", "value-objects-spec.md"))
    # generate-infra-code (extension tier): directory output with a file in it
    write(os.path.join(root, "generated", "infrastructure", "k8s", "deployment.yaml"))
    # generate-test-specs (extension tier): its declared directory exists but is empty
    os.makedirs(os.path.join(root, "reports", "07_test-specs", "bdd-scenarios"),
                exist_ok=True)
    # review-report: registry claims completed, nothing on disk -> drift. The name is
    #           architect's alone, so the claim is unambiguous and only the files refute it.
    # map-domains: the same claim under a name BOTH manifests define -> the entry may be
    #           the product pipeline's, so it is not read as this phase being done.
    # redesign: registry never left pending, both outputs present -> the other drift,
    #           and the files win over the unstamped entry
    for name in ("bounded-contexts-redesign.md", "context-map.md"):
        write(os.path.join(root, "reports", "03_design", name))

    progress = {
        "schema_version": 1,
        "project_name": proj,
        "updated_at": "2026-08-06T10:00:00Z",
        "options": {"scalardb_enabled": False, "output_language": "ja",
                    "skip_phases": ["analyze-data-model"]},
        "phases": {
            "investigate": {"status": "in_progress", "started_at": "2026-08-06T09:00:00Z",
                            "note": "step 3/4", "outputs": []},
            "review-report": {"status": "completed", "completed_at": "2026-08-06T09:30:00Z"},
            "map-domains": {"status": "completed", "completed_at": "2026-08-06T09:30:00Z"},
            "redesign": {"status": "pending"},
            # pending with nothing on disk: the entry and the files agree, no drift
            "design-api": {"status": "pending"},
            "evaluate-mmi": {"status": "failed"},
            "hand-written-phase": {"status": "completed"},
        },
        "errors": ["evaluate-mmi: sub-agent failed"],
        "warnings": [],
    }
    write(os.path.join(root, "work", "pipeline-progress.json"),
          json.dumps(progress, indent=2))

    ledger = {
        "phases": {
            "investigate": {"cost_usd": 1.0},
            "evaluate-mmi+evaluate-ddd": {"cost_usd": 3.0},
            "_unassigned": {"cost_usd": 0.5},
        },
        "total_cost_usd": 4.5,
    }
    write(os.path.join(root, "work", "token-usage.json"), json.dumps(ledger))

    now = datetime.now(timezone.utc).isoformat()
    write(os.path.join(root, "work", "token-usage.jsonl"), "\n".join([
        json.dumps({"ts": "2026-01-01T00:00:00+00:00", "attributed_to": "analyze"}),
        json.dumps({"ts": now, "attributed_to": "_pending",
                    "in_progress": ["investigate"]}),
    ]) + "\n")
    return proj


# --------------------------------------------------------------------------- the checks
def check_yaml_reader():
    print("mini-YAML reader")
    text = (
        "schema_version: 1        # trailing comment\n"
        "plugin: product\n"
        "orchestrators:\n"
        "  start: { model: sonnet, note: \"a, b # not a comment\" }\n"
        "phases:\n"
        "  one:\n"
        "    depends_on: []\n"
        "    optional: true\n"
        "    outputs:\n"
        "      - reports/a.md\n"
        "      - reports/b.md\n"
        "  two:\n"
        "    depends_on: [one]\n"
        "    outputs: [reports/c.md]\n"
        "profiles:\n"
        "  full: [one,\n"
        "         two]\n"
    )
    data = P.parse_yaml(text)
    check("scalars, booleans and comments", data.get("schema_version") == 1
          and data["phases"]["one"]["optional"] is True, data.get("schema_version"))
    check("quoted value keeps its # and comma",
          data["orchestrators"]["start"]["note"] == "a, b # not a comment",
          data["orchestrators"]["start"])
    check("block list", data["phases"]["one"]["outputs"] == ["reports/a.md",
                                                             "reports/b.md"])
    check("inline list", data["phases"]["two"]["depends_on"] == ["one"])
    check("inline list wrapped across lines", data["profiles"]["full"] == ["one", "two"])


def check_real_manifests():
    print("shipped skill-dependencies.yaml")
    arch = P.load_phase_manifest("architect")
    prod = P.load_phase_manifest("product")
    check("architect manifest parses with its core phases",
          {"investigate", "analyze", "review-synthesizer", "report"} <= set(arch),
          sorted(arch)[:5])
    check("architect deps survive",
          arch["analyze"]["depends_on"] == ["investigate"], arch["analyze"])
    check("architect conditions survive",
          arch["design-scalardb"]["conditions"] == ["scalardb_enabled"],
          arch["design-scalardb"])
    check("architect outputs survive (4 for investigate)",
          len(arch["investigate"]["outputs"]) == 4, arch["investigate"]["outputs"])
    check("extension tier is added to architect only",
          arch["design-infrastructure"]["tier"] == "extension"
          and all(s["tier"] == "core" for s in prod.values()),
          arch["design-infrastructure"]["tier"])
    check("product manifest parses (>= 20 phases, orchestrators excluded)",
          len(prod) >= 20 and "start" not in prod, len(prod))
    check("product categories survive",
          prod["generate-ui-mock"]["category"] == "spec", prod["generate-ui-mock"])
    check("product gate flag survives", prod["validate-assumptions"].get("gate") is True,
          prod["validate-assumptions"])
    order = P.order_phases(arch)
    check("dependency order: analyze after investigate, synthesizer after its reviews",
          order.index("analyze") > order.index("investigate")
          and order.index("review-synthesizer") > order.index("review-consistency"),
          order[:6])

    marketplace_path = os.path.join(P.plugin_root(), ".claude-plugin", "marketplace.json")
    with open(marketplace_path, encoding="utf-8") as fh:
        marketplace = json.load(fh)
    architect = next(p for p in marketplace["plugins"] if p["name"] == "architect")
    check("Claude marketplace discovers both GraphQL skills",
          {"./skills/design-graphql", "./skills/generate-graphql-code"}
          <= set(architect["skills"]), architect["skills"])


# The manual extension tier as CLAUDE.md and README describe it. The dashboard claims to
# cover the tier, so a skill added there must be added here too — that is what this pins.
DOC_EXTENSION_TIER = [
    "investigate-security", "select-scalardb-edition", "design-scalardb-analytics",
    "design-implementation", "generate-test-specs", "generate-scalardb-code",
    "generate-api-code", "generate-graphql-code", "generate-contract-tests",
    "generate-infra-code", "generate-docs", "verify-implementation",
    "design-infrastructure", "design-security",
    "design-observability", "design-disaster-recovery", "estimate-cost",
    "estimate-token-cost", "report-token-cost",
]


def check_extension_tier():
    print("extension tier coverage")
    root = P.plugin_root()
    arch = P.load_phase_manifest("architect")
    missing = [n for n in DOC_EXTENSION_TIER if n not in arch]
    check("every documented extension-tier skill is known to the dashboard",
          not missing, missing)
    extra = [n for n, s in arch.items()
             if s["tier"] == "extension" and n not in DOC_EXTENSION_TIER]
    check("the dashboard invents no extension phase the docs do not list", not extra,
          extra)
    unshipped = [n for n in DOC_EXTENSION_TIER
                 if not os.path.isfile(os.path.join(root, "skills", n, "SKILL.md"))]
    check("every extension-tier phase has a SKILL.md", not unshipped, unshipped)

    # A declared output is a path this tool globs against a real project, and a filename
    # the skill itself has to write. `architect:investigate-security.md` shipped as one
    # for a while: a colon in a filename, off-convention, and unmatchable in practice.
    bad = []
    for name in DOC_EXTENSION_TIER:
        for pattern in arch[name]["outputs"]:
            base = os.path.basename(pattern.rstrip("/"))
            # kebab-case is the rule for the reports/ tree (@rules/output-conventions.md);
            # generated code keeps its ecosystem's names (Dockerfile, build.gradle).
            kebab = not pattern.startswith("reports/") or re.match(
                r"^[a-z0-9*{}][a-z0-9*.{}-]*$", base)
            if ":" in pattern or not kebab:
                bad.append("%s -> %s" % (name, pattern))
    check("declared extension outputs are colon-free, kebab-case under reports/",
          not bad, bad)

    # Each extension phase's outputs must appear in its own SKILL.md Output table, or the
    # dashboard measures progress against files the skill never promised to write. The
    # skills spell their placeholders out ({service}); this tool globs them.
    def variants(pattern):
        stem = pattern.rstrip("/")
        return {stem, stem.replace("*", "{service}"), stem.replace("*", "{project}")}

    undocumented = []
    for name in DOC_EXTENSION_TIER:
        try:
            with open(os.path.join(root, "skills", name, "SKILL.md"),
                      encoding="utf-8") as fh:
                body = fh.read()
        except OSError:
            continue
        for pattern in arch[name]["outputs"]:
            if not any(v in body for v in variants(pattern)):
                undocumented.append("%s -> %s" % (name, pattern))
    check("every declared extension output is named in its SKILL.md", not undocumented,
          undocumented)


# ------------------------------------------------------- invalidation (stale) fixture
# A finished stretch of the architect pipeline, written in dependency order an hour ago:
# investigate -> analyze -> evaluate-mmi / evaluate-ddd -> integrate-evaluations.
STALE_CHAIN = [
    ("investigate", ["reports/before/demo/technology-stack.md",
                     "reports/before/demo/codebase-structure.md",
                     "reports/before/demo/issues-and-debt.md",
                     "reports/before/demo/ddd-readiness.md"]),
    ("analyze", ["reports/01_analysis/system-overview.md",
                 "reports/01_analysis/ubiquitous-language.md",
                 "reports/01_analysis/actors-roles-permissions.md",
                 "reports/01_analysis/domain-code-mapping.md"]),
    ("evaluate-mmi", ["reports/02_evaluation/mmi-overview.md",
                      "reports/02_evaluation/mmi-by-module.md"]),
    ("evaluate-ddd", ["reports/02_evaluation/ddd-strategic-evaluation.md",
                      "reports/02_evaluation/ddd-tactical-architecture-evaluation.md"]),
    ("integrate-evaluations", ["reports/02_evaluation/integrated-evaluation.md",
                               "reports/02_evaluation/unified-improvement-plan.md"]),
]


def build_stale_fixture(root, base):
    """Write the chain with each phase's files older than the phase that consumed them."""
    for step, (_, paths) in enumerate(STALE_CHAIN):
        for path in paths:
            full = os.path.join(root, path)
            write(full)
            os.utime(full, (base + step * 60, base + step * 60))
    # The last phase is left out of the registry, so derived-completed is covered too.
    write(os.path.join(root, "work", "pipeline-progress.json"), json.dumps({
        "project_name": "demo",
        "options": {"scalardb_enabled": False},
        "phases": {name: {"status": "completed"} for name, _ in STALE_CHAIN[:-1]},
    }))


def check_staleness(root):
    print("invalidation of completed phases")
    proj = os.path.join(root, "stale")
    base = time.time() - 3600
    build_stale_fixture(proj, base)

    phases = P.derive_all(proj)["phases"]
    check("a chain written in dependency order is not stale",
          not any(p["stale"] for p in phases.values()),
          [n for n, p in phases.items() if p["stale"]])
    check("and its phases still read completed",
          phases["analyze"]["display_status"] == "completed"
          and phases["integrate-evaluations"]["display_status"] == "completed")

    # An upstream output written a hair later than its consumer — same-run ordering,
    # not a change — must stay inside the grace window.
    edited = os.path.join(proj, STALE_CHAIN[0][1][0])
    nudged = base + 60 + P.STALE_GRACE - 1
    os.utime(edited, (nudged, nudged))
    phases = P.derive_all(proj)["phases"]
    check("an upstream write inside the grace window does not invalidate",
          not phases["analyze"]["stale"], phases["analyze"]["stale_by"])

    # Now the real thing: the first phase of the chain is fixed after the fact.
    os.utime(edited, None)
    state = P.derive_all(proj)
    phases = state["phases"]
    check("the phase reading the edited output goes stale",
          phases["analyze"]["stale"] and phases["analyze"]["stale_by"] == ["investigate"],
          phases["analyze"])
    check("the edited phase itself stays completed",
          not phases["investigate"]["stale"]
          and phases["investigate"]["display_status"] == "completed")
    check("staleness propagates down the chain",
          phases["evaluate-mmi"]["stale_inherited"] == ["analyze"]
          and phases["integrate-evaluations"]["stale_inherited"] == ["evaluate-mmi",
                                                                    "evaluate-ddd"],
          phases["integrate-evaluations"])
    check("a derived-completed phase is invalidated too (no registry entry)",
          phases["integrate-evaluations"]["source"] == "derived"
          and phases["integrate-evaluations"]["stale"])
    check("the status column reads stale, the recorded status is untouched",
          phases["analyze"]["display_status"] == "stale"
          and phases["analyze"]["status"] == "completed")
    check("the change timestamp is carried for display",
          phases["analyze"]["stale_at"] and phases["analyze"]["stale_at"] > base + 3000,
          phases["analyze"]["stale_at"])

    print("what the invalidation does to the summary and the next command")
    stale = {"analyze", "evaluate-mmi", "evaluate-ddd", "integrate-evaluations"}
    check("every invalidated phase is listed on the state",
          set(state["stale"]) == stale and state["summary"]["stale"] == 4,
          state["stale"])
    check("stale phases leave the done fraction",
          state["summary"]["by_status"]["stale"] == 4
          and state["summary"]["completed"] == sum(
              1 for p in phases.values()
              if p["tier"] == "core" and p["display_status"] in ("completed", "skipped")),
          state["summary"])
    check("next = the earliest stale phase, not the first pending one",
          state["next"] == "analyze", state["next"])
    check("a stale phase is runnable again",
          phases["analyze"]["runnable"] and not phases["analyze"]["blocked_by"])
    check("but does not block its dependents",
          "analyze" not in phases["evaluate-mmi"]["blocked_by"],
          phases["evaluate-mmi"]["blocked_by"])
    cmd = P.default_action(state, phases["analyze"])
    check("its default action is a rerun, not opening the output",
          cmd == ("rerun phase", "/architect:analyze"), cmd)
    rows = P.flatten(state, status_filter="stale")
    check("the stale filter selects exactly those phases",
          {r[0]["key"] for r in rows if r[0]["kind"] == "phase"} == stale, rows)
    group = next(g for g in state["groups"] if g["key"] == "evaluation")
    check("group counts drop the invalidated phases",
          P.group_counts(group) == (0, len(group["phases"])), P.group_counts(group))

    print("invalidation is not claimed where it cannot be known")
    check("a pending upstream invalidates nothing",
          not phases["redesign"]["stale"] and not phases["map-domains"]["stale"])
    check("a phase that declares outputs but wrote none is drift, not stale",
          not any(p["stale"] for p in phases.values() if p["declared"]
                  and not p["written"]),
          [n for n, p in phases.items() if p["stale"] and not p["written"]])


_HOOK = []


def check_id_prefix_registry():
    """`id_prefix` in the manifests is the ID namespace's single source of truth.

    Every skill that appends to `work/traceability.json` mints IDs under a prefix, and the
    whole traceability contract (docs/design.md §1.3/§1.5, and adapt-change's blast radius)
    assumes those prefixes are known and distinct. They used to live only in each SKILL.md's
    prose, where three skills turned out to declare none at all — a screen or a market
    finding with no ID is a node nothing downstream can cite.
    """
    print("ID prefix registry")
    root = P.plugin_root()

    def skill_path(plugin, name):
        parts = [root, "skills"] + (["product"] if plugin == "product" else []) + [name, "SKILL.md"]
        return os.path.join(*parts)

    claims, missing_decl, unused, malformed = {}, [], [], []
    for plugin in ("product", "architect"):
        for name, spec in P.load_phase_manifest(plugin).items():
            prefixes = spec.get("id_prefix") or []
            if not prefixes:
                continue
            path = skill_path(plugin, name)
            body = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
            for prefix in prefixes:
                if not (prefix.endswith("-") and prefix[:-1].isupper()):
                    malformed.append((name, prefix))
                claims.setdefault(prefix, []).append((plugin, name))
                if body and prefix not in body:
                    unused.append((name, prefix))

    check("declared prefixes are UPPERCASE and end in '-'", not malformed, malformed)
    check("every declared prefix appears in its own SKILL.md", not unused, unused)

    # The inverse: a skill that writes to the graph must say under which prefix.
    for plugin in ("product", "architect"):
        for name, spec in P.load_phase_manifest(plugin).items():
            if spec.get("id_prefix"):
                continue
            path = skill_path(plugin, name)
            if not os.path.exists(path):
                continue
            body = open(path, encoding="utf-8").read()
            if "Append traceability" in body:
                missing_decl.append((plugin, name))
    check("every skill that appends to the graph declares a prefix", not missing_decl,
          missing_decl)

    # Distinct within a manifest; NFR- is the one deliberate cross-manifest claim (§1.5).
    dupes = {p: c for p, c in claims.items()
             if len({(pl, n) for pl, n in c}) > 1 and len({pl for pl, _ in c}) == 1}
    check("no two skills in one manifest claim the same prefix", not dupes, dupes)
    crossing = sorted(p for p, c in claims.items() if len({pl for pl, _ in c}) > 1)
    check("NFR- is the only prefix both manifests claim — the §1.5 carry-over",
          crossing == ["NFR-"], crossing)

    # The three that had none, and the edge that closes the journey->feature chain.
    for name, prefix in (("research-landscape", "MKT-"), ("generate-ui-mock", "SCR-"),
                         ("generate-frontend", "PG-")):
        check("%s mints %s" % (name, prefix),
              prefix in (P.load_phase_manifest("product")[name].get("id_prefix") or []))
    check("define-features cites the screen it came from",
          "SCR-" in open(skill_path("product", "define-features"), encoding="utf-8").read())


def check_conditional_outputs_and_gate(root):
    """Two things an end-to-end run surfaced that a synthetic fixture had not.

    `define-requirements` writes `scalardb-applicability.md` only when ScalarDB is in play,
    but the manifest listed it unconditionally — so a ScalarDB-free project sat at 3/4
    outputs forever, reading as an unfinished phase rather than one with nothing to write.
    And the validation gate belongs to *product*, yet an unlabelled `gate: no-go` was
    printed over the architect tree as if architect had rendered that verdict.
    """
    print("conditional outputs and gate ownership")
    spec = P.load_phase_manifest("architect")["define-requirements"]
    check("the conditional output is declared apart from the unconditional ones",
          "reports/00_requirements/scalardb-applicability.md" not in (spec.get("outputs") or [])
          and any("scalardb-applicability.md" in e
                  for e in spec.get("conditional_outputs") or []), spec)

    proj = os.path.join(root, "conditional")
    for name in ("requirements-definition.md", "data-transaction-requirements.md",
                 "open-questions.md"):
        write(os.path.join(proj, "reports", "00_requirements", name))
    reg = {"project_name": "demo", "options": {"scalardb_enabled": False},
           "phases": {"define-requirements": {"status": "completed", "plugin": "architect"}},
           "gates": {"validate-assumptions": {"verdict": "no-go",
                                              "open_assumptions": ["ASM-001"]}}}
    write(os.path.join(proj, "work", "pipeline-progress.json"), json.dumps(reg))

    off = P.derive_all(proj, plugin="architect")
    state = off["phases"]["define-requirements"]
    check("ScalarDB off: the conditional output is not counted (3 of 3)",
          (state["written"], state["declared"]) == (3, 3), state["outputs"])
    check("and the phase reads completed with no drift",
          state["status"] == "completed" and state["drift"] is None, state)

    reg["options"]["scalardb_enabled"] = True
    write(os.path.join(proj, "work", "pipeline-progress.json"), json.dumps(reg))
    on = P.derive_all(proj, plugin="architect")["phases"]["define-requirements"]
    check("ScalarDB on: it is counted and missing (3 of 4)",
          (on["written"], on["declared"]) == (3, 4), on["outputs"])

    check("the gate carries its owning pipeline",
          off["gate"]["plugin"] == "product", off["gate"])
    check("the product gate is still surfaced on the architect view",
          off["gate"]["verdict"] == "no-go")


def check_graphql_condition(root):
    """GraphQL detailed design runs only after design-api selected that surface."""
    print("GraphQL API-style condition")
    spec = P.load_phase_manifest("architect")["design-graphql"]
    check("design-graphql follows design-api and is condition-gated",
          spec["depends_on"] == ["design-api"]
          and spec["conditions"] == ["api_style_graphql"], spec)

    proj = os.path.join(root, "graphql-condition")
    write(os.path.join(proj, "work", "pipeline-progress.json"), json.dumps({
        "project_name": "demo",
        "options": {"scalardb_enabled": False, "api_style_graphql": False},
        "phases": {},
    }))
    off = P.derive_all(proj)["phases"]["design-graphql"]
    check("REST-only: GraphQL design is conditionally skipped",
          off["status"] == "skipped" and off["excluded"] == "condition", off)

    write(os.path.join(proj, "work", "pipeline-progress.json"), json.dumps({
        "project_name": "demo",
        "options": {"scalardb_enabled": False, "api_style_graphql": True},
        "phases": {},
    }))
    on = P.derive_all(proj)["phases"]["design-graphql"]
    check("GraphQL/hybrid: GraphQL design is enabled",
          on["status"] == "pending" and on["excluded"] is None, on)

    decision_path = os.path.join(proj, "reports", "03_design", "api-style-decisions.json")
    surface = {
        "surface_id": "customer", "scalardb_backed": False,
        "access_surface": "external", "application_framework": "Spring for GraphQL",
        "consumers": ["web"], "operations": ["Query.customer"],
        "selected_style": "graphql", "client_variability": "variable projections",
        "cache_needs": "application", "security_model": "OIDC",
        "transport": "HTTP", "execution_model": "Spring MVC", "data_access": "JDBC",
        "transaction_model": "local", "operational_readiness": "ready",
        "rejected_alternatives": ["REST"], "requirement_ids": ["FR-001"],
        "rationale": "consumer projections",
    }
    write(decision_path, json.dumps({"surfaces": [surface]}))
    write(os.path.join(proj, "work", "pipeline-progress.json"), json.dumps({
        "project_name": "demo",
        "options": {"scalardb_enabled": False, "api_style_graphql": False},
        "phases": {},
    }))
    canonical_graphql = P.derive_all(proj)
    graphql_phase = canonical_graphql["phases"]["design-graphql"]
    check("canonical GraphQL overrides a stale false option",
          graphql_phase["status"] == "pending" and graphql_phase["excluded"] is None,
          graphql_phase)
    check("canonical/legacy disagreement is visible",
          any("ignored stale options.api_style_graphql" in warning
              for warning in canonical_graphql["warnings"]), canonical_graphql["warnings"])

    surface["selected_style"] = "rest"
    write(decision_path, json.dumps({"surfaces": [surface]}))
    write(os.path.join(proj, "work", "pipeline-progress.json"), json.dumps({
        "project_name": "demo",
        "options": {"scalardb_enabled": False, "api_style_graphql": True},
        "phases": {},
    }))
    canonical_rest = P.derive_all(proj)["phases"]["design-graphql"]
    check("canonical REST overrides a stale true option",
          canonical_rest["status"] == "skipped" and canonical_rest["excluded"] == "condition",
          canonical_rest)

    write(decision_path, "{broken")
    invalid = P.derive_all(proj)
    invalid_phase = invalid["phases"]["design-graphql"]
    check("invalid canonical decision blocks GraphQL design as a condition failure",
          invalid_phase["excluded"] == "condition-error"
          and invalid_phase["status"] == "failed" and not invalid_phase["runnable"],
          invalid_phase)
    check("invalid canonical decision surfaces an actionable error",
          any("invalid canonical API-style decision" in error for error in invalid["errors"]),
          invalid["errors"])

    # Restore the GraphQL contract for output-ownership fixtures below.
    surface["selected_style"] = "graphql"
    write(decision_path, json.dumps({"surfaces": [surface]}))

    # design-api owns this inventory directory. Its presence must not complete
    # the detailed design phase.
    write(os.path.join(proj, "reports", "03_design", "api-specifications", "graphql",
                       "inventory.md"), "inventory")
    inventory_only = P.derive_all(proj)["phases"]["design-graphql"]
    check("GraphQL inventory alone does not complete detailed design",
          inventory_only["status"] == "pending" and inventory_only["written"] == 0,
          inventory_only)

    graphql_dir = os.path.join(proj, "reports", "03_design", "api-specifications", "graphql")
    for name in ("customer.graphqls", "resolver-contracts.md", "authorization-matrix.md",
                 "batch-loading-plan.md", "query-governance.md", "transport-design.md"):
        write(os.path.join(graphql_dir, name), "contract")
    complete = P.derive_all(proj)["phases"]["design-graphql"]
    check("all six owned GraphQL contracts complete detailed design",
          complete["status"] == "completed" and complete["written"] == 6,
          complete)

    codegen = os.path.join(root, "graphql-codegen-ownership")
    # The generator is conditioned on the same canonical decision as its design phase,
    # so a project that ran it necessarily carries a GraphQL surface.
    write(os.path.join(codegen, "reports", "03_design", "api-style-decisions.json"),
          json.dumps({"surfaces": [surface]}))
    write(os.path.join(codegen, "generated", "demo", "src", "main", "resources",
                       "graphql", "schema.graphqls"), "schema")
    write(os.path.join(codegen, "generated", "demo", "src", "main", "java",
                       "Controller.java"), "class Controller {}")
    write(os.path.join(codegen, "reports", "06_implementation", "api-contract-map.md"), "map")
    write(os.path.join(codegen, "reports", "06_implementation", "api-contract-map.json"), "{}")
    shared_only = P.derive_codegen(codegen, "architect")["phases"]["generate-graphql-code"]
    check("shared source and map outputs do not complete GraphQL code generation",
          shared_only["status"] == "pending" and shared_only["written"] == 0,
          shared_only)
    write(os.path.join(codegen, "reports", "06_implementation",
                       "graphql-code-generation.md"), "evidence")
    owned = P.derive_codegen(codegen, "architect")["phases"]["generate-graphql-code"]
    check("unique generation evidence completes GraphQL code generation",
          owned["status"] == "completed" and owned["written"] == 1, owned)

    # The extension tier used to hardcode conditions=[] when folding EXTENSION_PHASES into
    # the manifest, which silently disarmed every condition an extension phase declared.
    manifest = P.load_phase_manifest("architect")
    check("the extension tier keeps the conditions its phases declare",
          manifest["generate-graphql-code"]["conditions"] == ["api_style_graphql"],
          manifest["generate-graphql-code"])
    surface["selected_style"] = "rest"
    write(os.path.join(codegen, "reports", "03_design", "api-style-decisions.json"),
          json.dumps({"surfaces": [surface]}))
    rest_codegen = P.derive_codegen(codegen, "architect")["phases"]["generate-graphql-code"]
    check("a REST-only decision withdraws the GraphQL generator from the codegen view",
          rest_codegen["excluded"] == "condition" and not rest_codegen["runnable"],
          rest_codegen)


def hook_module():
    """hooks/record_token_usage.py, imported by path — it is not on sys.path."""
    if not _HOOK:
        import importlib.util
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(root, "hooks", "record_token_usage.py")
        spec = importlib.util.spec_from_file_location("record_token_usage", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _HOOK.append(mod)
    return _HOOK[0]


def check_shared_phase_names(root):
    """Both pipelines write one registry keyed by bare phase name.

    So a `completed` entry under a name both manifests define carries no evidence of
    which pipeline wrote it, and the architect tab used to render the product pipeline's
    `map-domains` as its own — which `/architect:pipeline --resume-from` would then skip.
    An entry is only distrusted when this phase has nothing on disk to corroborate it.
    """
    print("phase names shared by both manifests")
    shared = P.shared_phase_names()
    check("the shared set is exactly the four colliding names",
          shared == {"map-domains", "design-api", "create-domain-story", "report"}, shared)
    check("shared and exclusive partition each manifest",
          not (shared & P.exclusive_phases("architect"))
          and not (shared & P.exclusive_phases("product")))

    # The main fixture's registry: `map-domains` completed, no architect output on disk.
    phases = P.derive_all(root)["phases"]
    check("a shared completed entry with nothing written is not read as done",
          phases["map-domains"]["status"] == "pending"
          and phases["map-domains"]["source"] == "derived", phases["map-domains"])
    check("and it is reported as drift, named for the reason",
          phases["map-domains"]["drift"] == "shared-name", phases["map-domains"])
    check("a shared pending entry is left alone, as before",
          phases["design-api"]["status"] == "pending"
          and phases["design-api"]["drift"] is None, phases["design-api"])

    # Same registry claim, but this pipeline's own output exists: the claim is corroborated.
    corroborated = os.path.join(root, "shared-ok")
    write(os.path.join(corroborated, "reports", "03_design", "domain-analysis.md"))
    write(os.path.join(corroborated, "work", "pipeline-progress.json"), json.dumps({
        "project_name": "demo", "options": {"scalardb_enabled": False},
        "phases": {"map-domains": {"status": "completed"},
                   # in_progress is exempt: the registry is the only thing that can say a
                   # phase is running, and a running phase has written nothing yet.
                   "design-api": {"status": "in_progress"},
                   "create-domain-story": {"status": "skipped"}},
    }))
    phases = P.derive_all(corroborated)["phases"]
    check("a shared entry backed by this pipeline's own output keeps its status",
          phases["map-domains"]["status"] == "completed"
          and phases["map-domains"]["source"] == "progress"
          and phases["map-domains"]["drift"] is None, phases["map-domains"])
    check("in_progress under a shared name is never demoted",
          phases["design-api"]["status"] == "in_progress"
          and phases["design-api"]["source"] == "progress", phases["design-api"])
    check("an unexplained shared skipped is distrusted like completed",
          phases["create-domain-story"]["status"] == "pending"
          and phases["create-domain-story"]["drift"] == "shared-name",
          phases["create-domain-story"])

    # The registry entry naming its own pipeline settles the question outright — no
    # output corroboration needed, and it holds for every status including in_progress.
    labelled = os.path.join(root, "shared-labelled")
    write(os.path.join(labelled, "reports", "03_domain", "domain-map.md"))
    write(os.path.join(labelled, "work", "pipeline-progress.json"), json.dumps({
        "project_name": "demo", "options": {"scalardb_enabled": False},
        "phases": {"map-domains": {"status": "completed", "plugin": "product"},
                   "design-api": {"status": "in_progress", "plugin": "product"}},
    }))
    phases = P.derive_all(labelled, plugin="architect")["phases"]
    check("an entry labelled for the other pipeline is not this phase's status",
          phases["map-domains"]["status"] == "pending"
          and phases["design-api"]["status"] == "pending", phases["map-domains"])
    phases = P.derive_all(labelled, plugin="product")["phases"]
    check("and it is that phase's status on its own pipeline",
          phases["map-domains"]["status"] == "completed"
          and phases["design-api"]["status"] == "in_progress", phases["design-api"])
    check("a labelled entry raises no shared-name drift — it is not ambiguous",
          phases["map-domains"]["drift"] is None
          and P.derive_all(labelled, plugin="architect")["phases"]["map-domains"]["drift"]
          is None)

    print("token-usage buckets under a shared phase name")
    check("the hook's fallback shared set matches the manifests",
          set(hook_module().SHARED_PHASE_NAMES) == shared,
          hook_module().SHARED_PHASE_NAMES)
    check("the hook namespaces a shared name and leaves the rest bare",
          (hook_module().phase_key("map-domains", "product", shared),
           hook_module().phase_key("investigate", "architect", shared),
           hook_module().phase_key("map-domains", None, shared))
          == ("product:map-domains", "investigate", "map-domains"))

    ledger = os.path.join(root, "shared-cost")
    write(os.path.join(ledger, "work", "pipeline-progress.json"), json.dumps({
        "project_name": "demo", "options": {"scalardb_enabled": False}, "phases": {}}))
    write(os.path.join(ledger, "work", "token-usage.json"), json.dumps({
        "phases": {"architect:map-domains": {"cost_usd": 1.5},
                   "product:map-domains": {"cost_usd": 2.5},
                   "investigate": {"cost_usd": 4.0},
                   "map-domains": {"cost_usd": 8.0},      # legacy, un-namespaced
                   "_unassigned": {"cost_usd": 0.5}},
        "total_cost_usd": 16.5}))
    costs, total, unassigned = P.load_cost(ledger, "architect")
    check("a namespaced bucket is charged only to its own pipeline",
          costs.get("map-domains") == 1.5, costs)
    check("an unshared name still resolves without a prefix",
          costs.get("investigate") == 4.0, costs)
    check("a legacy bare bucket under a shared name is unassignable, not either side's",
          unassigned == 8.5 and total == 16.5, (unassigned, total))
    check("the neighbour's bucket is not unassigned either — it is charged on its own tab",
          P.load_cost(ledger, "product")[0].get("map-domains") == 2.5,
          P.load_cost(ledger, "product")[0])

    # ...but a skip this project actually asked for is this pipeline's own decision.
    excluded = os.path.join(root, "shared-skip")
    write(os.path.join(excluded, "work", "pipeline-progress.json"), json.dumps({
        "project_name": "demo",
        "options": {"scalardb_enabled": False, "skip_phases": ["create-domain-story"]},
        "phases": {"create-domain-story": {"status": "skipped"}},
    }))
    phases = P.derive_all(excluded)["phases"]
    check("a shared skipped with a skip_phases reason is honoured",
          phases["create-domain-story"]["status"] == "skipped"
          and phases["create-domain-story"]["drift"] is None,
          phases["create-domain-story"])


def check_hostile_inputs(root):
    """The registry is agent-written mid-run: a loose shape must degrade, not crash."""
    print("malformed inputs degrade instead of raising")
    bad = os.path.join(root, "bad")
    write(os.path.join(bad, "work", "pipeline-progress.json"), json.dumps({
        "phases": {"investigate": "completed",          # bare string status
                   "analyze": {"status": "weird"},      # unknown status value
                   "report": None},                     # no entry at all
        "options": ["scalardb_enabled"],                # wrong type
        "errors": "boom",                               # wrong type
    }))
    state = P.derive_all(bad)
    check("a bare string phase entry is read as that status",
          state["phases"]["investigate"]["status"] == "completed",
          state["phases"]["investigate"]["status"])
    check("an unknown status value falls back to derivation",
          state["phases"]["analyze"]["status"] == "pending"
          and state["phases"]["analyze"]["source"] == "derived")
    check("a null entry does not crash", state["phases"]["report"]["status"] == "pending")
    check("non-dict options are ignored", state["options"] == {})
    check("a scalar errors field becomes a list", state["errors"] == ["boom"])

    write(os.path.join(bad, "reports", "backlog", "backlog-manifest.json"),
          json.dumps({"nodes": [{"level": "issue"}]}))   # node without a local_id
    check("a malformed backlog manifest yields no summary line, not an exception",
          P.backlog_summary(bad) is None)

    write(os.path.join(bad, "work", "token-usage.jsonl"), "{not json\n[]\n")
    per_phase, latest = P.load_activity(bad)
    check("unparseable jsonl lines are skipped", (per_phase, latest) == ({}, 0.0))

    empty = os.path.join(root, "empty")
    os.makedirs(empty, exist_ok=True)
    state = P.derive_all(empty)
    check("a project with no registry at all still renders",
          state["has_progress"] is False
          and state["summary"]["by_status"]["completed"] == 0
          and state["summary"]["total"] > 0, state["summary"])
    # The progress fraction counts skipped as resolved — a conditional branch that will
    # never run (the ScalarDB-disabled path here) is not outstanding work.
    check("skipped counts toward the progress fraction",
          state["summary"]["completed"] == state["summary"]["by_status"]["skipped"],
          state["summary"])


def run(root, plugin=None):
    state = P.derive_all(root, plugin=plugin)
    phases = state["phases"]

    print("plugin detection")
    check("architect detected from the phase names", state["plugin"] == "architect",
          state["plugin"])
    check("product detected from a gates block",
          P.detect_plugin({"gates": {"validate-assumptions": {}}, "phases": {}}, root)
          == "product")
    check("product detected from its phase names",
          P.detect_plugin({"phases": {"define-vision": {}, "map-journey": {}}}, root)
          == "product")

    print("status precedence")
    check("registry wins: investigate stays in_progress",
          phases["investigate"]["status"] == "in_progress"
          and phases["investigate"]["source"] == "progress", phases["investigate"])
    check("no registry entry -> derived from outputs (analyze completed)",
          phases["analyze"]["status"] == "completed"
          and phases["analyze"]["source"] == "derived", phases["analyze"])
    check("partial outputs -> derived in_progress (design-microservices 1 of 2)",
          phases["design-microservices"]["status"] == "in_progress"
          and phases["design-microservices"]["source"] == "derived",
          phases["design-microservices"])
    check("registry entry unknown to the manifest is still shown",
          "hand-written-phase" in phases)
    check("failed status survives", phases["evaluate-mmi"]["status"] == "failed")

    print("drift")
    check("completed with no output written -> outputs-missing",
          phases["review-report"]["drift"] == "outputs-missing", phases["review-report"])
    check("and the recorded completed still wins, because the name is unambiguous",
          phases["review-report"]["status"] == "completed"
          and phases["review-report"]["source"] == "progress", phases["review-report"])
    check("pending with every output present -> outputs-present",
          phases["redesign"]["drift"] == "outputs-present", phases["redesign"])
    check("an unstamped pending entry loses to the files that exist",
          phases["redesign"]["status"] == "completed"
          and phases["redesign"]["source"] == "derived", phases["redesign"])
    check("a pending entry with nothing written stays pending",
          phases["design-api"]["status"] == "pending"
          and phases["design-api"]["drift"] is None, phases["design-api"])
    check("agreement raises no drift", phases["investigate"]["drift"] is None)

    print("output counting")
    check("{project} glob resolves (2 of 4 investigate outputs)",
          (phases["investigate"]["written"], phases["investigate"]["declared"]) == (2, 4),
          phases["investigate"]["outputs"])
    check("extension outputs are counted per declared file (1 of 5 specs)",
          (phases["design-implementation"]["written"],
           phases["design-implementation"]["declared"]) == (1, 5),
          phases["design-implementation"]["outputs"])
    codegen = P.derive_codegen(root)["phases"]
    check("directory with a file counts as written",
          codegen["generate-infra-code"]["written"] == 1,
          codegen["generate-infra-code"]["outputs"])
    check("empty directory does not count",
          phases["generate-test-specs"]["written"] == 0,
          phases["generate-test-specs"]["outputs"])
    check("output bar reflects the fraction",
          P.output_bar(phases["investigate"]) == "[==..]",
          P.output_bar(phases["investigate"]))
    check("nothing declared -> blank bar",
          P.output_bar(codegen["generate-docs"]).strip() == "")

    print("exclusion")
    check("skip_phases excludes analyze-data-model",
          phases["analyze-data-model"]["status"] == "skipped"
          and phases["analyze-data-model"]["excluded"] == "option",
          phases["analyze-data-model"])
    check("scalardb_enabled=false skips the ScalarDB branch",
          phases["design-scalardb"]["status"] == "skipped"
          and phases["design-scalardb"]["excluded"] == "condition")
    check("and keeps the non-ScalarDB branch runnable",
          phases["design-data-layer"]["excluded"] is None)

    print("dependencies")
    check("unmet dependencies are listed (failed and pending both count)",
          phases["integrate-evaluations"]["blocked_by"] == ["evaluate-mmi",
                                                            "evaluate-ddd"],
          phases["integrate-evaluations"]["blocked_by"])
    check("skipped dependency counts as satisfied",
          "design-scalardb" not in phases["review-synthesizer"]["blocked_by"],
          phases["review-synthesizer"]["blocked_by"])
    check("runnable = pending/failed with every dependency met",
          phases["evaluate-ddd"]["runnable"] and not phases["redesign"]["runnable"],
          (phases["evaluate-ddd"]["runnable"], phases["redesign"]["blocked_by"]))
    check("next = the first runnable required phase, not an optional entry point",
          state["next"] == "evaluate-mmi"
          and phases["define-requirements"]["runnable"], state["next"])
    check("current = the in_progress core phase", state["current"] == "investigate")

    print("grouping")
    keys = [g["key"] for g in state["groups"]]
    check("extension tier is its own group", "extension" in keys, keys)
    check("extension group holds only extension phases",
          all(p["tier"] == "extension"
              for g in state["groups"] if g["key"] == "extension"
              for p in g["phases"]))
    check("core progress count excludes the extension tier",
          state["summary"]["total"] == sum(
              1 for p in phases.values() if p["tier"] == "core"),
          state["summary"]["total"])
    rows = P.flatten(state)
    check("flatten emits group headers and phase rows",
          rows[0][0]["kind"] == "group" and any(r[0]["kind"] == "phase" for r in rows))
    collapsed_rows = P.flatten(state, collapsed={keys[0]})
    check("a collapsed group hides its phases", len(collapsed_rows) < len(rows))
    core_rows = P.flatten(state, tier_filter="core")
    check("tier filter drops the extension group",
          all(r[0]["key"] != "extension" for r in core_rows))
    filtered = P.flatten(state, status_filter="failed")
    check("status filter keeps only matching phases",
          all(r[0]["phase"]["status"] == "failed"
              for r in filtered if r[0]["kind"] == "phase"))

    print("cost & activity")
    check("joined ledger key splits evenly across its phases",
          phases["evaluate-mmi"]["cost_usd"] == 1.5
          and phases["evaluate-ddd"]["cost_usd"] == 1.5,
          phases["evaluate-mmi"]["cost_usd"])
    check("_-prefixed ledger key is unassigned, not a phase",
          state["summary"]["unassigned_cost_usd"] == 0.5
          and state["summary"]["total_cost_usd"] == 4.5, state["summary"])
    check("recent token event marks the phase active",
          phases["investigate"]["active"], phases["investigate"]["last_activity"])
    check("an old event does not", not phases["evaluate-ddd"]["active"])
    check("rel_time formats an age", P.rel_time(
        datetime.now(timezone.utc).timestamp() - 125).endswith("m"))

    print("actions")
    cmd = P.default_action(state, phases["evaluate-ddd"])
    check("runnable phase defaults to running it",
          cmd[1] == "/architect:evaluate-ddd", cmd)
    cmd = P.default_action(state, phases["integrate-evaluations"])
    check("blocked phase defaults to its blocker",
          cmd[1] == "/architect:evaluate-mmi", cmd)
    acts = dict(P.actions_for(state, phases["investigate"]))
    check("architect offers resume/rerun from the phase",
          acts.get("resume from here") == "/architect:pipeline --resume-from=investigate"
          and "rerun from here" in acts, acts)
    prod_state = dict(state, plugin="product")
    acts = dict(P.actions_for(prod_state, phases["investigate"]))
    check("product commands use the /product: prefix and its orchestrator",
          acts["run phase"].startswith("/product:")
          and acts.get("resume pipeline") == "/product:start", acts)

    print("errors surface")
    check("registry errors are carried through", state["errors"], state["errors"])
    check("gate is None for architect", state["gate"] is None)
    gate = P.read_gate({"gates": {"validate-assumptions": {"verdict": "go",
                                                           "open_assumptions": ["A1"]}}})
    check("product gate verdict is read, carrying the pipeline that owns it",
          gate == {"verdict": "go", "plugin": "product", "open_assumptions": ["A1"]}, gate)


def check_sections(root):
    """product / architect / codegen are three separate trees, not one detected tree."""
    print("pipeline / codegen split")
    arch = P.load_phase_manifest("architect")
    prod = P.load_phase_manifest("product")
    check("every codegen phase is named in its manifest",
          all(n in arch for n in P.CODEGEN_PHASES["architect"])
          and all(n in prod for n in P.CODEGEN_PHASES["product"]),
          P.CODEGEN_PHASES)
    check("the manifests mark exactly those phases as codegen",
          {n for n, s in arch.items() if s["section"] == "codegen"}
          == set(P.CODEGEN_PHASES["architect"])
          and {n for n, s in prod.items() if s["section"] == "codegen"}
          == set(P.CODEGEN_PHASES["product"]),
          [n for n, s in arch.items() if s["section"] == "codegen"])
    check("generate-test-specs writes specs, so it stays in the pipeline",
          arch["generate-test-specs"]["section"] == "pipeline")

    pipeline = P.derive_all(root, plugin="architect")
    check("the pipeline tree holds no codegen phase",
          not any(n in pipeline["phases"] for n in P.CODEGEN_PHASES["architect"]),
          sorted(pipeline["phases"]))
    check("but the whole manifest is still there for dependencies to resolve against",
          all(n in pipeline["all_phases"] for n in P.CODEGEN_PHASES["architect"]))

    codegen = P.derive_codegen(root)
    check("the codegen tree holds only codegen phases",
          set(codegen["phases"]) <= (set(P.CODEGEN_PHASES["architect"])
                                     | set(P.CODEGEN_PHASES["product"])),
          sorted(codegen["phases"]))
    check("codegen groups by plugin, not by category",
          [g["key"] for g in codegen["groups"]] == ["architect"],
          [g["key"] for g in codegen["groups"]])
    check("a plugin that never ran gets no codegen group",
          "product" not in [g["key"] for g in codegen["groups"]])
    check("codegen dependencies still point at the design phases that feed them",
          codegen["phases"]["generate-scalardb-code"]["depends_on"]
          == ["design-implementation"],
          codegen["phases"]["generate-scalardb-code"]["depends_on"])
    check("codegen counts every phase, since the whole tier is manual",
          codegen["summary"]["total"] == len(codegen["phases"]),
          codegen["summary"])

    both = P.derive_codegen(root, plugins=["product", "architect"])
    check("asking for both plugins puts product first",
          [g["key"] for g in both["groups"]] == ["product", "architect"],
          [g["key"] for g in both["groups"]])
    frontend = both["phases"]["generate-frontend"]
    infra = both["phases"]["generate-infra-code"]
    check("each codegen phase carries the plugin it came from",
          (frontend["plugin"], infra["plugin"]) == ("product", "architect"),
          (frontend["plugin"], infra["plugin"]))
    check("and offers that plugin's slash command, not the view's",
          dict(P.actions_for(both, frontend))["run phase"]
          == "/product:generate-frontend"
          and dict(P.actions_for(both, infra))["run phase"]
          == "/architect:generate-infra-code",
          [P.actions_for(both, frontend)[0], P.actions_for(both, infra)[0]])
    check("the tier filter does not apply to the codegen tree",
          len(P.flatten(both, tier_filter="core")) == len(P.flatten(both)),
          len(P.flatten(both, tier_filter="core")))

    print("which pipelines this project ran")
    check("architect has evidence, product does not",
          P.derive_all(root, plugin="architect")["evidence"]
          and not P.derive_all(root, plugin="product")["evidence"])
    check("so only architect is offered a codegen group",
          P.codegen_plugins(root) == ["architect"], P.codegen_plugins(root))
    check("shared phase names are no evidence on their own",
          "design-api" not in P.exclusive_phases("product")
          and "define-vision" in P.exclusive_phases("product"))

    bare = tempfile.mkdtemp(prefix="nx-bare-")
    try:
        write(os.path.join(bare, "work", "pipeline-progress.json"),
              json.dumps({"gates": {"validate-assumptions": {}}, "phases": {}}))
        check("a freshly initialized project still falls back to its detected pipeline",
              P.codegen_plugins(bare) == ["product"], P.codegen_plugins(bare))
    finally:
        shutil.rmtree(bare, ignore_errors=True)


def check_backlog_strip(root):
    """The backlog tab's pipeline strip must agree with the pipeline tab beside it."""
    print("backlog view's pipeline strip")
    import backlog_status_data as B
    strip = B.load_pipeline(root)
    state = P.derive_all(root)
    registry_entries = len((P.load_progress(root) or {}).get("phases") or {})
    check("strip totals the manifest's phases, not the registry's entries",
          strip["total"] == state["summary"]["total"]
          and strip["total"] > registry_entries,
          (strip, registry_entries))
    check("strip's completed count matches the pipeline view",
          strip["completed"] == state["summary"]["completed"], strip)
    check("strip carries the current phase and the stale count",
          strip["current"] == state["current"]
          and strip["stale"] == state["summary"]["stale"], strip)
    bare = tempfile.mkdtemp(prefix="nx-no-pipeline-")
    try:
        check("a project with no pipeline gets no strip at all",
              B.load_pipeline(bare) is None)
    finally:
        shutil.rmtree(bare, ignore_errors=True)


def main():
    check_yaml_reader()
    check_real_manifests()
    check_extension_tier()
    if len(sys.argv) > 1:
        root, cleanup = os.path.abspath(sys.argv[1]), None
        print("checking %s" % root)
        state = P.derive_all(root)
        print("  plugin=%s phases=%d completed=%d/%d" % (
            state["plugin"], len(state["phases"]), state["summary"]["completed"],
            state["summary"]["total"]))
        check("the project has a progress registry or derivable outputs",
              state["has_progress"] or any(p["written"]
                                           for p in state["phases"].values()))
    else:
        root = tempfile.mkdtemp(prefix="nx-pipeline-status-")
        cleanup = root
        print("checking scratch fixture project at %s" % root)
        build_fixture(root)
        run(root)
        check_sections(root)
        check_backlog_strip(root)
        check_staleness(root)
        check_id_prefix_registry()
        check_conditional_outputs_and_gate(root)
        check_graphql_condition(root)
        check_shared_phase_names(root)
        check_hostile_inputs(root)
    if cleanup:
        shutil.rmtree(cleanup, ignore_errors=True)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
