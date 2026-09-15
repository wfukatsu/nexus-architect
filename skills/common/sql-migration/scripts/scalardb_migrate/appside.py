"""What moves to the application when ScalarDB SQL cannot run a read-only statement.

  * inventory()       every construct that has to be evaluated outside ScalarDB SQL, over the whole statement (CTE
                      bodies and subqueries included) -- the converter stops at the first one it trips over
  * h2_unsupported()  constructs the H2 residual engine cannot run (references/app-side-notes.md), so a fetch + H2 plan
                      would fail at run time
  * semantic_notes()  source-engine behaviour an application-side rewrite must reproduce (verified against Oracle while
                      rewriting an area sales report, references/app-side-notes.md)
  * design_advice()   tables and keys that would let ScalarDB serve the statement by key
  * estimate_cost()   read-cost estimate from the measured per-row scan cost (references/architecture.md, Performance)

The Java helpers named in the messages live in runtime-java, package com.scalar.migrate.appside.
"""

from __future__ import annotations

from sqlglot import exp

from .schema import SchemaRegistry

AGGREGATES = (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)
# literal forms the converter turns into plain ScalarDB literals
LITERAL_WRAPPERS = (exp.DateStrToDate, exp.TimeStrToTime, exp.StrToDate, exp.StrToTime, exp.TsOrDsToDate,
                    exp.TsOrDsToTimestamp, exp.Cast)
HIERARCHY_FUNCS = {"SYS_CONNECT_BY_PATH", "CONNECT_BY_ROOT", "CONNECT_BY_ISLEAF", "CONNECT_BY_ISCYCLE", "LEVEL"}
NOW_FUNCS = {"SYSDATE", "SYSTIMESTAMP", "NOW", "GETDATE", "CURRENT_TIMESTAMP", "CURRENT_DATE", "LOCALTIMESTAMP"}
OPERATORS = {exp.Div: "/", exp.Mul: "*", exp.Add: "+", exp.Sub: "-", exp.DPipe: "||", exp.Mod: "%"}
QUERY_TYPES = (exp.Select, exp.Union, exp.Except, exp.Intersect)

# Measured on ScalarDB Cluster 3.19.1 + PostgreSQL 16, SERIALIZABLE, scan_fetch_size 10, single client
# (references/architecture.md, Performance): scans cost ~25 us per row, key access 3-6 ms regardless of table size.
SCAN_US_PER_ROW = 25
KEY_ACCESS_MS = 5
GRPC_DEADLINE_MS = 60_000  # scalar.db.cluster.grpc.deadline_duration_millis default


def fn_name(e: exp.Expression) -> str:
    if isinstance(e, exp.Anonymous):
        return e.name.upper()
    if type(e) in OPERATORS:
        return OPERATORS[type(e)]
    if isinstance(e, exp.Func):
        return e.sql_name()
    return type(e).__name__.upper()


def _scope(sel: exp.Expression) -> str:
    owner = sel.find_ancestor(exp.CTE, exp.Subquery)
    if isinstance(owner, exp.CTE):
        return f"CTE {owner.alias}"
    return "subquery" if owner is not None else "main query"


def _own_selects(node: exp.Expression):
    """Every SELECT in the statement, including CTE bodies, derived tables and set-operation branches."""
    return list(node.find_all(exp.Select))


def _is_plain_aggregate(e: exp.Expression) -> bool:
    return isinstance(e, AGGREGATES) and not isinstance(e.this, exp.Distinct) \
        and isinstance(e.this, (exp.Column, exp.Star, exp.Literal))


def _clip(sql: str, limit: int = 80) -> str:
    """One expression's SQL for a message, on one line and cut to `limit` characters."""
    sql = " ".join(sql.split())
    return sql if len(sql) <= limit else sql[:limit - 3] + "..."


