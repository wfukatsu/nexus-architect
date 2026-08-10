"""Validation and rendering for API style and ScalarDB GraphQL decisions."""

import hashlib
import html
import json
import re

STRING_FIELDS = (
    "access_surface", "application_framework", "selected_style", "client_variability",
    "cache_needs", "security_model", "transport", "execution_model", "data_access",
    "transaction_model", "operational_readiness", "rationale",
)
STRING_LIST_FIELDS = (
    "consumers", "operations", "rejected_alternatives", "requirement_ids",
)
NATIVE_FIELDS = (
    "graphql_provider", "native_exposure", "approval", "pinned_product",
    "pinned_release", "contracted_edition", "control_evidence",
)
CONTROL_FIELDS = (
    "authentication", "authorization", "audit", "query_limits", "network_isolation",
)
DETAIL_FIELDS = (
    "scalardb_backed", "access_surface", "application_framework", "consumers", "operations",
    "selected_style", "client_variability", "cache_needs", "security_model", "transport",
    "execution_model", "data_access", "transaction_model", "operational_readiness",
    "rejected_alternatives", "requirement_ids", "rationale", "graphql_provider",
    "native_exposure", "approval", "pinned_product", "pinned_release", "contracted_edition",
    "control_evidence",
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
        elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", surface_id):
            errors.append("%s.surface_id: invalid stable identifier" % prefix)
        elif surface_id in seen:
            errors.append("%s.surface_id: duplicate %s" % (prefix, surface_id))
        seen.add(surface_id)

        for field in STRING_FIELDS:
            value = surface.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append("%s.%s: required non-empty string" % (surface_id, field))
        for field in STRING_LIST_FIELDS:
            value = surface.get(field)
            if not isinstance(value, list) or not value or not all(
                    isinstance(item, str) and item.strip() for item in value):
                errors.append("%s.%s: required non-empty string array" % (surface_id, field))
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
    if isinstance(value, list):
        return "<br>".join(_cell(item) for item in value)
    if isinstance(value, dict):
        return "<br>".join("%s: %s" % (_cell(key), _cell(value[key]))
                           for key in sorted(value, key=lambda item: str(item))) or "{}"
    escaped = html.escape(str(value), quote=True)
    return (escaped.replace("|", "&#124;").replace("`", "&#96;")
            .replace("\r\n", "<br>").replace("\r", "<br>").replace("\n", "<br>"))


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
    # Frontmatter per @rules/output-conventions.md, with one deliberate omission:
    # `generated_at` would make an unchanged decision render differently on every run, and
    # this projection is asserted to be byte-stable. `source_sha256` identifies the exact
    # input it was rendered from, which is the stronger claim a timestamp only approximates.
    lines = [
        "---", "title: \"%s\"" % title, "schema_version: 1",
        "phase: \"Phase 3: Design\"",
        "skill: design-api", "input_files:",
        "  - reports/03_design/api-style-decisions.json",
        "canonical_source: reports/03_design/api-style-decisions.json",
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
    detail_title = "判断根拠" if ja else "Decision Evidence"
    field_header = "フィールド" if ja else "Field"
    value_header = "値" if ja else "Value"
    for surface in surfaces:
        lines.extend([
            "", "## %s: %s" % (detail_title, _cell(surface.get("surface_id"))), "",
            "| %s | %s |" % (field_header, value_header), "|---|---|",
        ])
        for field in DETAIL_FIELDS:
            lines.append("| `%s` | %s |" % (field, _cell(surface.get(field))))
    lines.append("")
    return "\n".join(lines)
