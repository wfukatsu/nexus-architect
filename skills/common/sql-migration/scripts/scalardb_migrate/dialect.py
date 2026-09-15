"""sqlglot dialect definition for ScalarDB SQL (generation side).

Only the output (Generator) matters for migration; parsing is done with the source dialect.
The generator is intentionally strict: it emits only constructs that exist in the ScalarDB SQL grammar,
so anything the converter forgot to rewrite shows up as a sqlglot UnsupportedError instead of silently
producing SQL that ScalarDB would reject.
"""

from __future__ import annotations

from sqlglot import exp
from sqlglot.dialects.dialect import Dialect
from sqlglot.errors import ErrorLevel, UnsupportedError
from sqlglot.generator import Generator
from sqlglot.tokens import Tokenizer


class Upsert(exp.Insert):
    """Marker node: an INSERT that must be emitted as ScalarDB `UPSERT INTO`."""


def _not_sql(self: Generator, e: exp.Not) -> str:
    inner = e.this
    if isinstance(inner, exp.Paren):
        inner = inner.this
    if isinstance(inner, exp.Is) and isinstance(inner.expression, exp.Null):
        return f"{self.sql(inner, 'this')} IS NOT NULL"
    if isinstance(inner, exp.Like):
        return f"{self.sql(inner, 'this')} NOT LIKE {self.sql(inner, 'expression')}"
    raise UnsupportedError(f"NOT is only supported as IS NOT NULL / NOT LIKE: {e.sql()}")


def _placeholder_sql(self: Generator, e: exp.Placeholder) -> str:
    return f":{e.name}" if e.this else "?"


_TYPED_LITERAL = {
    exp.DataType.Type.DATE: "DATE",
    exp.DataType.Type.TIME: "TIME",
    exp.DataType.Type.TIMESTAMP: "TIMESTAMP",
    exp.DataType.Type.DATETIME: "TIMESTAMP",
    exp.DataType.Type.TIMESTAMPTZ: "TIMESTAMPTZ",
}


def _cast_sql(self: Generator, e: exp.Cast) -> str:
    # DATE '2024-01-01' style typed literals are the only CAST-like form ScalarDB accepts
    if isinstance(e.this, exp.Literal) and e.this.is_string and e.to.this in _TYPED_LITERAL:
        return f"{_TYPED_LITERAL[e.to.this]} '{e.this.name}'"
    raise UnsupportedError(f"CAST is not supported by ScalarDB SQL: {e.sql()}")


def _unsupported(what: str):
    def fn(self: Generator, e: exp.Expression) -> str:
        raise UnsupportedError(f"{what} is not supported by ScalarDB SQL: {e.sql()[:80]}")
    return fn


class ScalarDB(Dialect):
    class Tokenizer(Tokenizer):
        QUOTES = ["'"]
        IDENTIFIERS = ['"']
        HEX_STRINGS = [("X'", "'"), ("x'", "'")]

    class Generator(Generator):
        TYPE_MAPPING = {
            **{t: "INT" for t in (exp.DataType.Type.TINYINT, exp.DataType.Type.SMALLINT, exp.DataType.Type.INT)},
            exp.DataType.Type.BIGINT: "BIGINT",
            exp.DataType.Type.FLOAT: "FLOAT",
            exp.DataType.Type.DOUBLE: "DOUBLE",
            exp.DataType.Type.BOOLEAN: "BOOLEAN",
            exp.DataType.Type.TEXT: "TEXT",
            exp.DataType.Type.VARCHAR: "TEXT",
            exp.DataType.Type.CHAR: "TEXT",
            exp.DataType.Type.BLOB: "BLOB",
            exp.DataType.Type.VARBINARY: "BLOB",
            exp.DataType.Type.DATE: "DATE",
            exp.DataType.Type.TIME: "TIME",
            exp.DataType.Type.TIMESTAMP: "TIMESTAMP",
            exp.DataType.Type.DATETIME: "TIMESTAMP",
            exp.DataType.Type.TIMESTAMPTZ: "TIMESTAMPTZ",
        }

        TRANSFORMS = {
            **Generator.TRANSFORMS,
            exp.Not: _not_sql,
            exp.Placeholder: _placeholder_sql,
            exp.Parameter: lambda self, e: "?",
            exp.Transaction: lambda self, e: "BEGIN",
            exp.Commit: lambda self, e: "COMMIT",
            exp.Rollback: lambda self, e: "ROLLBACK",
            Upsert: lambda self, e: "UPSERT" + self.insert_sql(e)[len("INSERT"):],
            exp.HexString: lambda self, e: f"X'{e.this}'",
            exp.Subquery: _unsupported("subquery"),
            exp.Union: _unsupported("UNION"),
            exp.Intersect: _unsupported("INTERSECT"),
            exp.Except: _unsupported("EXCEPT"),
            exp.With: _unsupported("CTE (WITH)"),
            exp.Window: _unsupported("window function"),
            exp.In: _unsupported("IN (rewrite to OR-chain first)"),
            exp.Offset: _unsupported("OFFSET"),
            exp.Distinct: _unsupported("DISTINCT"),
            exp.Case: _unsupported("CASE expression"),
            exp.Returning: _unsupported("RETURNING"),
            exp.OnConflict: _unsupported("ON CONFLICT / ON DUPLICATE KEY (rewrite to UPSERT first)"),
            exp.Fetch: _unsupported("FETCH (rewrite to LIMIT first)"),
            exp.Cast: _cast_sql,
            exp.TryCast: _cast_sql,
        }

        def datatype_sql(self, expression: exp.DataType) -> str:
            # ScalarDB types never take parameters (no VARCHAR(n), NUMBER(p,s), TIMESTAMP(6) ...)
            name = self.TYPE_MAPPING.get(expression.this)
            if name is None:
                raise UnsupportedError(f"data type {expression.sql()} has no ScalarDB equivalent")
            return name

        def ordered_sql(self, expression: exp.Ordered) -> str:
            # ScalarDB: order_key [ASC|DESC] only, no NULLS FIRST/LAST
            return f"{self.sql(expression, 'this')}{' DESC' if expression.args.get('desc') else ''}"

        def limit_sql(self, expression: exp.Limit, top: bool = False) -> str:
            return f" LIMIT {self.sql(expression, 'expression')}"

        def function_fallback_sql(self, expression: exp.Func) -> str:
            if isinstance(expression, (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)):
                return super().function_fallback_sql(expression)
            raise UnsupportedError(f"function {expression.sql_name()} is not supported by ScalarDB SQL")

        def anonymous_sql(self, expression: exp.Anonymous) -> str:
            raise UnsupportedError(f"function {expression.name} is not supported by ScalarDB SQL")


def to_scalardb_sql(node: exp.Expression) -> str:
    """Generate ScalarDB SQL from a (rewritten) sqlglot AST. Raises UnsupportedError for unconvertible nodes."""
    return node.sql(dialect="scalardb", unsupported_level=ErrorLevel.RAISE, identify=False, pretty=False)