def _constructs(e: exp.Expression) -> list[str]:
    """Function and operator names inside an expression, leaving out window functions and subqueries (reported on
    their own) and the literal forms the converter accepts."""
    names: list[str] = []

    def prune(n):
        return isinstance(n, (exp.Window, exp.Subquery, exp.Select)) or isinstance(n, LITERAL_WRAPPERS) and \
            isinstance(n.this, exp.Literal)

    for n in e.walk(prune=prune):
        if isinstance(n, (exp.Window, exp.Subquery, exp.Select)):
            continue
        if isinstance(n, LITERAL_WRAPPERS) and isinstance(n.this, exp.Literal):
            continue
        if isinstance(n, (exp.Func, exp.Binary)) and not isinstance(n, (exp.Connector, exp.Predicate)) \
                or type(n) in OPERATORS:
            name = fn_name(n)
            if name not in HIERARCHY_FUNCS and name not in names:
                names.append(name)
    return names


# --------------------------------------------------------------------------------------------------
# inventory
# --------------------------------------------------------------------------------------------------

def inventory(node: exp.Expression, dialect: str) -> list[tuple[str, str]]:
    """(code, message) for every construct ScalarDB SQL cannot evaluate, deduplicated per code and scope."""
    out: list[tuple[str, str]] = []

    def add(code: str, msg: str) -> None:
        if (code, msg) not in out:
            out.append((code, msg))

    ctes = [c.alias for c in node.find_all(exp.CTE)]
    if ctes:
        add("CTE", f"WITH {', '.join(ctes)}: evaluate each common table expression in the application "
                   f"(fetch its base tables through ScalarDB SQL)")
    for s in node.find_all(exp.Union, exp.Except, exp.Intersect):
        add("SET_OP", f"{_scope(s)}: {type(s).__name__.upper()} -- run each branch and combine the rows in the application")

    for sel in _own_selects(node):
        where = _scope(sel)
        if sel.args.get("connect"):
            funcs = sorted({fn_name(n) if not isinstance(n, exp.Column) else n.name.upper()
                            for n in sel.walk() if isinstance(n, (exp.Anonymous, exp.Column, exp.ConnectByRoot))
                            and (fn_name(n) if not isinstance(n, exp.Column) else n.name.upper()) in HIERARCHY_FUNCS
                            | {"CONNECTBYROOT"}})
            add("HIERARCHICAL", f"{where}: START WITH / CONNECT BY{' with ' + ', '.join(funcs) if funcs else ''} -- walk "
                                f"the tree in the application (appside.Hierarchy) or precompute it into a table")
        windows = []
        for w in sel.find_all(exp.Window):
            if w.find_ancestor(exp.Select) is not sel:
                continue
            if (w.args.get("over") or "").upper() == "KEEP":
                add("KEEP", f"{where}: {w.this.sql(dialect=dialect)} KEEP (DENSE_RANK {'FIRST' if w.args.get('first') else 'LAST'} ...) "
                            f"-- pick the first/last row per group in the application")
                continue
            name = fn_name(w.this) + (" OVER" if isinstance(w.this, AGGREGATES) else "")
            if name not in windows:
                windows.append(name)
        if windows:
            add("WINDOW", f"{where}: window functions {', '.join(windows)} -- partition, sort and compute in the "
                          f"application (appside.Windows)")
        for p in sel.args.get("pivots") or []:
            add("PIVOT", f"{where}: {'UNPIVOT' if p.args.get('unpivot') else 'PIVOT'} -- reshape the rows in the application")
        if sel.args.get("distinct"):
            add("DISTINCT", f"{where}: SELECT DISTINCT -- de-duplicate in the application")
        if sel.args.get("offset"):
            add("OFFSET", f"{where}: OFFSET -- page with a clustering-key range instead")
        exprs = []
        for p in sel.expressions:
            inner = p.this if isinstance(p, exp.Alias) else p
            if isinstance(inner, (exp.Column, exp.Star)) or _is_plain_aggregate(inner) or not _constructs(inner):
                continue
            # the expression itself, not its operator names: "(SUM, *)" read as SELECT *
            text = _clip(inner.sql(dialect=dialect))
            if text not in exprs:
                exprs.append(text)
        if exprs:
            add("PROJECTION", f"{where}: expressions in the select list ({'; '.join(exprs)}) -- compute them in the "
                              f"application")
        group = sel.args.get("group")
        if group:
            for k in ("rollup", "cube", "grouping_sets"):
                if group.args.get(k):
                    add("GROUP", f"{where}: GROUP BY {k.upper().replace('_', ' ')} -- aggregate each level in the application")
            for g in group.expressions:
                if isinstance(g, (exp.Rollup, exp.Cube, exp.GroupingSets)):
                    add("GROUP", f"{where}: GROUP BY {type(g).__name__.upper()} -- aggregate each level in the application")
                elif not isinstance(g, exp.Column):
                    add("GROUP", f"{where}: GROUP BY expression {g.sql(dialect=dialect)} -- group in the application")
        cond = sel.args.get("where")
        if cond is not None:
            for n in cond.this.walk(prune=lambda x: isinstance(x, (exp.Subquery, exp.Select))):
                if isinstance(n, (exp.Subquery, exp.Exists)) or isinstance(n, exp.In) and n.args.get("query"):
                    add("SUBQUERY", f"{where}: subquery in WHERE -- fetch the inner result first and bind its values")
                elif fn_name(n) in NOW_FUNCS or isinstance(n, (exp.CurrentTimestamp, exp.CurrentDate)):
                    add("NOW", f"{where}: {n.sql(dialect=dialect)} -- compute the time in the application and bind it")
            funcs = [name for name in _constructs(cond.this) if name not in NOW_FUNCS and name not in
                     ("CURRENT_TIMESTAMP", "CURRENT_DATE")]
            if funcs:
                add("PRED", f"{where}: functions or arithmetic in WHERE ({', '.join(funcs)}) -- filter after fetching")
        from_ = sel.args.get("from_") or sel.args.get("from")
        if from_ is not None and isinstance(from_.this, exp.Subquery) or \
                any(isinstance(j.this, exp.Subquery) for j in sel.args.get("joins") or []):
            add("SUBQUERY", f"{where}: derived table in FROM -- evaluate it in the application")
        order = sel.args.get("order")
        if order is not None:
            bad = [o.this.sql(dialect=dialect) for o in order.expressions
                   if not (isinstance(o.this, (exp.Column, exp.Identifier)) or _is_plain_aggregate(o.this))]
            if bad:
                add("ORDER", f"{where}: ORDER BY expression {', '.join(bad)} -- sort in the application")
    return out


