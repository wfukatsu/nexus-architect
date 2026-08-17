"""Validation and rendering for API style and ScalarDB GraphQL decisions."""

import hashlib
import html
import json
import os
import re

MAX_DOCUMENT_BYTES = 1_000_000
MAX_SURFACES = 100
MAX_COLLECTION_ITEMS = 500
MAX_NESTING = 12
MAX_RENDERED_BYTES = 2_000_000

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


def validate_limits(document):
    errors = []
    stack = [(document, 0, "document")]
    while stack:
        value, depth, path = stack.pop()
        if depth > MAX_NESTING:
            errors.append("%s: nesting exceeds %d" % (path, MAX_NESTING))
            continue
        if isinstance(value, dict):
            if len(value) > MAX_COLLECTION_ITEMS:
                errors.append("%s: object exceeds %d entries" % (path, MAX_COLLECTION_ITEMS))
            stack.extend((item, depth + 1, "%s.%s" % (path, key))
                         for key, item in value.items())
        elif isinstance(value, list):
            if len(value) > MAX_COLLECTION_ITEMS:
                errors.append("%s: array exceeds %d items" % (path, MAX_COLLECTION_ITEMS))
            stack.extend((item, depth + 1, "%s[%d]" % (path, index))
                         for index, item in enumerate(value))
    return errors


def validate_document(document, project_dir=None, okf_root=None):
    """Return stable error strings for an api-style-decisions JSON document."""
    if not isinstance(document, dict):
        return ["document: must be an object with a surfaces array"]
    limit_errors = validate_limits(document)
    if limit_errors:
        return limit_errors
    surfaces = document.get("surfaces")
    if not isinstance(surfaces, list):
        return ["document: surfaces must be an array"]
    if not surfaces:
        return ["document: surfaces must not be empty"]
    if len(surfaces) > MAX_SURFACES:
        return ["document: surfaces exceeds %d" % MAX_SURFACES]

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
                    if not isinstance(value, dict) or not isinstance(value.get("path"), str) \
                            or not value["path"].strip():
                        errors.append("%s.control_evidence.%s: {path, anchor?} reference required" %
                                      (surface_id, control))
            if project_dir:
                errors.extend(_validate_native_references(surface, surface_id, project_dir,
                                                           okf_root))
    return errors


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _validate_native_references(surface, surface_id, project_dir, okf_root):
    errors = []
    approval_id = surface.get("approval", "").removeprefix("approved:")
    approvals = _read_json(os.path.join(project_dir, "reports", "03_design",
                                        "api-style-approvals.json")) or {}
    approval_entries = approvals.get("approvals", []) if isinstance(approvals, dict) else []
    matches = [entry for entry in approval_entries
               if isinstance(entry, dict) and entry.get("decision_id") == approval_id]
    owner = matches[0].get("approved_by") if len(matches) == 1 else None
    approved_at = matches[0].get("approved_at") if len(matches) == 1 else None
    if len(matches) != 1 or not isinstance(owner, str) or not owner.strip() or not (
            isinstance(approved_at, str) and re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
                approved_at)):
        errors.append("%s.approval: decision does not resolve to one recorded human approval" %
                      surface_id)

    versions = _read_json(os.path.join(project_dir, "work", "version-decisions.json")) or {}
    version_entries = versions.get("entries", []) if isinstance(versions, dict) else []
    version_matches = [entry for entry in version_entries
                       if isinstance(entry, dict) and entry.get("name") in
                       ("scalardb", "com.scalar-labs:scalardb") and entry.get("verified") is True]
    chosen = str(version_matches[0].get("chosen", "")) if len(version_matches) == 1 else ""
    pinned = str(surface.get("pinned_release", ""))
    chosen_line = ".".join(chosen.split(".")[:2])
    pinned_line = ".".join(pinned.split(".")[:2])
    if not chosen or chosen_line != pinned_line:
        errors.append("%s.pinned_release: does not match verified version decision" % surface_id)
    if surface.get("pinned_product") != "ScalarDB":
        errors.append("%s.pinned_product: must resolve to ScalarDB" % surface_id)
    release_line = pinned_line
    # Only assert the pinned line resolves when the bundle is actually present. The knowledge
    # bundle is a git submodule, so a clone without --recurse-submodules has the path but not the
    # content — and reporting "this ScalarDB release does not document GraphQL" when the truth is
    # "the documentation is not checked out here" blames the design decision for a missing input.
    # The caller says so out loud instead (tools/validate-api-style-decisions.py).
    if okf_root and os.path.isdir(okf_root):
        graphql_index = os.path.join(okf_root, "products", "scalardb", release_line,
                                     "scalardb-graphql", "index.md")
        if not os.path.isfile(graphql_index):
            errors.append("%s.pinned_release: ScalarDB GraphQL is not resolved in pinned OKF line" %
                          surface_id)

    edition_path = os.path.join(project_dir, "reports", "03_design",
                                "scalardb-edition-selection.md")
    try:
        with open(edition_path, encoding="utf-8") as handle:
            edition_text = handle.read()
    except OSError:
        edition_text = ""
    if surface.get("contracted_edition") not in edition_text:
        errors.append("%s.contracted_edition: does not resolve to edition selection" % surface_id)

    for control in CONTROL_FIELDS:
        ref = (surface.get("control_evidence") or {}).get(control)
        if not isinstance(ref, dict):
            continue
        rel = ref.get("path", "")
        target = os.path.realpath(os.path.join(project_dir, rel))
        root = os.path.realpath(project_dir) + os.sep
        if not target.startswith(root) or not os.path.isfile(target):
            errors.append("%s.control_evidence.%s: path does not resolve inside project" %
                          (surface_id, control))
            continue
        anchor = ref.get("anchor")
        if anchor:
            try:
                with open(target, encoding="utf-8") as handle:
                    content = handle.read()
            except OSError:
                content = ""
            if str(anchor) not in content:
                errors.append("%s.control_evidence.%s: anchor does not resolve" %
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
    rendered = "\n".join(lines)
    if len(rendered.encode("utf-8")) > MAX_RENDERED_BYTES:
        raise ValueError("rendered report exceeds %d bytes" % MAX_RENDERED_BYTES)
    return rendered
