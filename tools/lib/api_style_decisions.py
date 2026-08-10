"""Validation for machine-readable API style and ScalarDB GraphQL decisions."""

NATIVE_FIELDS = (
    "graphql_provider", "native_exposure", "approval", "pinned_product",
    "pinned_release", "contracted_edition", "control_evidence", "rationale",
)
CONTROL_FIELDS = (
    "authentication", "authorization", "audit", "query_limits", "network_isolation",
)


def validate_document(document):
    """Return stable error strings for an api-style-decisions JSON document."""
    surfaces = document.get("surfaces") if isinstance(document, dict) else document
    if not isinstance(surfaces, list):
        return ["document: surfaces must be an array"]

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

        if not surface.get("scalardb_backed", False):
            continue
        for field in NATIVE_FIELDS:
            if field not in surface:
                errors.append("%s.%s: required for ScalarDB-backed surface" %
                              (surface_id, field))

        provider = surface.get("graphql_provider")
        exposure = surface.get("native_exposure")
        if provider not in ("spring-for-graphql", "scalardb-native", "not-applicable"):
            errors.append("%s.graphql_provider: invalid value" % surface_id)
        if exposure not in ("none", "internal", "external"):
            errors.append("%s.native_exposure: invalid value" % surface_id)
        if provider != "scalardb-native" and exposure not in (None, "none"):
            errors.append("%s.native_exposure: only scalardb-native may be exposed" % surface_id)

        if provider == "scalardb-native" and exposure in ("internal", "external"):
            approval = surface.get("approval")
            if not isinstance(approval, str) or not approval.startswith("approved:") \
                    or not approval.removeprefix("approved:").strip():
                errors.append("%s.approval: approved:<decision-id> required" % surface_id)
            evidence = surface.get("control_evidence")
            if not isinstance(evidence, dict):
                errors.append("%s.control_evidence: object required" % surface_id)
            else:
                for control in CONTROL_FIELDS:
                    value = evidence.get(control)
                    if not isinstance(value, str) or not value.strip():
                        errors.append("%s.control_evidence.%s: reference required" %
                                      (surface_id, control))
            for field in ("pinned_product", "pinned_release", "contracted_edition", "rationale"):
                value = surface.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append("%s.%s: non-empty value required" % (surface_id, field))
    return errors