def h2_unsupported(node: exp.Expression) -> list[str]:
    """Constructs the H2 compatibility modes do not implement (references/app-side-notes.md)."""
    found = []
    if any(s.args.get("connect") for s in node.find_all(exp.Select)):
        found.append("CONNECT BY (rewrite as recursive WITH, or walk the tree in the application)")
    if any(g for g in node.find_all(exp.Rollup, exp.Cube, exp.GroupingSets)) or any(
            grp.args.get(k) for grp in node.find_all(exp.Group) for k in ("rollup", "cube", "grouping_sets")):
        found.append("ROLLUP / CUBE / GROUPING SETS (UNION ALL one aggregate per level)")
    for p in node.find_all(exp.Pivot):
        found.append("UNPIVOT (UNION ALL)" if p.args.get("unpivot") else "PIVOT (conditional aggregation)")
    if any((w.args.get("over") or "").upper() == "KEEP" for w in node.find_all(exp.Window)):
        found.append("KEEP (DENSE_RANK FIRST/LAST) (ROW_NUMBER() ... = 1)")
    return list(dict.fromkeys(found))


# --------------------------------------------------------------------------------------------------
# semantics an application-side rewrite must keep
# --------------------------------------------------------------------------------------------------

def _string_typed(e: exp.Expression, registry: SchemaRegistry) -> bool:
    """True when an ORDER BY term is (or may be) a string: TEXT columns, unknown columns, string functions."""
    if isinstance(e, exp.Column):
        types = {ty for m in registry.tables() for c, ty in m.columns.items() if c.lower() == e.name.lower()}
        return not types or "TEXT" in types
    if isinstance(e, (exp.DPipe, exp.Concat, exp.ToChar, exp.Substring, exp.Upper, exp.Lower)):
        return True
    return isinstance(e, exp.Anonymous) and e.name.upper() in ("SYS_CONNECT_BY_PATH", "LPAD", "RPAD", "INITCAP")


