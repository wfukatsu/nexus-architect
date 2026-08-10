"""Validation and rendering for API style and ScalarDB GraphQL decisions."""

import hashlib
import json

BASE_FIELDS = (
    "access_surface", "application_framework", "consumers", "operations", "selected_style",
    "client_variability", "cache_needs", "security_model", "transport", "execution_model",
    "data_access", "transaction_model", "operational_readiness", "rejected_alternatives",
    "requirement_ids", "rationale",
)
NATIVE_FIELDS = (
    "graphql_provider", "native_exposure", "approval", "pinned_product",
    "pinned_release", "contracted_edition", "control_evidence",
)
CONTROL_FIELDS = (
    "authentication", "authorization", "audit", "query_limits", "network_isolation",
)


def validate_document(document):
    """Return stable error strings for an api-style-decisions JSON document."""
    if not isinstance(document, dict):
        return ["document: must be an object with a surfaces array"]
    surfaces = document.get("surfaces")
    if not isinstance(surfaces, list):
        return ["document: surfaces must be an array"]
    if not surfaces:
        return ["document: surfaces must not be empty"]

    errors = []
    seen = set()
    for index, surface in enumerate(surfaces):
        prefix = "surfaces[%d]" % index
        if not isinstance(surface, dict):
            errors.append("%s: must be an object" % prefix)
            continue
        surface_id = surface.get("surface_id")
        if not isinstance(surface_id, str) or not surface_id.strip():
            errors.append("%s.surface_id: required" % prefix)
            surface_id = prefix
        elif surface_id in seen:
            errors.append("%s.surface_id: duplicate %s" % (prefix, surface_id))
        seen.add(surface_id)

        for field in BASE_FIELDS:
            if field not in surface or surface[field] is None:
                errors.append("%s.%s: required canonical decision field" %
                              (surface_id, field))
        if surface.get("selected_style") not in (
                "rest", "graphql", "hybrid", "grpc", "asyncapi"):
            errors.append("%s.selected_style: invalid value" % surface_id)

        scalardb_backed = surface.get("scalardb_backed")
        if not isinstance(scalardb_backed, bool):
            errors.append("%s.scalardb_backed: required boolean" % surface_id)
            # Keep validating provider/exposure contradictions instead of allowing
            # an invalid discriminator to suppress security checks.
            scalardb_backed = True

        provider = surface.get("graphql_provider")
        exposure = surface.get("native_exposure")
        if not scalardb_backed:
            if provider == "scalardb-native":
                errors.append("%s.graphql_provider: scalardb-native requires scalardb_backed true" %
                              surface_id)
            if exposure in ("internal", "external"):
                errors.append("%s.native_exposure: native exposure requires scalardb_backed true" %
                              surface_id)
            continue
        for field in NATIVE_FIELDS:
            if field not in surface:
                errors.append("%s.%s: required for ScalarDB-backed surface" %
                              (surface_id, field))

        if provider not in ("spring-for-graphql", "scalardb-native", "not-applicable"):
            errors.append("%s.graphql_provider: invalid value" % surface_id)
        if exposure not in ("none", "internal", "external"):
            errors.append("%s.native_exposure: invalid value" % surface_id)
        if provider != "scalardb-native" and exposure not in (None, "none"):
            errors.append("%s.native_exposure: only scalardb-native may be exposed" % surface_id)

        approval = surface.get("approval")
        if approval not in ("not-required", "rejected") and not (
                isinstance(approval, str) and approval.startswith("approved:")
                and approval.removeprefix("approved:").strip()):
            errors.append("%s.approval: invalid value" % surface_id)
        if not isinstance(surface.get("control_evidence"), dict):
            errors.append("%s.control_evidence: object required" % surface_id)
        for field in ("pinned_product", "pinned_release", "contracted_edition", "rationale"):
            value = surface.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append("%s.%s: non-empty value required" % (surface_id, field))

        if provider == "scalardb-native" and exposure in ("internal", "external"):
            if not isinstance(approval, str) or not approval.startswith("approved:") \
                    or not approval.removeprefix("approved:").strip():
                errors.append("%s.approval: approved:<decision-id> required" % surface_id)
            evidence = surface.get("control_evidence")
            if isinstance(evidence, dict):
                for control in CONTROL_FIELDS:
                    value = evidence.get(control)
                    if not isinstance(value, str) or not value.strip():
                        errors.append("%s.control_evidence.%s: reference required" %
                                      (surface_id, control))
    return errors


def canonical_json(document):
    """Return the stable serialization used to identify the canonical source."""
    return json.dumps(document, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _cell(value):
    if value is None:
        return "—"
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(document, language="en"):
    """Render the human-readable projection from canonical JSON."""
    digest = hashlib.sha256(canonical_json(document).encode("utf-8")).hexdigest()
    ja = language == "ja"
    title = "APIスタイル決定" if ja else "API Style Decisions"
    note = ("このレポートは `api-style-decisions.json` から生成されています。直接編集しないでください。"
            if ja else
            "This report is generated from `api-style-decisions.json`. Do not edit it directly.")
    headers = (["サーフェス", "スタイル", "GraphQLプロバイダー", "ネイティブ公開",
                "フレームワーク", "データアクセス", "トランザクション", "承認"]
               if ja else
               ["Surface", "Style", "GraphQL provider", "Native exposure",
                "Framework", "Data access", "Transaction", "Approval"])
    lines = [
        "---", "title: \"%s\"" % title, "schema_version: \"1.0\"",
        "skill: design-api", "canonical_source: reports/03_design/api-style-decisions.json",
        "source_sha256: %s" % digest, "---", "", "# %s" % title, "", note, "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    surfaces = document.get("surfaces", [])
    for surface in surfaces:
        transaction = surface.get("transaction_model", surface.get("transaction"))
        values = [surface.get("surface_id"), surface.get("selected_style"),
                  surface.get("graphql_provider"), surface.get("native_exposure"),
                  surface.get("application_framework"), surface.get("data_access"),
                  transaction, surface.get("approval")]
        lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
    lines.append("")
    return "\n".join(lines)
