"""Validation for multi-surface GraphQL design completion evidence."""

import json
import os

ARTIFACT_FIELDS = ("resolver_contracts", "authorization_matrix", "batch_loading_plan",
                   "query_governance", "transport_design")


def _inside_file(project_dir, relative):
    if not isinstance(relative, str) or not relative.strip():
        return False
    root = os.path.realpath(project_dir) + os.sep
    path = os.path.realpath(os.path.join(project_dir, relative))
    return path.startswith(root) and os.path.isfile(path) and os.path.getsize(path) > 0


def validate_graphql_design_manifest(decisions, manifest, project_dir):
    expected = {surface["surface_id"] for surface in decisions.get("surfaces", [])
                if surface.get("selected_style") in ("graphql", "hybrid")}
    if not isinstance(manifest, dict) or not isinstance(manifest.get("surfaces"), list):
        return ["graphql design manifest: surfaces must be an array"]
    errors, schemas = [], set()
    entries = manifest["surfaces"]
    ids = [entry.get("surface_id") for entry in entries if isinstance(entry, dict)]
    if len(ids) != len(set(ids)):
        errors.append("graphql design manifest: duplicate surface_id")
    if set(ids) != expected:
        errors.append("graphql design manifest: surface set mismatch expected=%s actual=%s" %
                      (sorted(expected), sorted(str(item) for item in set(ids))))
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("graphql design manifest: entry must be an object")
            continue
        surface_id, schema = entry.get("surface_id", "<missing>"), entry.get("schema")
        if schema in schemas:
            errors.append("%s.schema: schema path must be unique" % surface_id)
        schemas.add(schema)
        if not _inside_file(project_dir, schema):
            errors.append("%s.schema: non-empty file must resolve inside project" % surface_id)
        for field in ARTIFACT_FIELDS:
            if not _inside_file(project_dir, entry.get(field)):
                errors.append("%s.%s: non-empty file must resolve inside project" %
                              (surface_id, field))
    schema_dir = os.path.join(project_dir, "reports", "03_design", "api-specifications", "graphql")
    discovered = set()
    if os.path.isdir(schema_dir):
        for name in os.listdir(schema_dir):
            if name.endswith((".graphqls", ".gqls")):
                discovered.add(os.path.relpath(os.path.join(schema_dir, name), project_dir))
    if discovered != schemas:
        errors.append("graphql design manifest: schema inventory mismatch declared=%s found=%s" %
                      (sorted(str(item) for item in schemas), sorted(discovered)))
    return errors


def load_and_validate(project_dir, decisions):
    path = os.path.join(project_dir, "reports", "03_design", "api-specifications", "graphql",
                        "graphql-design-manifest.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        return ["invalid GraphQL design manifest: %s" % exc]
    return validate_graphql_design_manifest(decisions, manifest, project_dir)