def semantic_notes(node: exp.Expression, dialect: str, registry: SchemaRegistry) -> list[str]:
    names = {fn_name(n) for n in node.walk() if isinstance(n, (exp.Func, exp.Binary))}
    names |= {n.name.upper() for n in node.find_all(exp.Column)}
    ordered = list(node.find_all(exp.Ordered))
    oracle = dialect == "oracle"
    notes = []
    if names & {"LAG", "LEAD"}:
        notes.append("LAG / LEAD return the previous / next row of the partition, not the previous calendar period: "
                     "periods without rows are skipped. Keep that, or fix the source SQL if a calendar comparison was meant")
    if "/" in names:
        notes.append({"oracle": "division by zero raises ORA-01476 and fails the whole statement",
                      "postgres": "division by zero raises division_by_zero; integer / integer truncates",
                      "mysql": "division by zero returns NULL (with a warning)"}.get(dialect, "division by zero")
                     + " -- decide it explicitly in the application (appside.OracleNumbers.divide throws like Oracle)")
    if "ROUND" in names:
        notes.append("ROUND on NUMBER / NUMERIC rounds half away from zero (-2.5 -> -3): use RoundingMode.HALF_UP, "
                     "not HALF_EVEN; keep money in BigDecimal, not double")
    if names & {"SUM", "AVG", "MIN", "MAX"}:
        notes.append("SUM / AVG / MIN / MAX ignore NULLs and return NULL when every input is NULL; COUNT(col) counts "
                     "non-NULL values only")
    if names & {"RANK", "DENSE_RANK", "ROW_NUMBER"}:
        notes.append("RANK / DENSE_RANK give equal ranks to equal ORDER BY values (NULLs compare equal to each other); "
                     "the order of ties under ROW_NUMBER is undefined")
    if ordered:
        nulls = "NULLs sort first for ASC and last for DESC" if dialect == "mysql" \
            else "NULLs sort last for ASC and first for DESC"
        notes.append(f"{nulls} (also inside OVER (ORDER BY ...)); Java comparators need an explicit nullsFirst / "
                     f"nullsLast (appside.OracleOrdering)")
        if any(_string_typed(o.this, registry) for o in ordered):
            notes.append({"oracle": "string ORDER BY follows NLS_SORT: BINARY is code-point order (AL32UTF8 byte order), "
                                    "which String.compareTo breaks for surrogate pairs (appside.OracleOrdering.BINARY); "
                                    "linguistic sorts such as JAPANESE_M need a Collator",
                          "postgres": "string ORDER BY follows the column collation (often not code-point order)",
                          "mysql": "string ORDER BY follows the collation, case-insensitive by default"}
                         .get(dialect, "string ORDER BY follows the database collation"))
    if "SYS_CONNECT_BY_PATH" in names:
        notes.append("SYS_CONNECT_BY_PATH puts the separator before every value (the path starts with it) and fails "
                     "with ORA-30004 when a value contains the separator")
    if "LEVEL" in names and any(s.args.get("connect") for s in node.find_all(exp.Select)):
        notes.append("CONNECT BY: LEVEL starts at 1 for the START WITH rows; a cycle raises ORA-01436 unless NOCYCLE")
    if names & {"ADD_MONTHS", "ADDMONTHS"}:
        notes.append("ADD_MONTHS keeps month ends (2025-02-28 minus 12 months = 2024-02-29); LocalDate.plusMonths does "
                     "not (appside.OracleDates.addMonths)")
    if names & {"TO_CHAR", "TOCHAR", "TIME_TO_STR", "DATE_FORMAT"}:
        notes.append("date formatting (TO_CHAR / DATE_FORMAT) uses the session time zone and date language; format in "
                     "the same zone and locale in the application")
    if names & NOW_FUNCS or node.find(exp.CurrentTimestamp, exp.CurrentDate):
        notes.append("SYSDATE / CURRENT_TIMESTAMP come from the database server clock and time zone, not the JVM")
    if oracle and any(isinstance(n, exp.EQ) and isinstance(n.expression, exp.Literal) and n.expression.is_string
                      and n.expression.name == "" for n in node.walk()):
        notes.append("Oracle treats the empty string as NULL")
    return notes


# --------------------------------------------------------------------------------------------------
# design advice
# --------------------------------------------------------------------------------------------------

