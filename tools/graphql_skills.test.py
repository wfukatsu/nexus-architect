#!/usr/bin/env python3
"""Static contract checks for the Spring for GraphQL skill chain."""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "lib"))
import pipeline_status_data as pipeline  # noqa: E402
from api_style_decisions import render_markdown, validate_document  # noqa: E402

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


def decision_surface(**overrides):
    surface = {
        "surface_id": "surface", "scalardb_backed": True,
        "access_surface": "external", "application_framework": "Spring for GraphQL",
        "consumers": ["web"], "operations": ["Query.customer"],
        "selected_style": "graphql", "client_variability": "multiple projections",
        "cache_needs": "application cache", "security_model": "OIDC + field authorization",
        "transport": "HTTP", "execution_model": "Spring MVC", "data_access": "ScalarDB",
        "transaction_model": "ScalarDB transaction", "operational_readiness": "ready",
        "rejected_alternatives": ["native GraphQL"], "requirement_ids": ["FR-001"],
        "rationale": "application security boundary",
        "graphql_provider": "spring-for-graphql", "native_exposure": "none",
        "approval": "not-required", "pinned_product": "ScalarDB",
        "pinned_release": "verified-release", "contracted_edition": "verified-edition",
        "control_evidence": {},
    }
    surface.update(overrides)
    return surface


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
    check("generator is conditioned on the canonical decision",
          pipeline.EXTENSION_PHASES["generate-graphql-code"].get("conditions")
          == ["api_style_graphql"])

    # `design-graphql` skipped satisfies the dependency, so only the condition keeps the
    # codegen view from offering GraphQL generation on a REST-only project.
    def codegen_state(document, phase_name="generate-graphql-code"):
        with tempfile.TemporaryDirectory() as project:
            os.makedirs(os.path.join(project, "reports", "03_design"))
            if document is not None:
                with open(os.path.join(project, "reports", "03_design",
                                       "api-style-decisions.json"), "w",
                          encoding="utf-8") as handle:
                    handle.write(document)
            progress = {"project_name": "p", "options": {"scalardb_enabled": True},
                        "phases": {name: {"status": "completed", "plugin": "architect"}
                                   for name in ("design-api", "design-implementation")}}
            derived = pipeline.derive_all(project, plugin="architect", progress=progress,
                                          section="codegen")
            for group in derived["groups"]:
                for phase in group["phases"]:
                    if phase["name"] == phase_name:
                        return phase
        return None

    rest_only = json.dumps({"surfaces": [decision_surface(
        selected_style="rest", graphql_provider="not-applicable")]})
    graphql = json.dumps({"surfaces": [decision_surface()]})
    rest_state = codegen_state(rest_only)
    graphql_state = codegen_state(graphql)
    invalid_state = codegen_state("{ not json")
    check("REST-only decision withdraws the GraphQL generator",
          rest_state["excluded"] == "condition" and not rest_state["runnable"],
          rest_state)
    check("GraphQL decision keeps the generator, waiting on its design phase",
          graphql_state["excluded"] is None
          and graphql_state["blocked_by"] == ["design-graphql"],
          graphql_state)
    check("invalid decision fails the generator instead of offering it",
          invalid_state["status"] == "failed" and not invalid_state["runnable"],
          invalid_state)

    # The mirror rule: a GraphQL-only decision withdraws the REST generator. Absent any
    # decision it stays, because REST codegen predates the canonical artifact.
    rest_gen_graphql_only = codegen_state(graphql, "generate-api-code")
    rest_gen_rest_only = codegen_state(rest_only, "generate-api-code")
    rest_gen_legacy = codegen_state(None, "generate-api-code")
    rest_gen_invalid = codegen_state("{ not json", "generate-api-code")
    check("GraphQL-only decision withdraws the REST generator",
          rest_gen_graphql_only["excluded"] == "condition", rest_gen_graphql_only)
    check("REST decision keeps the REST generator",
          rest_gen_rest_only["excluded"] is None and rest_gen_rest_only["runnable"],
          rest_gen_rest_only)
    check("a project predating the canonical artifact keeps the REST generator",
          rest_gen_legacy["excluded"] is None and rest_gen_legacy["runnable"],
          rest_gen_legacy)
    check("invalid decision fails the REST generator too",
          rest_gen_invalid["status"] == "failed" and not rest_gen_invalid["runnable"],
          rest_gen_invalid)
    hybrid = json.dumps({"surfaces": [decision_surface(selected_style="hybrid")]})
    check("a hybrid surface keeps both generators",
          codegen_state(hybrid)["excluded"] is None
          and codegen_state(hybrid, "generate-api-code")["excluded"] is None)

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
    check("ScalarDB applicability is explicit and fail-closed",
          "scalardb_backed" in selection_rule
          and "required boolean" in read("tools/lib/api_style_decisions.py"))
    check("native exposure without approval and controls is critical",
          "critical" in security_review.lower()
          and "approved:<decision-id>" in security_review
          and all(control in security_review for control in
                  ("authentication", "authorization", "audit", "query limits",
                   "network isolation")))
    spring_surface = {"surfaces": [decision_surface(surface_id="customer-api")]}
    check("Spring facade decision fixture validates",
          validate_document(spring_surface) == [], validate_document(spring_surface))
    check("canonical decision list cannot be empty",
          validate_document({"surfaces": []}) ==
          ["document: surfaces must not be empty"],
          validate_document({"surfaces": []}))
    check("canonical document requires the object envelope",
          validate_document([]) ==
          ["document: must be an object with a surfaces array"], validate_document([]))
    for field in (
            "access_surface", "application_framework", "selected_style", "client_variability", "cache_needs",
            "security_model", "transport", "execution_model", "data_access",
            "transaction_model", "operational_readiness", "rationale"):
        wrong = {"surfaces": [decision_surface(**{field: []})]}
        check("canonical string field rejects wrong type: %s" % field,
              any((".%s:" % field) in error for error in validate_document(wrong)),
              validate_document(wrong))
    for field in ("consumers", "operations", "rejected_alternatives", "requirement_ids"):
        wrong = {"surfaces": [decision_surface(**{field: "not-an-array"})]}
        check("canonical array field rejects scalar: %s" % field,
              any((".%s:" % field) in error for error in validate_document(wrong)),
              validate_document(wrong))
        empty_item = {"surfaces": [decision_surface(**{field: [""]})]}
        check("canonical array field rejects empty item: %s" % field,
              any((".%s:" % field) in error for error in validate_document(empty_item)),
              validate_document(empty_item))
    invalid_id = {"surfaces": [decision_surface(surface_id="bad id|row")]}
    check("surface ID enforces the stable identifier shape",
          any("invalid stable identifier" in error for error in validate_document(invalid_id)),
          validate_document(invalid_id))
    approved_native = {"surfaces": [decision_surface(
        surface_id="admin-api", graphql_provider="scalardb-native",
        native_exposure="internal", approval="approved:ADR-042",
        control_evidence={
            "authentication": {"path": "reports/security.md", "anchor": "SEC-1"},
            "authorization": {"path": "reports/security.md", "anchor": "SEC-2"},
            "audit": {"path": "reports/security.md", "anchor": "SEC-3"},
            "query_limits": {"path": "reports/security.md", "anchor": "SEC-4"},
            "network_isolation": {"path": "reports/security.md", "anchor": "SEC-5"}},
        rationale="approved internal administration",
    )]}
    check("approved internal native decision fixture validates",
          validate_document(approved_native) == [], validate_document(approved_native))
    missing_surface = decision_surface(
        surface_id="bypass", graphql_provider="scalardb-native",
        native_exposure="external")
    del missing_surface["scalardb_backed"]
    missing_flag = {"surfaces": [missing_surface]}
    missing_flag_errors = validate_document(missing_flag)
    check("omitting ScalarDB applicability cannot bypass native checks",
          any("scalardb_backed" in error for error in missing_flag_errors)
          and any("approval" in error for error in missing_flag_errors),
          missing_flag_errors)
    false_native = {"surfaces": [decision_surface(
        surface_id="contradiction", scalardb_backed=False,
        graphql_provider="scalardb-native", native_exposure="external")]}
    check("non-ScalarDB surface cannot select native provider",
          len(validate_document(false_native)) >= 2, validate_document(false_native))
    for bad_value in (None, "true", 1):
        bad_type = {"surfaces": [decision_surface(
            surface_id="bad-type", scalardb_backed=bad_value)]}
        check("ScalarDB applicability rejects %r" % bad_value,
              any("required boolean" in error for error in validate_document(bad_type)),
              validate_document(bad_type))
    unsafe_external = {"surfaces": [decision_surface(
        surface_id="public-api", graphql_provider="scalardb-native",
        native_exposure="external", approval="not-required", control_evidence={},
        rationale="convenience")]}
    unsafe_errors = validate_document(unsafe_external)
    check("unapproved external native decision fixture is rejected",
          any("approval" in error for error in unsafe_errors)
          and all(any(control in error for error in unsafe_errors)
                  for control in ("authentication", "authorization", "audit",
                                  "query_limits", "network_isolation")), unsafe_errors)
    rendered = render_markdown(approved_native, "ja")
    check("Markdown projection is deterministic and identifies canonical JSON",
          rendered == render_markdown(approved_native, "ja")
          and "canonical_source: reports/03_design/api-style-decisions.json" in rendered
          and "source_sha256:" in rendered)
    check("Markdown projection exposes every canonical decision field",
          all(("`%s`" % field) in rendered for field in (
              "consumers", "operations", "security_model", "control_evidence", "rationale",
              "rejected_alternatives", "operational_readiness", "requirement_ids")))
    check("Markdown projection includes decision evidence values",
          all(value in rendered for value in (
              "approved internal administration", "OIDC + field authorization",
              "SEC-1", "native GraphQL", "FR-001")))
    hostile = {"surfaces": [decision_surface(
        rationale="<script>alert(1)</script>|row\nnext`code`",
        control_evidence={"note": "a|b\r\nc"})]}
    hostile_rendered = render_markdown(hostile, "en")
    check("Markdown projection escapes structural and HTML metacharacters",
          "<script>" not in hostile_rendered
          and "&#124;" in hostile_rendered and "&#96;" in hostile_rendered
          and "<br>" in hostile_rendered, hostile_rendered)
    check("downstream skills consume canonical JSON",
          "api-style-decisions.json" in design_skill
          and "api-style-decisions.json" in generator_skill
          and "api-style-decisions.md" not in design_skill
          and "api-style-decisions.md" not in generator_skill)
    check("plugin-owned validator uses plugin root",
          '${CLAUDE_PLUGIN_ROOT}/tools/validate-api-style-decisions.py' in design_api_skill
          and '${CLAUDE_PLUGIN_ROOT}/tools/validate-api-style-decisions.py' in security_review)

    with tempfile.TemporaryDirectory() as external_project:
        report_dir = os.path.join(external_project, "reports", "03_design")
        os.makedirs(report_dir)
        json_path = os.path.join(report_dir, "api-style-decisions.json")
        md_path = os.path.join(report_dir, "api-style-decisions.md")
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(spring_surface, handle)
        validator = os.path.join(ROOT, "tools", "validate-api-style-decisions.py")
        result = subprocess.run(
            [sys.executable, validator, json_path, "--render-markdown", md_path,
             "--lang", "en"], cwd=external_project, capture_output=True, text=True)
        check("validator runs from an external consumer workspace",
              result.returncode == 0 and os.path.isfile(md_path),
              result.stderr or result.stdout)
        frontmatter = subprocess.run(
            [os.path.join(ROOT, "hooks", "validate-frontmatter.sh"), md_path],
            cwd=external_project, capture_output=True, text=True)
        mermaid = subprocess.run(
            [os.path.join(ROOT, "hooks", "validate-mermaid.sh"), md_path],
            cwd=external_project, capture_output=True, text=True)
        check("rendered Markdown passes report hooks",
              frontmatter.returncode == 0 and mermaid.returncode == 0,
              frontmatter.stderr or mermaid.stderr)
        ja_path = os.path.join(report_dir, "api-style-decisions-ja.md")
        ja_result = subprocess.run(
            [sys.executable, validator, json_path, "--render-markdown", ja_path,
             "--lang", "ja"], cwd=external_project, capture_output=True, text=True)
        ja_frontmatter = subprocess.run(
            [os.path.join(ROOT, "hooks", "validate-frontmatter.sh"), ja_path],
            cwd=external_project, capture_output=True, text=True)
        ja_mermaid = subprocess.run(
            [os.path.join(ROOT, "hooks", "validate-mermaid.sh"), ja_path],
            cwd=external_project, capture_output=True, text=True)
        check("Japanese rendered Markdown passes report hooks",
              ja_result.returncode == 0 and ja_frontmatter.returncode == 0
              and ja_mermaid.returncode == 0,
              ja_result.stderr or ja_frontmatter.stderr or ja_mermaid.stderr)
        security_path = os.path.join(external_project, "reports", "security.md")
        with open(security_path, "w", encoding="utf-8") as handle:
            handle.write("SEC-1\nSEC-2\nSEC-3\nSEC-4\nSEC-5\n")
        with open(os.path.join(report_dir, "api-style-approvals.json"), "w",
                  encoding="utf-8") as handle:
            json.dump({"approvals": [{"decision_id": "ADR-042", "approved_by": "user",
                                      "approved_at": "2026-08-12T00:00:00Z"}]}, handle)
        with open(os.path.join(report_dir, "scalardb-edition-selection.md"), "w",
                  encoding="utf-8") as handle:
            handle.write("Enterprise Premium")
        work_dir = os.path.join(external_project, "work")
        os.makedirs(work_dir)
        with open(os.path.join(work_dir, "version-decisions.json"), "w",
                  encoding="utf-8") as handle:
            json.dump({"entries": [{"name": "com.scalar-labs:scalardb",
                                    "chosen": "3.19.0", "verified": True}]}, handle)
        resolved_native = {"surfaces": [decision_surface(
            surface_id="native", graphql_provider="scalardb-native",
            native_exposure="external", approval="approved:ADR-042",
            pinned_release="3.19", contracted_edition="Enterprise Premium",
            control_evidence={control: {"path": "reports/security.md",
                                        "anchor": "SEC-%d" % (index + 1)}
                              for index, control in enumerate(
                                  ("authentication", "authorization", "audit",
                                   "query_limits", "network_isolation"))})]}
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(resolved_native, handle)
        resolved = subprocess.run([sys.executable, validator, json_path], cwd=external_project,
                                  capture_output=True, text=True)
        check("native approval, version, edition and controls resolve",
              resolved.returncode == 0, resolved.stderr or resolved.stdout)

        # The OKF bundle is a submodule, so a clone without it — CI, a plugin install, a
        # contributor who skipped --recurse-submodules — must not turn a missing input into a
        # verdict on the design. It is skipped, and the skip is announced.
        with tempfile.TemporaryDirectory() as bundleless:
            os.makedirs(os.path.join(bundleless, "tools", "lib"))
            shutil.copy(validator, os.path.join(bundleless, "tools"))
            for module in os.listdir(os.path.join(ROOT, "tools", "lib")):
                if module.endswith(".py"):
                    shutil.copy(os.path.join(ROOT, "tools", "lib", module),
                                os.path.join(bundleless, "tools", "lib"))
            without_bundle = subprocess.run(
                [sys.executable, os.path.join(bundleless, "tools",
                                              os.path.basename(validator)), json_path],
                cwd=external_project, capture_output=True, text=True)
            check("a checkout without the OKF bundle skips pinned-line resolution",
                  without_bundle.returncode == 0
                  and "is not resolved in pinned OKF line" not in without_bundle.stderr,
                  without_bundle.stderr or without_bundle.stdout)
            check("the skipped check is announced rather than silent",
                  "OKF knowledge bundle is not checked out" in without_bundle.stderr,
                  without_bundle.stderr)
        fabricated = resolved_native.copy()
        fabricated = json.loads(json.dumps(fabricated))
        fabricated["surfaces"][0]["approval"] = "approved:DOES-NOT-EXIST"
        fabricated["surfaces"][0]["pinned_release"] = "99.99"
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(fabricated, handle)
        rejected = subprocess.run([sys.executable, validator, json_path], cwd=external_project,
                                  capture_output=True, text=True)
        check("fabricated native evidence is rejected",
              rejected.returncode == 1 and "does not resolve" in rejected.stderr,
              rejected.stderr or rejected.stdout)

        with open(md_path, "w", encoding="utf-8") as handle:
            handle.write("ORIGINAL")
        deeply_nested = decision_surface()
        nested = "leaf"
        for _ in range(20):
            nested = {"x": nested}
        deeply_nested["control_evidence"] = nested
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump({"surfaces": [deeply_nested]}, handle)
        bounded = subprocess.run(
            [sys.executable, validator, json_path, "--render-markdown", md_path],
            cwd=external_project, capture_output=True, text=True)
        with open(md_path, encoding="utf-8") as handle:
            preserved = handle.read()
        check("bounded failure preserves the previous report",
              bounded.returncode == 1 and preserved == "ORIGINAL",
              bounded.stderr or bounded.stdout)
        invalid_path = os.path.join(report_dir, "invalid.json")
        with open(invalid_path, "w", encoding="utf-8") as handle:
            json.dump(missing_flag, handle)
        invalid = subprocess.run([sys.executable, validator, invalid_path],
                                 cwd=external_project, capture_output=True, text=True)
        check("validator preserves invalid-contract exit code",
              invalid.returncode == 1, invalid.stderr or invalid.stdout)
        unreadable = subprocess.run(
            [sys.executable, validator, os.path.join(report_dir, "missing.json")],
            cwd=external_project, capture_output=True, text=True)
        check("validator preserves unreadable-input exit code",
              unreadable.returncode == 2, unreadable.stderr or unreadable.stdout)
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
