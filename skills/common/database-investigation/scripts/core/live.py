"""Live collection through a bounded query port."""
import time
from .design import object_id


def error_status(error):
    if isinstance(error, PermissionError):
        return "permission_denied"
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, NotImplementedError):
        return "unsupported"
    code = getattr(error, "sqlstate", None)
    if code == "42501":
        return "permission_denied"
    if code in {"57014", "55P03"}:
        return "timeout"
    if code in {"42P01", "42703"}:
        return "unsupported"
    arg = error.args[0] if error.args else None
    number = getattr(arg, "code", arg if isinstance(arg, int) else None)
    if number in {1031, 1044, 1045, 1142, 1227}:
        return "permission_denied"
    if number in {1013, 3024, 2006, 2013}:
        return "timeout"
    if number in {904, 1054, 1146}:
        return "unsupported"
    # ORA-00942 may mean nonexistent OR inaccessible: do not guess.
    return "error"


def normalize(rows, spec, result, eid, collected_at):
    for row in rows:
        kind = spec["kind"]
        schema, name = row["schema"], row["name"]
        if kind == "statistic":
            result["statistics"].append({
                "schema": schema, "name": name, "metric": spec["metric"],
                "value": row.get("value"), "unit": spec["unit"], "semantics": spec["semantics"],
                "collected_at": collected_at, "updated_at": row.get("updated_at"),
                "reset_at": row.get("reset_at"), "evidence_ids": [eid],
                "granularity": spec.get("granularity", "table"),
            })
            continue
        target_kind = "table" if kind in {"column", "constraint"} else kind
        oid = object_id(schema, name, target_kind)
        obj = next((o for o in result["objects"] if o["id"] == oid), None)
        if obj is None:
            obj = {"id": oid, "catalog": None, "schema": schema, "name": name, "kind": target_kind, "columns": [], "constraints": [], "extensions": {}, "evidence_ids": []}
            result["objects"].append(obj)
        if eid not in obj["evidence_ids"]:
            obj["evidence_ids"].append(eid)
        if kind == "column":
            obj["columns"].append({"name": row["column_name"], "type": row["data_type"], "ordinal": int(row["ordinal"]), "nullable": row["nullable"] in {"YES", "Y", True}, "evidence_ids": [eid]})
        elif kind == "constraint":
            c = next((c for c in obj["constraints"] if c["name"] == row["constraint_name"]), None)
            if c is None:
                c = {"name": row["constraint_name"], "kind": row["constraint_kind"], "columns": [], "evidence_ids": [eid]}
                if row.get("ref_table"):
                    c["references"] = {"schema": row["ref_schema"], "name": row["ref_table"], "columns": []}
                if c["kind"] == "check":
                    c["expression"] = "[definition withheld]"
                obj["constraints"].append(c)
            if row.get("column_name") and row["column_name"] not in c["columns"]:
                c["columns"].append(row["column_name"])
            if row.get("ref_column") and "references" in c:
                c["references"]["columns"].append(row["ref_column"])
        elif kind == "index":
            obj["extensions"].update({"table": row.get("table_name"), "table_schema": schema, "unique": bool(row.get("is_unique"))})
            obj["extensions"].setdefault("columns", []).append(row.get("column_name"))
        elif row.get("engine"):
            obj["extensions"]["engine"] = row["engine"]


def collect(adapter, port, schema, clock, limit=10000, budget=120):
    result = {"objects": [], "statistics": [], "evidence": [], "collections": [], "findings": []}
    deadline = time.monotonic() + budget
    try:
        for spec in adapter["queries"]:
            eid = "E" + str(len(result["evidence"]) + 1)
            now = clock()
            result["evidence"].append({"id": eid, "kind": "query", "query_id": spec["id"], "schema": schema, "collected_at": now})
            record = {"id": spec["id"], "status": "ok", "row_count": 0, "truncated": False, "evidence_ids": [eid]}
            result["collections"].append(record)
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                if spec.get("disabled"):
                    record["status"] = "disabled"
                    continue
                rows = port.query(spec, schema, limit, remaining)
                if any(r.get("schema") != schema for r in rows):
                    raise ValueError("scope violation")
                record["truncated"] = len(rows) > limit
                rows = rows[:limit]
                record["row_count"] = len(rows)
                record["status"] = "ok" if rows else "empty"
                # Normalize into a scratch inventory; malformed rows never leak partial objects.
                import copy
                staged = copy.deepcopy(result)
                normalize(rows, spec, staged, eid, now)
                result["objects"], result["statistics"] = staged["objects"], staged["statistics"]
            except Exception as exc:
                record["status"] = error_status(exc)
                record["row_count"] = 0
                record["reason"] = "collection unavailable; inspect permissions, capability and timeout locally"
    finally:
        port.close()
    return result