def _base_table(sel: exp.Select) -> exp.Table | None:
    from_ = sel.args.get("from_") or sel.args.get("from")
    if from_ is not None and isinstance(from_.this, exp.Table) and not sel.args.get("joins"):
        return from_.this
    return None


def design_advice(node: exp.Expression, registry: SchemaRegistry, storage: str, dialect: str) -> list[str]:
    advice = []
    cte_names = {c.alias.lower() for c in node.find_all(exp.CTE)}
    unknown = sorted({t.name for t in node.find_all(exp.Table)
                      if t.name.lower() not in cte_names and t.name.lower() != "dual" and registry.get(t.name) is None})
    if unknown:
        advice.append(f"table definitions unknown for {', '.join(unknown)}: include CREATE TABLE or pass --schema to get "
                      f"access-path checks and key-design advice")
    for sel in node.find_all(exp.Select):
        t = _base_table(sel)
        if t is None or t.name.lower() in cte_names:
            continue
        if sel.args.get("connect"):
            advice.append(f"{t.name}: precompute the hierarchy (node id -> parent, level, path) into a table keyed by node "
                          f"id and rebuild it when the tree changes, or cache the tree in the application; the tree is "
                          f"then read by key instead of scanning {t.name}")
        group = sel.args.get("group")
        if group and group.expressions:
            aliases = {p.this.sql(dialect=dialect).lower(): p.alias for p in sel.expressions if isinstance(p, exp.Alias)}
            keys = [aliases.get(g.sql(dialect=dialect).lower()) or (g.name if isinstance(g, exp.Column) else g.sql(dialect=dialect))
                    for g in group.expressions]
            advice.append(f"{t.name}: keep a summary table keyed by ({', '.join(keys)}) -- partition key {keys[0]} -- updated "
                          f"with each write or by a batch, so the query reads one row per group instead of every "
                          f"{t.name} row; store the count of non-NULL values too so SUM's NULL result can be reproduced")
    # join columns that are neither a key nor an index
    for j in node.find_all(exp.Join):
        on = j.args.get("on")
        if on is None or not isinstance(j.this, exp.Table):
            continue
        meta = registry.get(j.this.name)
        if meta is None:
            continue
        alias = (j.this.alias or j.this.name).lower()
        cols = {c.name.lower() for c in on.find_all(exp.Column) if (c.table or "").lower() == alias}
        keys = {c.lower() for c in meta.primary_key} | {c.lower() for c in meta.partition_key} | \
               {c.lower() for c in meta.secondary_indexes}
        for c in sorted(cols - keys):
            advice.append(f"{meta.name}.{c} is joined on but is neither a key nor indexed: make it the partition key or "
                          f"add CREATE INDEX ON {meta.name} ({c})")
    if storage != "jdbc":
        advice.append(f"on {storage}, give every access path a key: statements that would scan a whole table need a "
                      f"lookup table keyed by the value the application already knows")
    if node.find(exp.Window) and (node.find(exp.Group) or any(s.args.get("connect") for s in node.find_all(exp.Select))):
        advice.append("analytical query (aggregation + window functions): if it runs as a report rather than per request, "
                      "consider ScalarDB Analytics instead of fetching every row through transactions")
    return list(dict.fromkeys(advice))


# --------------------------------------------------------------------------------------------------
# cost
# --------------------------------------------------------------------------------------------------

def parse_expected_rows(items: list[str] | None) -> dict[str, tuple[int, int | None]]:
    """--expected-rows table=N[:per_key]  (total rows, rows per partition / index key)"""
    out = {}
    for item in items or []:
        table, _, spec = item.partition("=")
        total, _, per_key = spec.partition(":")
        out[table.strip().lower()] = (int(total.replace("_", "")), int(per_key.replace("_", "")) if per_key else None)
    return out


