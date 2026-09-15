"""Analyse source SQL (Oracle / PostgreSQL / MySQL) and convert it to ScalarDB SQL.

Every statement produces a Result with:
  * status      OK | WARN | ERROR   (ERROR = cannot be converted automatically)
  * converted   ScalarDB SQL (may be several statements, e.g. CREATE TABLE + CREATE INDEX)
  * issues      list of Issue(severity, code, message)

The rules encode the ScalarDB SQL grammar (https://scalardb.scalar-labs.com/docs/latest/scalardb-sql/grammar/).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, UnsupportedError
from sqlglot.optimizer.normalize import normalize
from sqlglot.tokens import TokenType
from sqlglot.transforms import eliminate_join_marks

from . import appside
from .decomposer import DEFAULT_ROW_LIMIT, ORDERED_SCAN_STORAGES, Decomposer, NotDecomposable, PlanBlocked
from .dialect import Upsert, to_scalardb_sql
from .schema import SchemaRegistry, TableMeta
from .types import map_type

AGGREGATES = (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)
COMPARISONS = (exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE)
FLIP = {exp.EQ: exp.EQ, exp.NEQ: exp.NEQ, exp.GT: exp.LT, exp.LT: exp.GT, exp.GTE: exp.LTE, exp.LTE: exp.GTE}
NEGATE = {exp.EQ: exp.NEQ, exp.NEQ: exp.EQ, exp.GT: exp.LTE, exp.LTE: exp.GT, exp.LT: exp.GTE, exp.GTE: exp.LT}
LITERAL_TYPES = (exp.Literal, exp.Null, exp.Boolean, exp.Placeholder, exp.Parameter, exp.HexString)


@dataclass
class Issue:
    severity: str  # INFO | WARN | ERROR
    code: str
    message: str


@dataclass
class Result:
    index: int
    source_sql: str
    kind: str
    status: str = "OK"
    converted: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    plan: dict | None = None  # app-side execution plan when status == PLANNED


class Unconvertible(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# --------------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------------

def _unparen(e: exp.Expression) -> exp.Expression:
    while isinstance(e, exp.Paren):
        e = e.this
    return e


def _is_literal(e: exp.Expression) -> bool:
    e = _unparen(e)
    if isinstance(e, LITERAL_TYPES):
        return True
    if isinstance(e, exp.Neg) and isinstance(e.this, exp.Literal):
        return True
    if isinstance(e, exp.Cast) and isinstance(e.this, exp.Literal):  # DATE '2024-01-01' style
        return True
    return False


def _is_aggregate(e: exp.Expression) -> bool:
    if not isinstance(e, AGGREGATES):
        return False
    arg = e.this
    if isinstance(arg, exp.Distinct):
        return False
    return isinstance(arg, (exp.Column, exp.Star, exp.Literal))


def _flatten(e: exp.Expression, op: type) -> list[exp.Expression]:
    e = _unparen(e)
    if isinstance(e, op):
        return _flatten(e.this, op) + _flatten(e.expression, op)
    return [e]


def _arg(node: exp.Expression, key: str):
    """sqlglot >= 28 renamed keyword-clashing args (from -> from_, with -> with_)."""
    return node.args.get(f"{key}_") if f"{key}_" in node.args else node.args.get(key)


def _from(node: exp.Expression):
    return _arg(node, "from")


def _bad_join_mark_rewrite(node: exp.Expression) -> bool:
    """sqlglot's eliminate_join_marks() mishandles (+) on the FROM-side table: it emits a CROSS JOIN and duplicates
    the table. Detect that so the statement is reported for manual rewriting instead of silently wrong SQL."""
    for sel in node.find_all(exp.Select):
        seen: set[str] = set()
        f = _from(sel)
        tables = ([f.this] if f is not None and isinstance(f.this, exp.Table) else []) + \
                 [j.this for j in sel.args.get("joins") or [] if isinstance(j.this, exp.Table)]
        for t in tables:
            key = (t.alias or t.name).lower()
            if key in seen:
                return True
            seen.add(key)
        if any((j.args.get("kind") or "").upper() == "CROSS" for j in sel.args.get("joins") or []):
            return True
    return False


def _split_statements(text: str, dialect: str) -> list[str]:
    """Split a script on top-level semicolons using the dialect tokenizer (comments/strings safe)."""
    tokens = sqlglot.tokenize(text, read=dialect)
    stmts, start = [], 0
    for tok in tokens:
        if tok.token_type == TokenType.SEMICOLON:
            chunk = text[start:tok.start].strip()
            if chunk:
                stmts.append(chunk)
            start = tok.end + 1
    tail = text[start:].strip()
    if tail:
        stmts.append(tail)
    return [s for s in stmts if not re.fullmatch(r"(\s|--[^\n]*\n?|/\*.*?\*/)*", s, re.S)]


# --------------------------------------------------------------------------------------------------
# converter
# --------------------------------------------------------------------------------------------------

class StatementConverter:
    def __init__(self, dialect: str, registry: SchemaRegistry, key_hints: dict[str, tuple[list[str], list[str]]],
                 decompose: bool = True, storage: str = "jdbc",
                 expected_rows: dict[str, tuple[int, int | None]] | None = None, isolation: str = "SERIALIZABLE",
                 row_limit: int = DEFAULT_ROW_LIMIT, h2_indexes: bool = False):
        self.dialect = dialect
        self.registry = registry
        self.key_hints = key_hints
        self.decompose = decompose
        self.storage = storage  # storage behind ScalarDB: "jdbc" or a non-JDBC one such as "cassandra"
        self.expected_rows = expected_rows or {}  # table -> (rows, rows per key), for cost estimates
        self.isolation = isolation  # ScalarDB Consensus Commit isolation level the estimates assume
        self.row_limit = row_limit
        self.h2_indexes = h2_indexes  # plans ask the runtime to build H2 indexes (joins over large fetches)
        self.issues: list[Issue] = []

    # -- issue helpers ------------------------------------------------------------------------------
    def info(self, code: str, msg: str) -> None:
        self.issues.append(Issue("INFO", code, msg))

    def warn(self, code: str, msg: str) -> None:
        self.issues.append(Issue("WARN", code, msg))

    def fail(self, code: str, msg: str) -> None:
        raise Unconvertible(code, msg)

    # -- entry point --------------------------------------------------------------------------------
    def convert(self, sql: str) -> Result:
        self.issues = []
        self._source = sql
        res = Result(0, sql, "UNKNOWN")
        upsert = False
        src = sql
        if re.match(r"\s*REPLACE\s+INTO\b", sql, re.I):  # MySQL REPLACE INTO is not parsed by sqlglot
            src = re.sub(r"^\s*REPLACE\s+INTO\b", "INSERT INTO", sql, flags=re.I)
            upsert = True
        try:
            node = sqlglot.parse_one(src, read=self.dialect)
        except ParseError as e:
            res.kind, res.status = "PARSE_ERROR", "ERROR"
            res.issues.append(Issue("ERROR", "PARSE", str(e).splitlines()[0]))
            return res
        res.kind = type(node).__name__.upper()
        try:
            if any(c.args.get("join_mark") for c in node.find_all(exp.Column)):
                node = eliminate_join_marks(node)
                if _bad_join_mark_rewrite(node):
                    self.fail("ORACLE_JOIN_MARK", "Oracle (+) outer join could not be rewritten automatically "
                                                  "(mark on the FROM-side table / mixed sides); rewrite as LEFT/RIGHT JOIN by hand")
                self.warn("ORACLE_JOIN_MARK", "Oracle (+) outer join rewritten as LEFT/RIGHT OUTER JOIN")
            self._normalize_identifiers(node)
            if upsert:
                self.warn("REPLACE", "REPLACE INTO converted to UPSERT: REPLACE resets unlisted columns to NULL, "
                                     "UPSERT keeps their existing values")
                node = Upsert(**node.args)
            out = self._dispatch(node)
            res.converted = [to_scalardb_sql(n) if isinstance(n, exp.Expression) else n for n in out]
        except Unconvertible as e:
            self.issues.append(Issue("ERROR", e.code, str(e)))
        except UnsupportedError as e:
            self.issues.append(Issue("ERROR", "UNSUPPORTED", str(e)))
        res.issues = list(self.issues)
        query = isinstance(node, appside.QUERY_TYPES)
        if any(i.severity == "ERROR" for i in res.issues):
            res.status, res.converted = "ERROR", []
            fresh = self._reparse(src) if query else None  # the converter mutated the first AST
            if fresh is not None:
                self._inventory(res, fresh)
            if self.decompose and query:
                self._try_plan(res, src)
            if fresh is not None:
                self._advise(res, fresh)
        elif any(i.severity == "WARN" for i in res.issues):
            res.status = "WARN"
        if res.status == "WARN" and isinstance(node, exp.Select) and any(i.code == "CROSS_PARTITION" for i in res.issues):
            self._cost(res, [(_from(node).this.name, "CROSS_PARTITION")], row_limit=None)
        return res

    def _reparse(self, src: str) -> exp.Expression | None:
        try:
            return sqlglot.parse_one(src, read=self.dialect)
        except ParseError:
            return None

    def _inventory(self, res: Result, fresh: exp.Expression) -> None:
        """List every construct that has to move to the application, not only the first one select() failed on.
        The converter's own ERROR is replaced when the inventory reports the same construct in more detail."""
        found = appside.inventory(fresh, self.dialect)
        codes = {c for c, _ in found}
        res.issues = [i for i in res.issues if not (i.severity == "ERROR" and i.code in codes)]
        res.issues.extend(Issue("ERROR", c, m) for c, m in found)

    def _advise(self, res: Result, fresh: exp.Expression) -> None:
        if res.status == "ERROR":  # a plan runs the original SQL in H2, which keeps these semantics itself
            res.issues.extend(Issue("WARN", "APP_SEMANTICS", m)
                              for m in appside.semantic_notes(fresh, self.dialect, self.registry))
        res.issues.extend(Issue("INFO", "DESIGN", m)
                          for m in appside.design_advice(fresh, self.registry, self.storage, self.dialect))

    def _cost(self, res: Result, fetches: list[tuple[str, str]], row_limit: int | None) -> dict:
        cfg = appside.recommended_config([p for _, p in fetches], self.isolation)
        res.issues.append(Issue("INFO", "CONFIG", appside.config_message(cfg)))
        res.issues.extend(Issue(sev, code, msg) for sev, code, msg in
                          appside.estimate_cost(fetches, self.expected_rows, self.isolation, row_limit))
        return cfg

    def _try_plan(self, res: Result, src: str) -> None:
        """ERROR statement that is read-only: build a fetch + residual plan (references/architecture.md, Execution plans)."""
        codes = {i.code for i in res.issues if i.severity == "ERROR"}
        try:
            fresh = sqlglot.parse_one(src, read=self.dialect)  # the converter mutated the first AST
            plan = Decomposer(self.dialect, self.registry, row_limit=self.row_limit, storage=self.storage,
                              h2_indexes=self.h2_indexes).decompose(fresh, src.strip(), codes)
        except PlanBlocked as e:
            res.issues.extend(Issue("ERROR", code, msg) for code, msg in e.problems)
            return
        except (NotDecomposable, Exception) as e:  # noqa: BLE001
            res.issues.append(Issue("INFO", "PLAN", f"not decomposable: {e}"))
            return
        res.plan = plan.to_dict()
        res.status = "PLANNED"
        for f in plan.fetch:
            res.issues.append(Issue("INFO", "PLAN_FETCH", f"{f.access_path}: {f.scalardb_sql}"))
        res.issues.append(Issue("INFO", "PLAN_RESIDUAL", f"H2 {plan.residual['java']['mode']} mode runs the original SQL "
                                                        f"(pattern {plan.pattern}, H2 indexes "
                                                        f"{'on' if self.h2_indexes else 'off'})"))
        for u in plan.unresolved:
            res.issues.append(Issue("WARN", "PLAN_UNRESOLVED", u))
        if plan.guardrails["requires_cross_partition_scan"]:
            res.issues.append(Issue("WARN", "PLAN_CROSS_PARTITION", "a fetch needs a cross-partition scan"))
        res.plan["recommended_config"] = self._cost(res, [(f.table, f.access_path) for f in plan.fetch], self.row_limit)

    def _dispatch(self, node: exp.Expression) -> list:
        if isinstance(node, exp.Select):
            return [self.select(node)]
        if isinstance(node, (exp.Union, exp.Intersect, exp.Except)):
            self.fail("SET_OP", "UNION / INTERSECT / EXCEPT are not supported; run the queries separately")
        if isinstance(node, exp.Insert):
            return [self.insert(node)]
        if isinstance(node, exp.Update):
            return [self.update(node)]
        if isinstance(node, exp.Delete):
            return [self.delete(node)]
        if isinstance(node, exp.Merge):
            return [self.merge(node)]
        if isinstance(node, exp.Create):
            return self.create(node)
        if isinstance(node, exp.Drop):
            return [self.drop(node)]
        if isinstance(node, exp.Alter):
            return self.alter(node)
        if isinstance(node, exp.TruncateTable):
            return [f"TRUNCATE TABLE {self._table_name(node.expressions[0])}"]
        if isinstance(node, (exp.Transaction, exp.Commit, exp.Rollback)):
            if node.args.get("this") or node.args.get("savepoint"):
                self.fail("SAVEPOINT", "savepoints / named transactions are not supported")
            return [node]
        if isinstance(node, exp.Use):
            return [f"USE {node.this.name}"]
        if isinstance(node, exp.Command):
            self.fail("UNPARSED", f"statement type '{node.this}' is not supported "
                                  f"(views, triggers, procedures, sequences, grants, session settings ...)")
        self.fail("STATEMENT", f"{type(node).__name__} statements are not supported by ScalarDB SQL")

    # -- identifiers --------------------------------------------------------------------------------
    def _normalize_identifiers(self, node: exp.Expression) -> None:
        for col in node.find_all(exp.Column):
            if col.name.upper() in ("ROWID", "ROWSCN", "ORA_ROWSCN"):
                self.fail("ROWID", f"pseudo-column {col.name.upper()} does not exist in ScalarDB; use the primary key")
        for ident in node.find_all(exp.Identifier):
            if ident.quoted:
                ident.set("quoted", False)
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ident.name):
                    self.warn("IDENT", f"identifier \"{ident.name}\" contains characters ScalarDB may not accept")

    def _table_name(self, t: exp.Expression) -> str:
        t = t.this if isinstance(t, exp.Schema) else t
        if not isinstance(t, exp.Table):
            self.fail("TABLE", f"expected a table name, got {t.sql()}")
        parts = [p for p in (t.args.get("catalog"), t.args.get("db")) if p]
        if len(parts) > 1:
            self.warn("NAMESPACE", f"{t.sql()}: catalog dropped, schema '{t.db}' used as ScalarDB namespace")
        return f"{t.db}.{t.name}" if t.db else t.name

    def _meta(self, t: exp.Expression) -> TableMeta | None:
        t = t.this if isinstance(t, exp.Schema) else t
        return self.registry.get(t.name) if isinstance(t, exp.Table) else None

    # -- literal / value rewriting ------------------------------------------------------------------
    def _value(self, e: exp.Expression, ctx: str) -> exp.Expression:
        """Return a ScalarDB literal for e, or fail."""
        e = _unparen(e)
        if _is_literal(e):
            return e
        if isinstance(e, exp.Cast) and isinstance(e.this, exp.Literal):
            return e
        # DATE '2020-01-01' / TIMESTAMP '2020-01-01 10:00:00': SQLGlot represents Oracle's ANSI date and timestamp
        # literals as DateStrToDate / TimeStrToTime. They are ISO by definition, so the plain literal is exact.
        if isinstance(e, (exp.DateStrToDate, exp.TimeStrToTime)) and isinstance(e.this, exp.Literal):
            self.info("DATE_LIT", f"{ctx}: {e.sql(dialect=self.dialect)} written as the plain literal '{e.this.name}'")
            return exp.Literal.string(e.this.name)
        # TO_DATE('2020-01-01','YYYY-MM-DD') / TO_TIMESTAMP(...) / '...'::date with constant args
        if isinstance(e, (exp.StrToDate, exp.StrToTime, exp.TsOrDsToDate, exp.TsOrDsToTimestamp)) \
                and isinstance(e.this, exp.Literal):
            self.warn("DATE_FMT", f"{ctx}: {e.sql(dialect=self.dialect)} replaced by the plain literal "
                                  f"'{e.this.name}'; make sure it is in ScalarDB format (YYYY-MM-DD [HH:MM:SS.FFF])")
            return exp.Literal.string(e.this.name)
        if isinstance(e, (exp.CurrentTimestamp, exp.CurrentDate, exp.CurrentTime)) or \
                (isinstance(e, exp.Anonymous) and e.name.upper() in ("SYSDATE", "SYSTIMESTAMP", "NOW", "GETDATE")):
            self.fail("NOW", f"{ctx}: {e.sql(dialect=self.dialect)} must be computed in the application and bound as a literal")
        if isinstance(e, exp.Column) and e.name.upper() in ("NEXTVAL", "CURRVAL") or "NEXTVAL" in e.sql().upper():
            self.fail("SEQUENCE", f"{ctx}: sequences are not supported; generate keys in the application (e.g. UUID)")
        self.fail("EXPR", f"{ctx}: only literals and bind markers are allowed, got '{e.sql(dialect=self.dialect)}'")

    def _column_type(self, col: exp.Column) -> str | None:
        for t in getattr(self, "_tables", []):
            meta = self.registry.get(t.name)
            if meta and (not col.table or col.table.lower() in ((t.alias or "").lower(), t.name.lower())):
                for c, ty in meta.columns.items():
                    if c.lower() == col.name.lower():
                        return ty
        return None

    def _fit_date_literal(self, col: exp.Column, value: exp.Expression, ctx: str) -> exp.Expression:
        """Oracle DATE carries a time; ScalarDB DATE does not. Strip a midnight time from literals compared to DATE columns."""
        if self._column_type(col) != "DATE":
            return value
        lit = value.this if isinstance(value, exp.Cast) and isinstance(value.this, exp.Literal) else value
        if isinstance(lit, exp.Literal) and lit.is_string:
            m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}(:\d{2}(\.\d+)?)?)", lit.name)
            if m and re.fullmatch(r"00:00(:00(\.0+)?)?", m.group(2)):
                self.info("DATE_LIT", f"{ctx}: midnight time part dropped from '{lit.name}' for DATE column {col.name}")
                return exp.Literal.string(m.group(1))
            if m:
                self.warn("DATE_LIT", f"{ctx}: '{lit.name}' has a time part but {col.name} is a ScalarDB DATE; "
                                      f"the time is dropped (use TIMESTAMP for the column if the time matters)")
                return exp.Literal.string(m.group(1))
        return value

    # -- predicates ---------------------------------------------------------------------------------
    def _push_not(self, e: exp.Expression, negate: bool) -> exp.Expression:
        e = _unparen(e)
        if isinstance(e, exp.Not):
            return self._push_not(e.this, not negate)
        if isinstance(e, exp.And):
            l, r = self._push_not(e.this, negate), self._push_not(e.expression, negate)
            return exp.Or(this=l, expression=r) if negate else exp.And(this=l, expression=r)
        if isinstance(e, exp.Or):
            l, r = self._push_not(e.this, negate), self._push_not(e.expression, negate)
            return exp.And(this=l, expression=r) if negate else exp.Or(this=l, expression=r)
        if not negate:
            return e
        if type(e) in NEGATE:
            return NEGATE[type(e)](this=e.this, expression=e.expression)
        if isinstance(e, exp.In):
            return exp.Not(this=e)  # expanded later
        if isinstance(e, exp.Between):
            return exp.Or(this=exp.LT(this=e.this.copy(), expression=e.args["low"]),
                          expression=exp.GT(this=e.this.copy(), expression=e.args["high"]))
        if isinstance(e, (exp.Is, exp.Like, exp.ILike, exp.Escape)):
            return exp.Not(this=e)
        self.fail("NOT", f"cannot negate '{e.sql(dialect=self.dialect)}'")

    def _expand_in(self, e: exp.Expression) -> exp.Expression:
        e = _unparen(e)
        if isinstance(e, (exp.And, exp.Or)):
            return type(e)(this=self._expand_in(e.this), expression=self._expand_in(e.expression))
        neg = isinstance(e, exp.Not) and isinstance(_unparen(e.this), exp.In)
        target = _unparen(e.this) if neg else e
        if isinstance(target, exp.In):
            if target.args.get("query") or not target.expressions:
                self.fail("SUBQUERY", "IN (subquery) is not supported; fetch the inner result first and bind literals")
            col = target.this
            if neg:
                parts = [exp.NEQ(this=col.copy(), expression=v) for v in target.expressions]
                return exp.and_(*parts) if len(parts) > 1 else parts[0]
            parts = [exp.EQ(this=col.copy(), expression=v) for v in target.expressions]
            self.info("IN", f"IN list on {col.sql()} expanded to an OR of {len(parts)} equality predicates")
            return exp.or_(*parts) if len(parts) > 1 else parts[0]
        return e

    def _check_leaf(self, leaf: exp.Expression, ctx: str, allow_agg: bool = False) -> exp.Expression:
        leaf = _unparen(leaf)
        if isinstance(leaf, exp.Exists) or leaf.find(exp.Subquery, exp.Select):
            self.fail("SUBQUERY", f"{ctx}: subqueries are not supported ('{leaf.sql(dialect=self.dialect)[:60]}')")
        if isinstance(leaf, exp.Not):
            inner = _unparen(leaf.this)
            if isinstance(inner, exp.Is) and isinstance(inner.expression, exp.Null) and isinstance(inner.this, exp.Column):
                return leaf
            if isinstance(inner, (exp.Like, exp.ILike)):
                return exp.Not(this=self._check_leaf(inner, ctx, allow_agg))
            self.fail("PRED", f"{ctx}: unsupported predicate '{leaf.sql(dialect=self.dialect)}'")
        if isinstance(leaf, exp.Is):
            if isinstance(leaf.this, exp.Column) and isinstance(leaf.expression, exp.Null):
                return leaf
            self.fail("PRED", f"{ctx}: IS is only supported as IS [NOT] NULL on a column")
        if isinstance(leaf, exp.Escape):
            like = self._check_leaf(leaf.this, ctx, allow_agg)
            return exp.Escape(this=like, expression=leaf.expression)
        if isinstance(leaf, exp.ILike):
            self.warn("ILIKE", f"{ctx}: ILIKE converted to LIKE (case-insensitive matching is lost)")
            leaf = exp.Like(this=leaf.this, expression=leaf.expression)
        if isinstance(leaf, exp.Like):
            if not isinstance(leaf.this, exp.Column):
                self.fail("PRED", f"{ctx}: LIKE left-hand side must be a column")
            leaf.set("expression", self._value(leaf.expression, ctx))
            return leaf
        if isinstance(leaf, exp.Between):
            if not isinstance(leaf.this, exp.Column):
                self.fail("PRED", f"{ctx}: BETWEEN left-hand side must be a column")
            leaf.set("low", self._value(leaf.args["low"], ctx))
            leaf.set("high", self._value(leaf.args["high"], ctx))
            return leaf
        if type(leaf) in FLIP:
            lhs, rhs = leaf.this, leaf.expression
            if _is_literal(lhs) and not _is_literal(rhs):  # 10 < col  ->  col > 10
                lhs, rhs = rhs, lhs
                leaf = FLIP[type(leaf)](this=lhs, expression=rhs)
            ok_lhs = isinstance(lhs, exp.Column) or (allow_agg and _is_aggregate(lhs))
            if not ok_lhs:
                if isinstance(lhs, exp.Column) is False and isinstance(rhs, exp.Column) and isinstance(lhs, exp.Column):
                    pass
                self.fail("PRED", f"{ctx}: left-hand side must be a column"
                                  f"{' or aggregate' if allow_agg else ''}, got '{lhs.sql(dialect=self.dialect)}'")
            if isinstance(rhs, exp.Column):
                self.fail("COL_COL", f"{ctx}: column-to-column comparison '{leaf.sql(dialect=self.dialect)}' is not "
                                     f"supported (only column vs literal / bind marker)")
            leaf.set("expression", self._fit_date_literal(lhs, self._value(rhs, ctx), ctx) if isinstance(lhs, exp.Column) else self._value(rhs, ctx))
            return leaf
        if isinstance(leaf, exp.Boolean):
            self.fail("PRED", f"{ctx}: constant boolean predicates are not supported")
        self.fail("PRED", f"{ctx}: unsupported predicate '{leaf.sql(dialect=self.dialect)}'")

    def _build_condition(self, cond: exp.Expression, ctx: str, allow_agg: bool = False) -> exp.Expression:
        """Rewrite a WHERE/HAVING condition into ScalarDB-compatible DNF or CNF with explicit parentheses."""
        cond = self._expand_in(self._push_not(cond, False))
        # keep the author's shape when it is already an OR-of-ANDs (DNF) or an AND-of-ORs (CNF)
        if not (self._is_normal_form(cond, exp.Or, exp.And) or self._is_normal_form(cond, exp.And, exp.Or)):
            dnf = normalize(cond.copy(), dnf=True, max_distance=128)
            cnf = normalize(cond.copy(), dnf=False, max_distance=128)
            ok_dnf = self._is_normal_form(dnf, exp.Or, exp.And)
            ok_cnf = self._is_normal_form(cnf, exp.And, exp.Or)
            if not (ok_dnf or ok_cnf):
                self.fail("NORMAL_FORM", f"{ctx}: predicate could not be normalised to DNF/CNF")
            cond = dnf if (ok_dnf and (not ok_cnf or len(dnf.sql()) <= len(cnf.sql()))) else cnf
            self.info("NORMAL_FORM", f"{ctx}: predicate rewritten into {'DNF' if cond is dnf else 'CNF'} as required by ScalarDB")
        outer = exp.And if isinstance(_unparen(cond), exp.And) else exp.Or
        inner = exp.Or if outer is exp.And else exp.And
        groups = []
        for g in _flatten(cond, outer):
            leaves = [self._check_leaf(x, ctx, allow_agg) for x in _flatten(g, inner)]
            if len(leaves) == 1:
                groups.append(leaves[0])
            else:
                groups.append(exp.Paren(this=(exp.and_ if inner is exp.And else exp.or_)(*leaves)))
        if len(groups) == 1:
            return groups[0]
        return (exp.and_ if outer is exp.And else exp.or_)(*groups)

    @staticmethod
    def _is_normal_form(e: exp.Expression, outer: type, inner: type) -> bool:
        for g in _flatten(e, outer):
            for leaf in _flatten(g, inner):
                if isinstance(_unparen(leaf), (exp.And, exp.Or)):
                    return False
        return True

    # -- access path analysis -----------------------------------------------------------------------
    def _access_path(self, meta: TableMeta | None, cond: exp.Expression | None, order: exp.Order | None,
                     ctx: str, grouped: bool = False) -> None:
        """Classify GET / partition SCAN / index SCAN / cross-partition SCAN. On a storage that is not given
        cross-partition scans (non-JDBC), fail every access that would need one -- ORDER BYs ScalarDB would push down
        to the storage, key IN-lists, predicates without a key -- so that the decomposer fetches by key and processes
        the rows in the application, or reports that nothing can be fetched by key (grouped queries over a keyed
        access are sorted by the SQL layer after aggregation and are unaffected)."""
        if meta is None:
            self.info("SCHEMA", f"{ctx}: table definition unknown, access path (GET / SCAN / cross-partition) not analysed")
            return
        ordered_scan = self.storage in ORDERED_SCAN_STORAGES
        pk = [c.lower() for c in meta.primary_key]
        pkey = [c.lower() for c in meta.partition_key]
        idx = [c.lower() for c in meta.secondary_indexes]
        keyish = set(idx) | ({pkey[0]} if len(pkey) == 1 else set())
        eq_cols: set[str] = set()
        range_cols: set[str] = set()
        key_or = None  # column of an OR / IN group over one partition-key or indexed column
        if cond is not None:
            if isinstance(_unparen(cond), exp.Or):
                if order is not None and not grouped and not ordered_scan:
                    self._no_ordered_scan(order, ctx)
                self._key_or_or_cross_partition(meta, self._key_or(cond, keyish), ctx,
                                                f"{ctx}: top-level OR forces a cross-partition scan on {meta.name}")
                return
            for leaf in _flatten(cond, exp.And):
                leaf = _unparen(leaf)
                if isinstance(leaf, exp.EQ) and isinstance(leaf.this, exp.Column):
                    eq_cols.add(leaf.this.name.lower())
                elif isinstance(leaf, (exp.GT, exp.GTE, exp.LT, exp.LTE, exp.Between)) and isinstance(leaf.this, exp.Column):
                    range_cols.add(leaf.this.name.lower())
                else:
                    if isinstance(leaf, exp.Or) and key_or is None:
                        key_or = self._key_or(leaf, keyish)
                    range_cols.add("?")
        if pk and all(c in eq_cols for c in pk):
            self.info("ACCESS", f"{ctx}: full primary key specified -> GET (single record)")
            return
        if pkey and all(c in eq_cols for c in pkey):
            self.info("ACCESS", f"{ctx}: full partition key specified -> partition SCAN")
            if order is not None and not grouped:
                ck = [c.lower() for c in meta.clustering_key]
                ords = [o for o in order.expressions if isinstance(o.this, exp.Column)]
                ocols = [o.this.name.lower() for o in ords]
                if len(ords) != len(order.expressions) or ocols != ck[:len(ocols)]:
                    if not ordered_scan:
                        self._no_ordered_scan(order, ctx, f" (not a prefix of the clustering key {ck})")
                    self.warn("ORDER", f"{ctx}: ORDER BY {ocols} is not a prefix of the clustering key {ck}; "
                                       f"ScalarDB falls back to a cross-partition scan with ordering (JDBC backends only)")
                elif not ordered_scan:
                    order_of = {c.lower(): o.upper() for c, o in meta.clustering_order.items()}
                    reversed_ = {bool(o.args.get("desc")) != (order_of.get(c, "ASC") == "DESC") for o, c in zip(ords, ocols)}
                    if len(reversed_) > 1:
                        self._no_ordered_scan(order, ctx, " (mixes the clustering order and its reverse)")
            return
        if any(c in eq_cols for c in idx) and order is None:
            self.info("ACCESS", f"{ctx}: equality on secondary index -> index SCAN")
            return
        if order is not None and not grouped and not ordered_scan:
            self._no_ordered_scan(order, ctx)
        self._key_or_or_cross_partition(meta, key_or, ctx,
                                        f"{ctx}: predicates do not cover the partition key {meta.partition_key} of "
                                        f"{meta.name} -> cross-partition SCAN (requires scalar.db.cross_partition_scan.enabled; "
                                        f"filtering/ordering across partitions is only recommended on JDBC backends)")

    @staticmethod
    def _key_or(e: exp.Expression, keyish: set[str]) -> str | None:
        leaves = [_unparen(x) for x in _flatten(e, exp.Or)]
        cols = {x.this.name.lower() for x in leaves if isinstance(x, exp.EQ) and isinstance(x.this, exp.Column)}
        if len(cols) == 1 and all(isinstance(x, exp.EQ) and isinstance(x.this, exp.Column) for x in leaves) \
                and next(iter(cols)) in keyish:
            return next(iter(cols))
        return None

    def _key_or_or_cross_partition(self, meta: TableMeta, key_or: str | None, ctx: str, message: str) -> None:
        if self.storage not in ORDERED_SCAN_STORAGES:
            if key_or and ctx == "SELECT":
                self.fail("OR_KEYS", f"{ctx}: OR / IN over {meta.name}.{key_or} runs as a scan of every partition on "
                                     f"{self.storage}; fetch each key with its own partition / index scan instead")
            self.fail("NO_CROSS_PARTITION",
                      message.split(" (requires")[0] + f"; cross-partition scans are used with JDBC backends only, so on "
                      f"{self.storage} " + ("the rows must be fetched by key and processed in the application"
                                             if ctx == "SELECT" else "select the keys first and write by primary key"))
        self.warn("CROSS_PARTITION", message)

    def _no_ordered_scan(self, order: exp.Order, ctx: str, why: str = "") -> None:
        cols = [o.this.sql() for o in order.expressions]
        self.fail("ORDER_STORAGE", f"{ctx}: ORDER BY {cols}{why} needs a cross-partition scan with ordering, which "
                                   f"ScalarDB does not support on {self.storage} (DB-CORE-10007); sort in the application")

    # -- SELECT ------------------------------------------------------------------------------------
    def select(self, s: exp.Select) -> exp.Select:
        ctx = "SELECT"
        if _arg(s, "with"):
            self.fail("CTE", "WITH (common table expressions) are not supported")
        if s.args.get("distinct"):
            self.fail("DISTINCT", "SELECT DISTINCT is not supported; de-duplicate in the application")
        if s.args.get("offset"):
            self.fail("OFFSET", "OFFSET is not supported; paginate with a clustering-key range predicate instead")
        if s.args.get("connect"):
            self.fail("HIERARCHICAL", "START WITH / CONNECT BY (hierarchical query) is not supported")
        if s.args.get("pivots"):
            self.fail("PIVOT", "PIVOT / UNPIVOT is not supported")
        for k in ("windows", "qualify", "laterals", "sample", "into", "cluster"):
            if s.args.get(k):
                self.fail("CLAUSE", f"{k.upper()} clause is not supported")
        if s.args.get("locks"):
            self.warn("LOCK", "FOR UPDATE / locking clause dropped (ScalarDB transactions handle isolation)")
            s.set("locks", None)
        from_ = _from(s)
        if from_ is None or not isinstance(from_.this, exp.Table):
            self.fail("FROM", "FROM must reference exactly one base table (no subqueries)")
        self._tables = [from_.this] + [j.this for j in s.args.get("joins") or [] if isinstance(j.this, exp.Table)]
        # projections
        for p in s.expressions:
            self._check_projection(p)
        # joins (also converts comma joins using WHERE equalities)
        where_expr = s.args["where"].this if s.args.get("where") else None
        where_expr = self._joins(s, where_expr)
        # ROWNUM -> LIMIT (Oracle)
        where_expr = self._rownum_to_limit(s, where_expr)
        # WHERE
        if where_expr is not None:
            s.set("where", exp.Where(this=self._build_condition(where_expr, "WHERE")))
        else:
            s.set("where", None)
        # GROUP BY / HAVING
        if s.args.get("group"):
            grp = s.args["group"]
            for k in ("rollup", "cube", "grouping_sets"):
                if grp.args.get(k):
                    self.fail("GROUP", f"GROUP BY {k.upper().replace('_', ' ')} is not supported")
            for g in grp.expressions:
                if isinstance(g, (exp.Rollup, exp.Cube, exp.GroupingSets)):
                    self.fail("GROUP", f"GROUP BY {type(g).__name__.upper()} is not supported")
                if not isinstance(g, exp.Column):
                    self.fail("GROUP", f"GROUP BY only accepts column names, got '{g.sql()}'")
        if s.args.get("having"):
            s.set("having", exp.Having(this=self._build_condition(s.args["having"].this, "HAVING", allow_agg=True)))
        # ORDER BY
        if s.args.get("order"):
            for o in s.args["order"].expressions:
                if o.args.get("nulls_first") is not None:
                    if re.search(r"NULLS\s+(FIRST|LAST)", self._source, re.I):
                        self.warn("NULLS", "NULLS FIRST/LAST dropped from ORDER BY")
                    o.set("nulls_first", None)
                if not (isinstance(o.this, (exp.Column, exp.Identifier)) or _is_aggregate(o.this)):
                    self.fail("ORDER", f"ORDER BY only accepts columns, aliases or aggregates, got '{o.this.sql()}'")
        # LIMIT / FETCH
        lim = s.args.get("limit")
        if isinstance(lim, exp.Fetch):
            if lim.args.get("percent") or (lim.args.get("limit_options") and lim.args["limit_options"].args.get("percent")):
                self.fail("LIMIT", "FETCH ... PERCENT is not supported")
            s.set("limit", exp.Limit(expression=lim.args["count"]))
            self.info("LIMIT", "FETCH FIRST n ROWS ONLY rewritten to LIMIT n")
        elif isinstance(lim, exp.Limit) and not _is_literal(lim.expression):
            self.fail("LIMIT", "LIMIT must be a literal or bind marker")
        grouped = bool(s.args.get("group")) or any(_is_aggregate(p.this if isinstance(p, exp.Alias) else p)
                                                   for p in s.expressions)
        self._access_path(self._meta(from_.this), s.args["where"].this if s.args.get("where") else None,
                          s.args.get("order"), ctx, grouped)
        return s

    def _check_projection(self, p: exp.Expression) -> None:
        inner = p.this if isinstance(p, exp.Alias) else p
        if isinstance(inner, (exp.Column, exp.Star)) or _is_aggregate(inner):
            return
        if isinstance(inner, AGGREGATES) and isinstance(inner.this, exp.Distinct):
            self.fail("AGG_DISTINCT", "COUNT(DISTINCT ...) is not supported")
        if isinstance(inner, AGGREGATES):
            # a supported function over an expression: the argument is the problem, not the function
            arg = inner.this.sql(dialect=self.dialect) if inner.this is not None else ""
            self.fail("AGG", f"aggregate {inner.sql_name()} over an expression ({arg}) is not supported; ScalarDB SQL "
                             f"aggregates only a column (or * for COUNT)")
        if isinstance(inner, exp.AggFunc):
            self.fail("AGG", f"aggregate {inner.sql_name()} is not supported (only COUNT, SUM, AVG, MIN, MAX)")
        self.fail("PROJECTION", f"projection '{inner.sql(dialect=self.dialect)}' is an expression; ScalarDB SQL only "
                                f"selects columns and aggregates. Compute it in the application")

    def _joins(self, s: exp.Select, where_expr: exp.Expression | None) -> exp.Expression | None:
        joins = s.args.get("joins") or []
        if not joins:
            return where_expr
        alias_of = {}
        base = _from(s).this
        alias_of[(base.alias or base.name).lower()] = base
        for j in joins:
            t = j.this
            if not isinstance(t, exp.Table):
                self.fail("JOIN", "joined relation must be a base table (no subqueries)")
            alias_of[(t.alias or t.name).lower()] = t
        for i, j in enumerate(joins):
            kind = (j.args.get("kind") or "").upper()
            side = (j.args.get("side") or "").upper()
            if kind in ("LEFT", "RIGHT", "FULL") and not side:  # eliminate_join_marks() puts the side into `kind`
                side, kind = kind, ""
                j.set("side", side)
                j.set("kind", None)
            if kind in ("CROSS", "NATURAL") or side == "FULL":
                self.fail("JOIN", f"{kind or side} JOIN is not supported")
            if j.args.get("using"):
                left = joins[i - 1].this if i else base
                using_cols = {u.name.lower() for u in j.args["using"]}
                on = [exp.EQ(this=exp.column(u.name, table=left.alias or left.name),
                             expression=exp.column(u.name, table=j.this.alias or j.this.name))
                      for u in j.args["using"]]
                j.set("using", None)
                j.set("on", exp.and_(*on))
                # the coalesced USING column is ambiguous once the join is ON-based: qualify it with the FROM table
                for c in s.find_all(exp.Column):
                    if not c.table and c.name.lower() in using_cols and c.find_ancestor(exp.Join) is None:
                        c.set("table", exp.to_identifier(base.alias or base.name))
                self.info("JOIN", "JOIN ... USING rewritten as JOIN ... ON")
            if not j.args.get("on"):
                # implicit (comma) join: pull column=column equalities between tables out of WHERE
                where_expr = self._comma_join_to_on(j, alias_of, where_expr)
            for leaf in _flatten(j.args["on"], exp.And):
                leaf = _unparen(leaf)
                if not (isinstance(leaf, exp.EQ) and isinstance(leaf.this, exp.Column) and isinstance(leaf.expression, exp.Column)):
                    self.fail("JOIN_ON", f"join predicate must be 'column = column' joined with AND, got '{leaf.sql()}'")
            if side == "RIGHT" and i != 0:
                self.fail("JOIN", "RIGHT OUTER JOIN must be the first join")
            meta = self._meta(j.this)
            if meta:
                jcols = {c.name.lower() for leaf in _flatten(j.args["on"], exp.And)
                         for c in _unparen(leaf).find_all(exp.Column) if (c.table or "").lower() == (j.this.alias or j.this.name).lower()}
                pk = {c.lower() for c in meta.primary_key}
                if not (pk <= jcols or any(c.lower() in jcols for c in meta.secondary_indexes)):
                    self.warn("JOIN_KEY", f"join on {meta.name} does not cover its full primary key {meta.primary_key} "
                                          f"or a secondary index; ScalarDB will reject this join")
            else:
                self.info("SCHEMA", f"join on {j.this.name}: table definition unknown, key coverage not checked")
        # ScalarDB rule: with INNER/LEFT JOIN, WHERE and ORDER BY may only reference the FROM table's columns;
        # with RIGHT JOIN (must be first) only the right table's columns.
        first_side = (joins[0].args.get("side") or "").upper()
        allowed = (joins[0].this.alias or joins[0].this.name).lower() if first_side == "RIGHT" \
            else (base.alias or base.name).lower()
        refs = list(where_expr.find_all(exp.Column)) if where_expr is not None else []
        if s.args.get("order"):
            refs += list(s.args["order"].find_all(exp.Column))
        for c in refs:
            q = (c.table or "").lower()
            if not q:
                owners = [a for a, t in alias_of.items() if (m := self.registry.get(t.name))
                          and c.name.lower() in {x.lower() for x in m.columns}]
                q = owners[0] if len(owners) == 1 else ""
            if q and q != allowed:
                self.fail("JOIN_SCOPE", f"column {c.sql()} belongs to a joined table; with JOIN, WHERE/ORDER BY may only "
                                        f"reference columns of the {'RIGHT JOIN' if first_side == 'RIGHT' else 'FROM'} table ({allowed})")
        return where_expr

    def _comma_join_to_on(self, j: exp.Join, alias_of: dict, where_expr: exp.Expression | None) -> exp.Expression | None:
        right = (j.this.alias or j.this.name).lower()
        if where_expr is None:
            self.fail("JOIN", "comma join without join condition (cartesian product) is not supported")
        keep, on = [], []
        for leaf in _flatten(where_expr, exp.And):
            u = _unparen(leaf)
            if isinstance(u, exp.EQ) and isinstance(u.this, exp.Column) and isinstance(u.expression, exp.Column) \
                    and right in {(u.this.table or "").lower(), (u.expression.table or "").lower()}:
                on.append(u)
            else:
                keep.append(leaf)
        if not on or isinstance(_unparen(where_expr), exp.Or):
            self.fail("JOIN", f"comma join with {j.this.name}: no 'a.col = b.col' equality found in WHERE to build ON")
        j.set("on", exp.and_(*on))
        j.set("kind", "INNER")
        self.warn("COMMA_JOIN", f"implicit comma join rewritten as INNER JOIN {j.this.name} ON {exp.and_(*on).sql()}")
        return exp.and_(*keep) if keep else None

    def _rownum_to_limit(self, s: exp.Select, where_expr: exp.Expression | None) -> exp.Expression | None:
        if where_expr is None:
            return None
        keep = []
        for leaf in _flatten(where_expr, exp.And):
            u = _unparen(leaf)
            if isinstance(u, COMPARISONS) and isinstance(u.this, exp.Column) and u.this.name.upper() == "ROWNUM":
                if not isinstance(u.expression, exp.Literal) or u.expression.is_string:
                    self.fail("ROWNUM", "ROWNUM must be compared with an integer literal")
                n = int(u.expression.name)
                if isinstance(u, exp.LT):
                    n -= 1
                elif isinstance(u, exp.EQ) and n == 1:
                    pass
                elif not isinstance(u, exp.LTE):
                    self.fail("ROWNUM", f"unsupported ROWNUM predicate '{u.sql()}'")
                if s.args.get("limit"):
                    self.fail("ROWNUM", "both ROWNUM and LIMIT/FETCH present")
                s.set("limit", exp.Limit(expression=exp.Literal.number(n)))
                self.warn("ROWNUM", f"'{u.sql()}' rewritten to LIMIT {n}. Note: Oracle applies ROWNUM before ORDER BY, "
                                    f"ScalarDB LIMIT applies after ORDER BY")
            else:
                keep.append(leaf)
        if any(c.name.upper() == "ROWNUM" for l in keep for c in l.find_all(exp.Column)):
            self.fail("ROWNUM", "ROWNUM inside OR / nested predicates cannot be converted")
        return exp.and_(*keep) if keep else None

    # -- INSERT / UPSERT / MERGE -------------------------------------------------------------------
    def insert(self, ins: exp.Insert) -> exp.Expression:
        if ins.args.get("ignore"):
            self.fail("INSERT_IGNORE", "INSERT IGNORE has no equivalent (INSERT fails on duplicate key)")
        if ins.args.get("returning"):
            self.fail("RETURNING", "RETURNING is not supported")
        if ins.args.get("overwrite") or ins.args.get("alternative"):
            self.fail("INSERT", "INSERT OVERWRITE / OR REPLACE variants are not supported")
        cols = [c.name for c in ins.this.expressions] if isinstance(ins.this, exp.Schema) else []
        if not cols:
            self.warn("INSERT_COLS", "no column list: ScalarDB uses table definition order; add an explicit column list")
        vals = ins.expression
        if not isinstance(vals, exp.Values):
            self.fail("INSERT_SELECT", "INSERT ... SELECT is not supported; read rows in the application then insert")
        for tup in vals.expressions:
            for i, v in enumerate(tup.expressions):
                tup.expressions[i].replace(self._value(v, f"VALUES column {cols[i] if i < len(cols) else i + 1}"))
        meta = self._meta(ins.this)
        if meta and cols:
            missing = [c for c in meta.primary_key if c.lower() not in {x.lower() for x in cols}]
            if missing:
                self.fail("PK", f"INSERT must specify the full primary key; missing {missing}")
        conflict = ins.args.get("conflict")
        node: exp.Insert = ins
        if isinstance(ins, Upsert):
            pass
        elif conflict is not None:
            node = self._conflict_to_upsert(ins, conflict, cols)
        return node

    def _conflict_to_upsert(self, ins: exp.Insert, conflict: exp.OnConflict, cols: list[str]) -> exp.Expression:
        action = (conflict.args.get("action").name if conflict.args.get("action") else "").upper()
        if "NOTHING" in action or (not conflict.expressions and not conflict.args.get("duplicate")):
            self.fail("DO_NOTHING", "ON CONFLICT DO NOTHING has no equivalent; catch the duplicate-key error in the "
                                    "application or read before insert")
        set_cols = []
        for eq in conflict.expressions:
            if not isinstance(eq, exp.EQ):
                self.fail("UPSERT", f"unsupported conflict action '{eq.sql()}'")
            target, src = eq.this.name, eq.expression
            same = (isinstance(src, exp.Column) and src.table and src.table.upper() == "EXCLUDED" and src.name.lower() == target.lower()) \
                or (isinstance(src, exp.Anonymous) and src.name.upper() == "VALUES" and src.expressions
                    and src.expressions[0].name.lower() == target.lower())
            if not same:
                self.fail("UPSERT", f"ON CONFLICT/DUPLICATE KEY update '{eq.sql()}' is not a plain "
                                    f"'col = EXCLUDED.col / VALUES(col)'; UPSERT cannot express it "
                                    f"(read-modify-write inside a transaction instead)")
            set_cols.append(target.lower())
        non_key = [c for c in cols if c.lower() not in set_cols]
        meta = self._meta(ins.this)
        pk = {c.lower() for c in meta.primary_key} if meta else set()
        pk |= {k.this.name.lower() for k in conflict.args.get("conflict_keys") or [] if isinstance(k.this, exp.Column)}
        extra = [c for c in non_key if c.lower() not in pk]
        if extra and not pk:
            self.warn("UPSERT", f"converted to UPSERT: on conflict ScalarDB overwrites ALL listed columns, the original "
                                f"only updated {set_cols}; {extra} are also overwritten unless they are key columns "
                                f"(table definition unknown)")
        elif extra:
            self.warn("UPSERT", f"converted to UPSERT: on conflict ScalarDB overwrites ALL listed columns, "
                                f"the original only updated {set_cols}; {extra} will also be overwritten")
        else:
            self.info("UPSERT", "ON CONFLICT DO UPDATE / ON DUPLICATE KEY UPDATE rewritten as UPSERT")
        args = dict(ins.args)
        args.pop("conflict", None)
        return Upsert(**args)

    def merge(self, m: exp.Merge) -> exp.Expression:
        src = m.args.get("using")
        row: dict[str, exp.Expression] = {}
        if isinstance(src, exp.Subquery) and isinstance(src.this, exp.Select) and not src.this.args.get("where"):
            for p in src.this.expressions:
                if isinstance(p, exp.Alias) and _is_literal(p.this):
                    row[p.alias.lower()] = p.this
                else:
                    self.fail("MERGE", f"MERGE source column '{p.sql()}' is not a constant")
        elif isinstance(src, exp.Values):
            self.fail("MERGE", "MERGE ... USING (VALUES ...) with column aliases is not handled by this PoC")
        else:
            self.fail("MERGE", "MERGE from a table/query source is not supported; only constant single-row sources can "
                               "become UPSERT")
        src_alias = (src.alias or "").lower()
        whens = m.args.get("whens")
        ins_cols, ins_vals = None, None
        for w in (whens.expressions if whens else []):
            then = w.args.get("then")
            if isinstance(then, exp.Insert):
                ins_cols = [c.name for c in then.this.expressions] if isinstance(then.this, (exp.Schema, exp.Tuple)) else []
                vals = then.expression
                ins_vals = vals.expressions[0].expressions if isinstance(vals, exp.Values) else vals.expressions
            elif isinstance(then, exp.Update):
                for eq in then.expressions:
                    v = eq.expression
                    if not (isinstance(v, exp.Column) and (v.table or "").lower() == src_alias and v.name.lower() == eq.this.name.lower()):
                        self.fail("MERGE", f"MERGE UPDATE '{eq.sql()}' is not 'col = src.col'; cannot express as UPSERT")
            elif isinstance(then, exp.Var) and then.name.upper() == "DELETE":
                self.fail("MERGE", "MERGE ... WHEN MATCHED THEN DELETE cannot be expressed as UPSERT")
        if not ins_cols:
            self.fail("MERGE", "MERGE without WHEN NOT MATCHED THEN INSERT cannot be expressed as UPSERT")
        values = []
        for v in ins_vals:
            if isinstance(v, exp.Column) and v.name.lower() in row:
                values.append(row[v.name.lower()])
            else:
                values.append(self._value(v, "MERGE INSERT"))
        self.warn("MERGE", "MERGE rewritten as UPSERT (all listed columns are overwritten when the row exists)")
        target = m.this.copy()
        target.set("alias", None)
        return Upsert(this=exp.Schema(this=target, expressions=[exp.to_identifier(c) for c in ins_cols]),
                      expression=exp.Values(expressions=[exp.Tuple(expressions=values)]))

    # -- UPDATE / DELETE ---------------------------------------------------------------------------
    def update(self, u: exp.Update) -> exp.Update:
        self._tables = [u.this] if isinstance(u.this, exp.Table) else []
        if _from(u) or u.args.get("joins") or (isinstance(u.this, exp.Table) and u.this.args.get("joins")):
            self.fail("UPDATE_JOIN", "UPDATE with FROM/JOIN is not supported; SELECT the keys first, then UPDATE by key")
        if u.args.get("returning"):
            self.fail("RETURNING", "RETURNING is not supported")
        if u.args.get("limit") or u.args.get("order"):
            self.fail("UPDATE", "UPDATE ... ORDER BY / LIMIT is not supported")
        for eq in u.expressions:
            if not isinstance(eq, exp.EQ) or not isinstance(eq.this, exp.Column):
                self.fail("SET", f"unsupported SET clause '{eq.sql()}'")
            v = eq.expression
            if isinstance(v, exp.Column) and v.name.lower() == eq.this.name.lower() or v.find(exp.Column):
                self.fail("RMW", f"SET {eq.sql(dialect=self.dialect)}: expressions referencing columns are not allowed; "
                                 f"do SELECT -> compute -> UPDATE with a literal inside one ScalarDB transaction")
            eq.set("expression", self._value(v, f"SET {eq.this.name}"))
            eq.this.set("table", None)
        where = u.args.get("where")
        cond = self._build_condition(where.this, "WHERE") if where else None
        u.set("where", exp.Where(this=cond) if cond is not None else None)
        if cond is None:
            self.warn("NO_WHERE", "UPDATE without WHERE updates every partition (cross-partition scan must be enabled)")
        self._access_path(self._meta(u.this), cond, None, "UPDATE")
        return u

    def delete(self, d: exp.Delete) -> exp.Delete:
        self._tables = [d.this] if isinstance(d.this, exp.Table) else []
        # MySQL multi-table DELETE (DELETE t FROM t JOIN u ...): sqlglot keeps the targets in `tables` and the joins on
        # the table itself
        if d.args.get("using") or d.args.get("joins") or d.args.get("tables") or \
                (isinstance(d.this, exp.Table) and d.this.args.get("joins")):
            self.fail("DELETE_JOIN", "DELETE ... USING / JOIN is not supported; SELECT the keys first, then DELETE by key")
        if d.args.get("returning"):
            self.fail("RETURNING", "RETURNING is not supported")
        if d.args.get("limit") or d.args.get("order"):
            self.fail("DELETE", "DELETE ... ORDER BY / LIMIT is not supported")
        where = d.args.get("where")
        cond = self._build_condition(where.this, "WHERE") if where else None
        d.set("where", exp.Where(this=cond) if cond is not None else None)
        if cond is None:
            self.warn("NO_WHERE", "DELETE without WHERE deletes every partition (cross-partition scan must be enabled)")
        self._access_path(self._meta(d.this), cond, None, "DELETE")
        return d

    # -- DDL ---------------------------------------------------------------------------------------
    def create(self, c: exp.Create) -> list:
        kind = (c.args.get("kind") or "").upper()
        if kind == "TABLE":
            return self.create_table(c)
        if kind == "INDEX":
            return [self.create_index(c)]
        if kind in ("SCHEMA", "DATABASE"):
            return [f"CREATE NAMESPACE {'IF NOT EXISTS ' if c.args.get('exists') else ''}{c.this.name}"]
        self.fail("DDL", f"CREATE {kind} is not supported (no views, sequences, triggers, procedures in ScalarDB)")

    def create_table(self, c: exp.Create) -> list:
        props = c.args.get("properties")
        if props:
            for p in props.expressions:
                if isinstance(p, exp.TemporaryProperty):
                    self.fail("TEMP", "temporary tables are not supported")
            self.info("TABLE_OPTS", f"table options dropped: {props.sql(dialect=self.dialect)[:60]}")
        if not isinstance(c.this, exp.Schema):
            self.fail("DDL", "CREATE TABLE ... AS SELECT / LIKE is not supported")
        tname = self._table_name(c.this)
        ns, _, bare = tname.rpartition(".")
        columns: dict[str, str] = {}
        pk: list[str] = []
        extra_stmts: list[str] = []
        for item in c.this.expressions:
            if isinstance(item, exp.ColumnDef):
                self._column_def(item, columns, pk)
            elif isinstance(item, exp.PrimaryKey):
                pk[:] = [e.name for e in item.expressions]
            elif isinstance(item, exp.Constraint):
                for sub in item.expressions:
                    if isinstance(sub, exp.PrimaryKey):
                        pk[:] = [e.name for e in sub.expressions]
                    elif isinstance(sub, exp.ForeignKey):
                        self.warn("FK", f"foreign key constraint '{item.this.name}' dropped (no referential integrity in ScalarDB)")
                    elif isinstance(sub, exp.UniqueColumnConstraint):
                        self.warn("UNIQUE", f"unique constraint '{item.this.name}' dropped (secondary indexes are not unique)")
                    elif isinstance(sub, exp.CheckColumnConstraint):
                        self.warn("CHECK", f"check constraint '{item.this.name}' dropped; enforce in the application")
                    else:
                        self.warn("CONSTRAINT", f"constraint '{item.sql(dialect=self.dialect)[:50]}' dropped")
            elif isinstance(item, exp.ForeignKey):
                self.warn("FK", "foreign key dropped (no referential integrity in ScalarDB)")
            elif isinstance(item, exp.UniqueColumnConstraint):
                self.warn("UNIQUE", "unique constraint dropped (secondary indexes are not unique)")
            elif isinstance(item, exp.CheckColumnConstraint):
                self.warn("CHECK", "check constraint dropped; enforce in the application")
            elif isinstance(item, (exp.IndexColumnConstraint, exp.Index)):
                cols = [x.name for x in (item.args.get("expressions") or item.args.get("params", exp.Tuple()).args.get("columns", []))]
                cols = [x if isinstance(x, str) else x.name for x in cols]
                if len(cols) == 1:
                    extra_stmts.append(f"CREATE INDEX ON {tname} ({cols[0]})")
                    self.info("INDEX", f"inline index on {cols[0]} emitted as a separate CREATE INDEX")
                else:
                    self.warn("INDEX", f"inline composite index {cols} dropped (ScalarDB indexes are single-column)")
            else:
                self.warn("DDL", f"table element '{item.sql(dialect=self.dialect)[:50]}' dropped")
        if not pk:
            self.fail("PK", "table has no PRIMARY KEY; ScalarDB requires a partition key (add PRIMARY KEY or pass --keys)")
        hint = self.key_hints.get(bare.lower())
        if hint:
            pkey, ckey = hint
            unknown = [c for c in pkey + ckey if c not in columns]
            if unknown:
                self.fail("KEYS", f"--keys references unknown columns {unknown}")
        else:
            pkey, ckey = pk[:1], pk[1:]
            if ckey:
                self.info("KEYS", f"primary key {pk}: first column '{pkey[0]}' used as partition key, {ckey} as "
                                  f"clustering key(s). Review with --keys if a different split is needed")
        meta = TableMeta(ns or None, bare, pkey, ckey, {}, columns)
        for ix in extra_stmts:
            meta.secondary_indexes.append(ix.rsplit("(", 1)[1].rstrip(")"))
        self.registry.add(meta)
        cols_sql = ",\n  ".join(f"{n} {t}" for n, t in columns.items())
        if len(pkey) == 1 and not ckey:
            cols_sql = ",\n  ".join(f"{n} {t}{' PRIMARY KEY' if n == pkey[0] else ''}" for n, t in columns.items())
            pk_sql = ""
        else:
            p = f"({', '.join(pkey)})" if len(pkey) > 1 else pkey[0]
            pk_sql = f",\n  PRIMARY KEY ({p}{', ' + ', '.join(ckey) if ckey else ''})"
        exists = "IF NOT EXISTS " if c.args.get("exists") else ""
        return [f"CREATE TABLE {exists}{tname} (\n  {cols_sql}{pk_sql}\n)"] + extra_stmts

    def _column_def(self, cd: exp.ColumnDef, columns: dict[str, str], pk: list[str]) -> None:
        name = cd.this.name
        if cd.kind is None:
            self.fail("DDL", f"column {name} has no data type")
        tm = map_type(cd.kind, self.dialect)
        if tm.scalardb_type is None:
            self.fail("TYPE", f"column {name}: {tm.note}")
        if tm.severity == "ERROR":
            self.fail("TYPE", f"column {name}: {tm.note}")
        if tm.severity == "WARN":
            self.warn("TYPE", f"column {name}: {tm.note}")
        elif tm.note:
            self.info("TYPE", f"column {name}: {tm.note}")
        columns[name] = tm.scalardb_type
        for con in cd.constraints or []:
            k = con.kind
            if isinstance(k, exp.PrimaryKeyColumnConstraint):
                pk[:] = [name]
            elif isinstance(k, exp.NotNullColumnConstraint):
                if k.args.get("allow_null"):
                    continue
                self.info("NOT_NULL", f"column {name}: NOT NULL dropped (ScalarDB columns are nullable; enforce in the application)")
            elif isinstance(k, exp.DefaultColumnConstraint):
                self.warn("DEFAULT", f"column {name}: DEFAULT {k.this.sql(dialect=self.dialect)} dropped; the application must supply the value")
            elif isinstance(k, (exp.AutoIncrementColumnConstraint, exp.GeneratedAsIdentityColumnConstraint)):
                self.fail("AUTO_INC", f"column {name}: AUTO_INCREMENT / IDENTITY / SERIAL is not supported; generate keys in the application (e.g. UUID as TEXT)")
            elif isinstance(k, exp.UniqueColumnConstraint):
                self.warn("UNIQUE", f"column {name}: UNIQUE dropped (a secondary index does not enforce uniqueness)")
            elif isinstance(k, exp.CheckColumnConstraint):
                self.warn("CHECK", f"column {name}: CHECK dropped; enforce in the application")
            elif isinstance(k, exp.Reference):
                self.warn("FK", f"column {name}: REFERENCES dropped (no referential integrity)")
            elif isinstance(k, (exp.CommentColumnConstraint, exp.CollateColumnConstraint, exp.CharacterSetColumnConstraint)):
                self.info("COL_OPT", f"column {name}: {con.sql(dialect=self.dialect)[:40]} dropped")
            elif isinstance(k, exp.GeneratedAsRowColumnConstraint) or isinstance(k, exp.ComputedColumnConstraint):
                self.fail("GENERATED", f"column {name}: generated/computed columns are not supported")
            else:
                self.warn("COL_OPT", f"column {name}: constraint '{con.sql(dialect=self.dialect)[:40]}' dropped")

    def create_index(self, c: exp.Create) -> str:
        idx = c.this
        cols = [o.this for o in idx.args["params"].args.get("columns", [])] if idx.args.get("params") else []
        if len(cols) != 1 or not isinstance(cols[0], exp.Column):
            self.fail("INDEX", f"ScalarDB secondary indexes are single-column; got {[x.sql() for x in cols]}. "
                               f"Consider making the leading column a partition key / clustering key instead")
        if c.args.get("unique"):
            self.warn("UNIQUE", "UNIQUE index converted to a plain secondary index (uniqueness not enforced)")
        col = cols[0].name
        tname = self._table_name(idx.args["table"])
        self.registry.add_index(tname.rpartition(".")[2], col)
        self.info("INDEX", f"index name '{idx.name}' dropped: ScalarDB identifies indexes by table + column")
        return f"CREATE INDEX {'IF NOT EXISTS ' if c.args.get('exists') else ''}ON {tname} ({col})"

    def drop(self, d: exp.Drop) -> str:
        kind = (d.args.get("kind") or "").upper()
        exists = "IF EXISTS " if d.args.get("exists") else ""
        if kind == "TABLE":
            return f"DROP TABLE {exists}{self._table_name(d.this)}"
        if kind in ("SCHEMA", "DATABASE"):
            return f"DROP NAMESPACE {exists}{d.this.name}{' CASCADE' if d.args.get('cascade') else ''}"
        if kind == "INDEX":
            self.fail("DROP_INDEX", "DROP INDEX must name table and column in ScalarDB: DROP INDEX ON <table> (<column>)")
        self.fail("DDL", f"DROP {kind} is not supported")

    def alter(self, a: exp.Alter) -> list:
        if (a.args.get("kind") or "").upper() != "TABLE":
            self.fail("DDL", f"ALTER {a.args.get('kind')} is not supported")
        tname = self._table_name(a.this)
        out = []
        for act in a.args.get("actions") or []:
            if isinstance(act, exp.ColumnDef):
                tm = map_type(act.kind, self.dialect)
                if tm.scalardb_type is None or tm.severity == "ERROR":
                    self.fail("TYPE", f"column {act.this.name}: {tm.note}")
                if act.constraints:
                    self.warn("COL_OPT", f"ADD COLUMN {act.this.name}: constraints dropped")
                out.append(f"ALTER TABLE {tname} ADD COLUMN {act.this.name} {tm.scalardb_type}")
            elif isinstance(act, exp.Drop) and (act.args.get("kind") or "").upper() == "COLUMN":
                out.append(f"ALTER TABLE {tname} DROP COLUMN {act.this.name}")
            elif isinstance(act, exp.RenameColumn):
                out.append(f"ALTER TABLE {tname} RENAME COLUMN {act.this.name} TO {act.args['to'].name}")
            elif isinstance(act, exp.AlterRename):
                out.append(f"ALTER TABLE {tname} RENAME TO {act.this.name}")
            elif isinstance(act, exp.ModifyColumn) or (isinstance(act, exp.AlterColumn) and act.args.get("dtype")):
                cd = act.this if isinstance(act, exp.ModifyColumn) else act
                dtype = cd.kind if isinstance(cd, exp.ColumnDef) else act.args["dtype"]
                name = cd.this.name if isinstance(cd, exp.ColumnDef) else act.this.name
                tm = map_type(dtype, self.dialect)
                if tm.scalardb_type is None or tm.severity == "ERROR":
                    self.fail("TYPE", f"column {name}: {tm.note}")
                out.append(f"ALTER TABLE {tname} ALTER COLUMN {name} SET DATA TYPE {tm.scalardb_type}")
                self.warn("ALTER_TYPE", "type change support depends on the underlying database")
            else:
                self.fail("ALTER", f"ALTER TABLE action '{act.sql(dialect=self.dialect)[:60]}' is not supported "
                                   f"(constraints, indexes, partitions, engine options ...)")
        if len(out) > 1:
            self.info("ALTER", "multiple actions split into separate ALTER TABLE statements (not atomic)")
        return out


