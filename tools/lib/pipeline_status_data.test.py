#!/usr/bin/env python3
"""Executable check of the pipeline-status derivation contract.

pipeline_status_data.py encodes how the dashboard reads a project's pipeline state;
this asserts those rules as behaviour, against a scratch project it builds itself:

- the shipped skill-dependencies.yaml files parse with the built-in mini-YAML reader
  (both plugins, including wrapped inline lists and inline maps);
- status precedence: the progress registry wins, the filesystem fills the gap, and the
  two disagreeing raises drift (completed with nothing written / pending with all
  outputs present);
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
import shutil
import sys
import tempfile
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
    # design-implementation (extension tier): directory output with a file in it
    write(os.path.join(root, "reports", "06_implementation", "value-objects-spec.md"))
    # generate-test-specs (extension tier): directory exists but is empty -> not written
    os.makedirs(os.path.join(root, "reports", "07_test-specs"), exist_ok=True)
    # map-domains: registry claims completed, nothing on disk -> drift
    # redesign: registry says pending, both outputs present -> the other drift
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
            "map-domains": {"status": "completed", "completed_at": "2026-08-06T09:30:00Z"},
            "redesign": {"status": "pending"},
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
          phases["map-domains"]["drift"] == "outputs-missing", phases["map-domains"])
    check("pending with every output present -> outputs-present",
          phases["redesign"]["drift"] == "outputs-present"
          and phases["redesign"]["status"] == "pending", phases["redesign"])
    check("agreement raises no drift", phases["investigate"]["drift"] is None)

    print("output counting")
    check("{project} glob resolves (2 of 4 investigate outputs)",
          (phases["investigate"]["written"], phases["investigate"]["declared"]) == (2, 4),
          phases["investigate"]["outputs"])
    check("directory with a file counts as written",
          phases["design-implementation"]["written"] == 1)
    check("empty directory does not count",
          phases["generate-test-specs"]["written"] == 0,
          phases["generate-test-specs"]["outputs"])
    check("output bar reflects the fraction",
          P.output_bar(phases["investigate"]) == "[==..]",
          P.output_bar(phases["investigate"]))
    check("nothing declared -> blank bar",
          P.output_bar(phases["generate-docs"]).strip() == "")

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
    check("product gate verdict is read",
          gate == {"verdict": "go", "open_assumptions": ["A1"]}, gate)


def main():
    check_yaml_reader()
    check_real_manifests()
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
        check_hostile_inputs(root)
    if cleanup:
        shutil.rmtree(cleanup, ignore_errors=True)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