def estimate_cost(fetches: list[tuple[str, str]], expected: dict[str, tuple[int, int | None]], isolation: str,
                  row_limit: int | None) -> list[tuple[str, str, str]]:
    """(severity, code, message) per fetch; fetches are (table, access path)."""
    out = []
    factor = 2 if isolation.upper() == "SERIALIZABLE" else 1
    total_ms = 0.0
    if not expected:
        scans = [t for t, p in fetches if p in ("CROSS_PARTITION", "UNKNOWN")]
        return [("INFO", "COST", f"full scan of {', '.join(dict.fromkeys(scans))} (~{SCAN_US_PER_ROW} us per row); pass "
                                 f"--expected-rows table=N for an estimate")] if scans else []
    for table, path in fetches:
        total, per_key = expected.get(table.lower(), (None, None))
        if path == "GET":
            ms, rows = KEY_ACCESS_MS, 1
        elif path in ("CROSS_PARTITION", "UNKNOWN"):
            if total is None:
                out.append(("INFO", "COST", f"{table}: full scan; pass --expected-rows {table}=N for an estimate"))
                continue
            rows = total
            ms = rows * SCAN_US_PER_ROW / 1000 * factor
        else:
            if per_key is None:
                out.append(("INFO", "COST", f"{table}: {path}; cost grows with the rows per key "
                                            f"(~{SCAN_US_PER_ROW} us per row; pass --expected-rows {table}=N:rows_per_key)"))
                continue
            rows = per_key
            ms = KEY_ACCESS_MS + rows * SCAN_US_PER_ROW / 1000 * factor
        total_ms += ms
        out.append(("INFO", "COST", f"{table}: {path} reading ~{rows:,} rows -> ~{_fmt_ms(ms)}"
                                    f"{' (SERIALIZABLE re-reads scans at commit: x2)' if factor == 2 and path != 'GET' else ''}"))
        if row_limit and rows > row_limit:
            out.append(("WARN", "ROW_LIMIT", f"{table}: ~{rows:,} rows exceed the plan row limit {row_limit:,}; add a key "
                                             f"range, page with a clustering-key range, or read a summary table"))
    if total_ms > GRPC_DEADLINE_MS:
        out.append(("WARN", "COST_DEADLINE", f"estimated ~{_fmt_ms(total_ms)} exceeds the ScalarDB Cluster gRPC deadline "
                                             f"({GRPC_DEADLINE_MS // 1000} s, scalar.db.cluster.grpc.deadline_duration_millis)"))
    if out:
        out.append(("INFO", "COST", f"estimate basis: ~{SCAN_US_PER_ROW} us per scanned row and ~{KEY_ACCESS_MS} ms per key "
                                    f"access, measured single-client with scan_fetch_size 10 (references/architecture.md, Performance)"))
    return out


def _fmt_ms(ms: float) -> str:
    return f"{ms / 1000:,.1f} s" if ms >= 1000 else f"{ms:,.0f} ms"


def recommended_config(paths: list[str], isolation: str) -> dict:
    scans = any(p != "GET" for p in paths)
    cfg = {"transaction": "read-only (DistributedTransactionManager.beginReadOnly / SqlSession.beginReadOnly, 3.16+)"}
    if scans:
        cfg["scalar.db.scan_fetch_size"] = 1000
        cfg["scalar.db.cluster.client.scan_fetch_size"] = 1000
    if "CROSS_PARTITION" in paths:
        cfg["scalar.db.cross_partition_scan.enabled"] = True
    if scans and isolation.upper() == "SERIALIZABLE":
        cfg["isolation_note"] = ("SERIALIZABLE re-executes every scan at commit; SNAPSHOT or READ_COMMITTED avoids it but "
                                 "applies to the whole node")
    return cfg


def config_message(cfg: dict) -> str:
    return "; ".join(f"{k}={v}" if k.startswith("scalar.") else v for k, v in cfg.items())


def group_issues(issues) -> dict[str, list]:
    """Split a statement's issues for reports: app-side work, semantics, design, cost, config."""
    groups = {"app_side": [], "semantics": [], "design": [], "cost": [], "config": []}
    for i in issues:
        if i.code == "APP_SEMANTICS":
            groups["semantics"].append(i)
        elif i.code == "DESIGN":
            groups["design"].append(i)
        elif i.code in ("COST", "ROW_LIMIT", "COST_DEADLINE"):
            groups["cost"].append(i)
        elif i.code == "CONFIG":
            groups["config"].append(i)
        elif i.severity == "ERROR":
            groups["app_side"].append(i)
    return groups