# --------------------------------------------------------------------------------------------------
# script entry point
# --------------------------------------------------------------------------------------------------

def convert_script(text: str, dialect: str, registry: SchemaRegistry | None = None,
                   key_hints: dict[str, tuple[list[str], list[str]]] | None = None,
                   decompose: bool = True, storage: str = "jdbc",
                   expected_rows: dict[str, tuple[int, int | None]] | None = None, isolation: str = "SERIALIZABLE",
                   row_limit: int = DEFAULT_ROW_LIMIT, h2_indexes: bool = False) -> tuple[list[Result], SchemaRegistry]:
    """storage: the storage behind ScalarDB ("jdbc", or a non-JDBC one such as "cassandra"); it decides whether a
    cross-partition ORDER BY can be pushed down and whether a key IN-list is worth splitting.
    expected_rows / isolation / row_limit only feed the cost estimates (appside.estimate_cost).
    h2_indexes: plans tell the runtime to index the fetched tables in H2 (for batch jobs joining large fetches)."""
    registry = registry or SchemaRegistry()
    conv = StatementConverter(dialect, registry, key_hints or {}, decompose=decompose, storage=storage,
                              expected_rows=expected_rows, isolation=isolation, row_limit=row_limit,
                              h2_indexes=h2_indexes)
    results = []
    for i, stmt in enumerate(_split_statements(text, dialect), start=1):
        r = conv.convert(stmt)
        r.index = i
        results.append(r)
    return results, registry
