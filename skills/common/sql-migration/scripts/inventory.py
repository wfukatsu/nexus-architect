#!/usr/bin/env python3
"""Inventory every SQL statement a ScalarDB migration has to decide.

Sources, all read and never executed:

  --app-root DIR   application code: MyBatis mapper XML, Java (JDBC / Spring JDBC calls, JPA @Query),
                   and .sql resources under the root
  --sql-file FILE  a SQL script the user supplies
  --db-run DIR     a /architect:investigate-db-design run (evidence lines re-read from the original DDL,
                   hash-checked) or an investigate-db-live run (views and routines counted as unavailable:
                   a live run holds no definitions)

    python3 inventory.py --source oracle|postgres|mysql --out reports/03_design/sql-migration/sql-inventory.json \
        [--app-root DIR]... [--sql-file FILE]... [--db-run DIR]... [--previous old-inventory.json] \
        [--exclude GLOB]... [--project-dir DIR]

String literals are never stored: each statement keeps its SQL with literals masked, the hash of the full
text, and the evidence to re-extract the full text on demand (statement_text), which refuses a source that
changed since. Dynamic SQL (string concatenation with a variable, MyBatis dynamic elements, ${...}) is
flagged, never expanded. IDs are SQM-###, kept across runs when --previous is given.

Exit 0: inventory written; 2: written with problems (stale or missing evidence, unreadable files);
1: fatal (no source, bad input).
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA_VERSION = 1
DIALECTS = ("oracle", "postgres", "mysql")
SKIP_DIRS = {".git", ".gradle", ".idea", ".mvn", "build", "node_modules", "out", "target"}
DEFINITION_KINDS = {"view", "function", "procedure", "package", "trigger"}

SQL_START = re.compile(r"^\s*(?:\(\s*)*(?:SELECT|WITH|INSERT|UPDATE|DELETE|MERGE|UPSERT|REPLACE|CREATE|ALTER|DROP|"
                       r"TRUNCATE|CALL|EXEC|EXECUTE|BEGIN|DECLARE)\b|^\s*\{\s*(?:\?\s*=\s*)?call\b", re.I)
JPQL_START = re.compile(r"^\s*(?:SELECT|UPDATE|DELETE)\b", re.I)
STRING_LITERAL = re.compile(r"'(?:''|[^'])*'")

# Methods whose first argument is SQL: JDBC, Spring JdbcTemplate / NamedParameterJdbcTemplate, JPA native queries.
SQL_METHODS = {"prepareStatement", "prepareCall", "executeQuery", "executeUpdate", "executeLargeUpdate", "execute",
               "addBatch", "createNativeQuery", "query", "queryForObject", "queryForList", "queryForMap",
               "queryForRowSet", "queryForStream", "update", "batchUpdate"}
JPQL_METHODS = {"createQuery"}
CONTROL_WORDS = {"if", "for", "while", "switch", "catch", "synchronized", "try", "return", "new", "else", "do"}

MYBATIS_STATEMENT = re.compile(r"<(select|insert|update|delete)\b([^>]*)>(.*?)</\1\s*>", re.S | re.I)
MYBATIS_FRAGMENT = re.compile(r"<sql\b([^>]*)>(.*?)</sql\s*>", re.S | re.I)
MYBATIS_INCLUDE = re.compile(r"<include\b([^>]*?)(?:/>|>.*?</include\s*>)", re.S | re.I)
MYBATIS_DYNAMIC = ("if", "choose", "when", "otherwise", "where", "set", "trim", "foreach", "bind")
MYBATIS_TAG = re.compile(r"<(/?)(" + "|".join(MYBATIS_DYNAMIC) + r")\b[^>]*?(/?)>", re.I)


class StaleEvidence(Exception):
    """The source a statement was inventoried from no longer yields the same text."""


def _sha(data) -> str:
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def mask(text: str) -> str:
    return STRING_LITERAL.sub("'?'", text)


def category(text: str) -> str:
    s = re.sub(r"^(?:\s+|--[^\n]*(?:\n|$)|/\*.*?\*/|\()*", "", text, flags=re.S).upper()
    if re.match(r"\{\s*(\?\s*=\s*)?CALL\b|(CALL|EXEC|EXECUTE)\b", s):
        return "call"
    if re.match(r"CREATE\s+(OR\s+REPLACE\s+)?((NON)?EDITIONABLE\s+)?(MATERIALIZED\s+)?VIEW\b", s):
        return "view"
    if re.match(r"CREATE\s+(OR\s+REPLACE\s+)?((NON)?EDITIONABLE\s+)?(FUNCTION|PROCEDURE|PACKAGE|TYPE\s+BODY)\b", s):
        return "routine"
    if re.match(r"CREATE\s+(OR\s+REPLACE\s+)?((NON)?EDITIONABLE\s+)?TRIGGER\b", s):
        return "trigger"
    if re.match(r"(CREATE|ALTER|DROP|TRUNCATE|COMMENT|RENAME|GRANT|REVOKE)\b", s):
        return "ddl"
    if re.match(r"(SELECT|WITH)\b", s):
        return "query"
    if re.match(r"(INSERT|UPDATE|DELETE|MERGE|UPSERT|REPLACE)\b", s):
        return "dml"
    if re.match(r"(BEGIN|COMMIT|ROLLBACK|SAVEPOINT|START\s+TRANSACTION|SET\s+TRANSACTION)\b", s):
        return "transaction"
    return "other"


def _statement(origin: dict, text: str, *, key: str, language: str = "sql", reasons=(), binds=()) -> tuple[dict, str]:
    masked = mask(text)
    stmt = {
        "id": None,
        "fingerprint": _sha("\n".join([origin["kind"], origin["path"], origin.get("locator", ""), _collapse(masked), key])),
        "origin": origin,
        "category": category(text),
        "language": language,
        "dynamic": bool(reasons),
        "dynamic_reasons": list(dict.fromkeys(reasons)),
        "sql": _collapse(masked),
        "binds": list(binds),
        "text_sha256": _sha(text),
    }
    return stmt, text


def _occurrence(seen: dict, *parts) -> str:
    k = "\n".join(parts)
    seen[k] = seen.get(k, 0) + 1
    return str(seen[k])


# ------------------------------------------------------------------------------------------------- MyBatis

def _attr(attrs: str, name: str) -> str | None:
    m = re.search(rf'\b{name}\s*=\s*"([^"]*)"', attrs)
    return m.group(1) if m else None


def _blank(match: re.Match) -> str:
    return re.sub(r"[^\n]", " ", match.group())


def _from_mapper(path: Path, rel: str, raw: bytes) -> list[tuple[dict, str]]:
    xml = re.sub(r"<!--.*?-->", _blank, raw.decode("utf-8-sig"), flags=re.S)
    namespace = _attr(re.search(r"<mapper\b([^>]*)>", xml).group(1), "namespace") or path.stem
    fragments = {_attr(m.group(1), "id"): m.group(2) for m in MYBATIS_FRAGMENT.finditer(xml)}
    digest, seen, out = _sha(raw), {}, []
    for m in MYBATIS_STATEMENT.finditer(xml):
        body, reasons = m.group(3), []
        for _ in range(10):  # includes may nest
            def include(im):
                ref = _attr(im.group(1), "refid")
                if ref in fragments:
                    return fragments[ref]
                reasons.append("mybatis_include")
                return f" /*<include {ref}>*/ "
            expanded = MYBATIS_INCLUDE.sub(include, body)
            if expanded == body:
                break
            body = expanded
        body = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", body, flags=re.S)
        events = [(t.start(), "mybatis_" + t.group(2).lower()) for t in MYBATIS_TAG.finditer(body) if not t.group(1)]
        events += [(d.start(), "mybatis_dollar") for d in re.finditer(r"\$\{", body)]
        reasons += [r for _, r in sorted(events)]
        body = MYBATIS_TAG.sub(lambda t: f" /*<{t.group(1)}{t.group(2).lower()}>*/ ", body)
        binds = []

        def bind(bm):
            binds.append(bm.group(1))
            return "?"
        text = html.unescape(re.sub(r"#\{\s*([\w.]+)[^}]*\}", bind, body)).strip()
        locator = f"{namespace}#{_attr(m.group(2), 'id')}"
        origin = {"kind": "app_code", "path": rel, "sha256": digest, "locator": locator,
                  "lines": [xml.count("\n", 0, m.start()) + 1, xml.count("\n", 0, m.end()) + 1]}
        out.append(_statement(origin, text, key=_occurrence(seen, locator), reasons=reasons, binds=binds))
    return out


# ------------------------------------------------------------------------------------------------- Java

_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "0": "\0", "s": " ", '"': '"', "'": "'", "\\": "\\"}


def _text_block(raw: str) -> str:
    lines = raw.split("\n")
    if lines and not lines[0].strip():
        lines = lines[1:]
    significant = [l for l in lines if l.strip()] + ([lines[-1]] if lines and not lines[-1].strip() else [])
    indent = min((len(l) - len(l.lstrip(" \t")) for l in significant), default=0)
    text = "\n".join(l[indent:].rstrip() for l in lines)
    return re.sub(r"\\(.)", lambda e: _ESCAPES.get(e.group(1), e.group(1)), text)


def _java_tokens(src: str) -> list[tuple[str, str, int]]:
    """(kind, value, line) with comments dropped; kinds: str, id, sym, lit."""
    tokens, i, line, n = [], 0, 1, len(src)
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
        elif c.isspace():
            i += 1
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            line += src.count("\n", i, j)
            i = j
        elif src.startswith('"""', i):
            j = i + 3
            while j < n and not (src.startswith('"""', j) and src[j - 1] != "\\"):
                j += 1
            tokens.append(("str", _text_block(src[i + 3:j]), line))
            line += src.count("\n", i, j + 3)
            i = j + 3
        elif c == '"':
            j, buf = i + 1, []
            while j < n and src[j] not in '"\n':
                if src[j] == "\\" and j + 1 < n:
                    buf.append(_ESCAPES.get(src[j + 1], src[j + 1]))
                    j += 2
                else:
                    buf.append(src[j])
                    j += 1
            tokens.append(("str", "".join(buf), line))
            i = j + 1
        elif c == "'":
            j = i + 1
            while j < n and src[j] not in "'\n":
                j += 2 if src[j] == "\\" else 1
            tokens.append(("lit", "", line))
            i = j + 1
        elif c.isalpha() or c in "_$":
            j = i
            while j < n and (src[j].isalnum() or src[j] in "_$"):
                j += 1
            tokens.append(("id", src[i:j], line))
            i = j
        elif c.isdigit():
            j = i
            while j < n and (src[j].isalnum() or src[j] in "._"):
                j += 1
            tokens.append(("lit", src[i:j], line))
            i = j
        else:
            tokens.append(("sym", c, line))
            i += 1
    return tokens


def _expression(tokens, i):
    """Operands of a `+` chain from tokens[i] to the first top-level , ) or ; -> (operands, index of the stop)."""
    operands, current, depth = [], [], 0
    while i < len(tokens):
        kind, value, _ = tokens[i]
        if kind == "sym" and depth == 0 and value in ",);":
            break
        if kind == "sym" and value in "([{":
            depth += 1
        elif kind == "sym" and value in ")]}":
            depth -= 1
        if kind == "sym" and value == "+" and depth == 0:
            operands.append(current)
            current = []
        else:
            current.append(tokens[i])
        i += 1
    operands.append(current)
    return [o for o in operands if o], i


def _java_constants(tokens) -> dict[str, list]:
    found: dict[str, list] = {}
    for i in range(len(tokens) - 3):
        if tokens[i][:2] == ("id", "String") and tokens[i + 1][0] == "id" and tokens[i + 2][:2] == ("sym", "="):
            operands, _ = _expression(tokens, i + 3)
            found.setdefault(tokens[i + 1][1], []).append(operands)
    return found


def _resolve(operands, constants, reasons, stack=()):
    parts = []
    for op in operands:
        if len(op) == 1 and op[0][0] == "str":
            parts.append(op[0][1])
            continue
        ids = [t[1] for t in op if t[0] == "id"]
        name = ids[-1] if ids and all(t[0] == "id" or t[1] == "." for t in op) else None
        defs = constants.get(name) if name else None
        if defs and len(defs) == 1 and name not in stack:
            # inline the constant, carrying its own dynamic parts, so `String sql = "SELECT ..." + x` stays visible
            parts.append(_resolve(defs[0], constants, reasons, stack + (name,)))
            continue
        reasons.append("java_concatenation")
        parts.append("${" + (name or "expression") + "}")
    return "".join(parts)


def _from_java(path: Path, rel: str, raw: bytes) -> list[tuple[dict, str]]:
    tokens = _java_tokens(raw.decode("utf-8-sig"))
    constants = _java_constants(tokens)
    package = ""
    for i, (kind, value, _) in enumerate(tokens):
        if (kind, value) == ("id", "package"):
            end = next(j for j in range(i + 1, len(tokens)) if tokens[j][1] == ";")
            package = "".join(t[1] for t in tokens[i + 1:end])
            break
    digest, seen, out = _sha(raw), {}, []
    classes: list[tuple[str, int]] = []  # (name, body depth)
    pending_class, method, method_depth, depth = None, None, None, 0

    def locator():
        owner = ".".join(filter(None, [package, classes[-1][0] if classes else path.stem]))
        return owner + (f"#{method}" if method else "")

    def emit(start, end, text, language, reasons, loc):
        origin = {"kind": "app_code", "path": rel, "sha256": digest, "locator": loc,
                  "lines": [tokens[start][2], tokens[min(end, len(tokens) - 1)][2]]}
        out.append(_statement(origin, text.strip(), key=_occurrence(seen, loc, _collapse(mask(text))),
                              language=language, reasons=reasons))

    i = 0
    while i < len(tokens):
        kind, value, _ = tokens[i]
        prev = tokens[i - 1] if i else ("", "", 0)
        if kind == "id" and value in ("class", "interface", "enum", "record") and prev[1] not in (".", "@") \
                and i + 1 < len(tokens) and tokens[i + 1][0] == "id":
            pending_class = tokens[i + 1][1]
        elif (kind, value) == ("sym", "{"):
            depth += 1
            if pending_class:
                classes.append((pending_class, depth))
                pending_class = None
            elif classes and depth == classes[-1][1] + 1 and method is None:
                method = _method_before(tokens, i)
                method_depth = depth if method else None
        elif (kind, value) == ("sym", "}"):
            if method_depth is not None and depth == method_depth:
                method, method_depth = None, None
            while classes and classes[-1][1] == depth:
                classes.pop()
            depth -= 1
        elif (kind, value) == ("sym", "@") and i + 2 < len(tokens) and tokens[i + 1][1] == "Query" and tokens[i + 2][1] == "(":
            text, native, reasons, end = _query_annotation(tokens, i + 3, constants)
            name = _next_method_name(tokens, end + 1)
            loc = ".".join(filter(None, [package, classes[-1][0] if classes else path.stem])) + (f"#{name}" if name else "")
            if text is not None:
                language = "sql" if native else "jpql"
                if (SQL_START if native else JPQL_START).match(text):
                    emit(i, end, text, language, reasons, loc)
            i = end
        elif kind == "id" and value in SQL_METHODS | JPQL_METHODS and prev[1] == "." \
                and i + 1 < len(tokens) and tokens[i + 1][1] == "(":
            operands, end = _expression(tokens, i + 2)
            if operands and any(len(o) == 1 and o[0][0] == "str" for o in operands[:1]) or \
                    (operands and len(operands[0]) >= 1 and operands[0][0][0] == "id"):
                reasons: list[str] = []
                text = _resolve(operands, constants, reasons)
                language = "jpql" if value in JPQL_METHODS else "sql"
                if (JPQL_START if language == "jpql" else SQL_START).match(text):
                    emit(i, end, text, language, reasons, locator())
        i += 1
    return out


def _method_before(tokens, brace):
    """Name of the method whose body starts at tokens[brace], or None (initializer, lambda, control block)."""
    j = brace - 1
    while j >= 0 and (tokens[j][0] == "id" or tokens[j][1] in ".,<>?"):  # throws A, B
        if tokens[j][1] == ")":
            break
        j -= 1
    if j < 0 or tokens[j][1] != ")":
        return None
    depth = 0
    while j >= 0:
        if tokens[j][1] == ")":
            depth += 1
        elif tokens[j][1] == "(":
            depth -= 1
            if depth == 0:
                break
        j -= 1
    name = tokens[j - 1] if j > 0 else None
    return name[1] if name and name[0] == "id" and name[1] not in CONTROL_WORDS else None


def _query_annotation(tokens, i, constants):
    """Parse @Query( ... ) from its first argument -> (text | None, nativeQuery, reasons, index of the closing paren)."""
    text, native, reasons = None, False, []
    while i < len(tokens) and tokens[i][1] != ")":
        if tokens[i][0] == "id" and i + 1 < len(tokens) and tokens[i + 1][1] == "=":
            attr = tokens[i][1]
            operands, i = _expression(tokens, i + 2)
            if attr == "value":
                text = _resolve(operands, constants, reasons)
            elif attr == "nativeQuery":
                native = any(t[1] == "true" for o in operands for t in o)
        else:
            operands, i = _expression(tokens, i)
            text = _resolve(operands, constants, reasons)
        if i < len(tokens) and tokens[i][1] == ",":
            i += 1
    return text, native, reasons, i


def _next_method_name(tokens, i):
    while i < len(tokens):
        if tokens[i][1] == "@":
            i += 2
            if i < len(tokens) and tokens[i][1] == "(":
                depth = 0
                while i < len(tokens):
                    depth += (tokens[i][1] == "(") - (tokens[i][1] == ")")
                    i += 1
                    if depth == 0:
                        break
            continue
        if tokens[i][1] == "(" and tokens[i - 1][0] == "id":
            return tokens[i - 1][1]
        if tokens[i][1] in ";{}":
            return None
        i += 1
    return None


# ------------------------------------------------------------------------------------------------- SQL files

def _from_sql_file(path: Path, rel: str, raw: bytes, dialect: str, kind: str = "sql_file") -> list[tuple[dict, str]]:
    from scalardb_migrate.converter import _split_statements  # needs sqlglot; imported only for SQL files

    text = raw.decode("utf-8-sig")
    digest, seen, out, cursor = _sha(raw), {}, [], 0
    for chunk in _split_statements(text, dialect):
        pos = text.find(chunk, cursor)
        cursor = pos + len(chunk)
        lead = re.match(r"(?:\s+|--[^\n]*(?:\n|$)|/\*.*?\*/)*", chunk, re.S).end()
        body = chunk[lead:]
        origin = {"kind": kind, "path": rel, "sha256": digest, "dialect": dialect,
                  "lines": [text.count("\n", 0, pos + lead) + 1, text.count("\n", 0, pos + len(chunk)) + 1]}
        out.append(_statement(origin, body, key=_occurrence(seen, _collapse(mask(body)))))
    return out


# ------------------------------------------------------------------------------------------------- investigation runs

def _from_db_run(run: Path, project: Path, problems: list, unavailable: list) -> list[tuple[dict, str]]:
    inv = json.loads((run / "inventory.json").read_text(encoding="utf-8"))
    objects_by_evidence: dict[str, list[str]] = {}
    for obj in inv.get("objects", []):
        for eid in obj.get("evidence_ids", []):
            objects_by_evidence.setdefault(eid, []).append(obj["id"])
    run_rel = _rel(project, run)
    if inv.get("mode") == "live":
        for obj in inv.get("objects", []):
            if obj.get("kind") in DEFINITION_KINDS:
                unavailable.append({"object_id": obj["id"], "kind": obj["kind"], "run": run_rel,
                                    "reason": "a live run holds no definitions; supply the source to migrate it"})
        return []
    out, stale, seen = [], set(), {}
    for ev in inv.get("evidence", []):
        if ev.get("kind") != "file":
            continue
        path = _abs(project, ev["path"])
        if ev["path"] in stale:
            continue
        if not path.is_file():
            stale.add(ev["path"])
            problems.append({"code": "missing_source", "run": run_rel, "path": ev["path"]})
            continue
        raw = path.read_bytes()
        if _sha(raw) != ev.get("sha256"):
            stale.add(ev["path"])
            problems.append({"code": "stale_evidence", "run": run_rel, "path": ev["path"],
                             "detail": "the file changed after the investigation; re-run it or pass the file with --sql-file"})
            continue
        first, last = ev["lines"]
        text = "\n".join(raw.decode("utf-8-sig").splitlines()[first - 1:last]).strip().rstrip(";").strip()
        if not text:
            continue
        origin = {"kind": "db_design_run", "path": ev["path"], "sha256": ev["sha256"], "lines": [first, last],
                  "run": run_rel, "evidence_id": ev["id"], "object_ids": objects_by_evidence.get(ev["id"], [])}
        out.append(_statement(origin, text, key=_occurrence(seen, ev["path"], _collapse(mask(text)))))
    return out


# ------------------------------------------------------------------------------------------------- assembly

def _rel(project: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _abs(project: Path, path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else project / p


def _walk(root: Path, exclude):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        if any(fnmatch.fnmatch(path.relative_to(root).as_posix(), g) for g in exclude):
            continue
        yield path


def _extract_file(path: Path, rel: str, dialect: str) -> list[tuple[dict, str]]:
    raw = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".java":
        return _from_java(path, rel, raw)
    if suffix == ".xml" and b"<mapper" in raw:
        return _from_mapper(path, rel, raw)
    if suffix == ".sql":
        return _from_sql_file(path, rel, raw, dialect)
    return []


def build(source: str, app_roots=(), sql_files=(), db_runs=(), project_dir=None, previous=None, exclude=()) -> dict:
    if source not in DIALECTS:
        raise ValueError(f"source must be one of {', '.join(DIALECTS)}")
    project = Path(project_dir) if project_dir else Path.cwd()
    found, problems, unavailable, sources = [], [], [], []
    for root in map(Path, app_roots):
        sources.append({"kind": "app_root", "path": _rel(project, root)})
        for path in _walk(root, exclude):
            try:
                found += _extract_file(path, _rel(project, path), source)
            except (UnicodeDecodeError, AttributeError, StopIteration) as e:
                problems.append({"code": "unreadable", "path": _rel(project, path), "detail": type(e).__name__})
    for f in map(Path, sql_files):
        sources.append({"kind": "sql_file", "path": _rel(project, f)})
        found += _from_sql_file(f, _rel(project, f), f.read_bytes(), source)
    for run in map(Path, db_runs):
        sources.append({"kind": "db_run", "path": _rel(project, run)})
        found += _from_db_run(run, project, problems, unavailable)

    statements = [s for s, _ in sorted(found, key=lambda st: (st[0]["origin"]["path"], st[0]["origin"]["lines"][0],
                                                               st[0]["origin"].get("locator", "")))]
    # IDs are allocated max + 1 over the previous inventory, so a statement keeps its ID across runs
    kept = {s["fingerprint"]: s["id"] for s in (previous or {}).get("statements", [])}
    next_number = max((int(i.split("-")[1]) for i in kept.values()), default=0) + 1
    used = set()
    for s in statements:
        if kept.get(s["fingerprint"]) and kept[s["fingerprint"]] not in used:
            s["id"] = kept[s["fingerprint"]]
        else:
            s["id"] = f"SQM-{next_number:03d}"
            next_number += 1
        used.add(s["id"])

    def count(key):
        out = {}
        for s in statements:
            out[key(s)] = out.get(key(s), 0) + 1
        return out
    return {
        "schema_version": SCHEMA_VERSION,
        "source_dialect": source,
        "sources": sources,
        "statements": statements,
        "unavailable": unavailable,
        "problems": problems,
        "summary": {"statements": len(statements), "by_origin": count(lambda s: s["origin"]["kind"]),
                    "by_category": count(lambda s: s["category"]), "dynamic": sum(s["dynamic"] for s in statements),
                    "jpql": sum(s["language"] == "jpql" for s in statements), "unavailable": len(unavailable),
                    "problems": len(problems)},
    }


def statement_text(statement: dict, project_dir=None) -> str:
    """The full text of an inventoried statement, re-extracted from its source; StaleEvidence when it changed."""
    project = Path(project_dir) if project_dir else Path.cwd()
    origin = statement["origin"]
    path = _abs(project, origin["path"])
    if not path.is_file():
        raise StaleEvidence(f"{origin['path']} no longer exists")
    raw = path.read_bytes()
    if origin["kind"] == "db_design_run":
        first, last = origin["lines"]
        candidates = [({"fingerprint": statement["fingerprint"]},
                       "\n".join(raw.decode("utf-8-sig").splitlines()[first - 1:last]).strip().rstrip(";").strip())]
    elif origin["kind"] == "sql_file":
        candidates = _from_sql_file(path, origin["path"], raw, origin["dialect"])
    else:
        candidates = _extract_file(path, origin["path"], origin.get("dialect", "oracle"))
    for candidate, text in candidates:
        if candidate["fingerprint"] == statement["fingerprint"]:
            if _sha(text) != statement["text_sha256"]:
                raise StaleEvidence(f"{statement['id']}: {origin['path']} changed since the inventory")
            return text
    raise StaleEvidence(f"{statement['id']}: no longer found in {origin['path']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Inventory the SQL statements a ScalarDB migration has to decide.")
    ap.add_argument("--source", required=True, choices=DIALECTS, help="source dialect")
    ap.add_argument("--app-root", action="append", default=[], help="application source root (repeatable)")
    ap.add_argument("--sql-file", action="append", default=[], help="SQL script (repeatable)")
    ap.add_argument("--db-run", action="append", default=[], help="investigate-db-design / -live run directory (repeatable)")
    ap.add_argument("--exclude", action="append", default=[], help="glob relative to an app root (repeatable)")
    ap.add_argument("--previous", help="earlier sql-inventory.json whose IDs are kept")
    ap.add_argument("--project-dir", default=".", help="directory evidence paths are relative to")
    ap.add_argument("--out", required=True, help="where to write sql-inventory.json")
    args = ap.parse_args(argv)
    if not (args.app_root or args.sql_file or args.db_run):
        print("inventory: give at least one --app-root, --sql-file or --db-run", file=sys.stderr)
        return 1
    try:
        previous = json.loads(Path(args.previous).read_text(encoding="utf-8")) if args.previous else None
        result = build(args.source, args.app_root, args.sql_file, args.db_run, args.project_dir, previous, args.exclude)
    except (OSError, ValueError, KeyError) as e:
        print(f"inventory failed: {e}", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    s = result["summary"]
    print(f"{s['statements']} statements ({s['dynamic']} dynamic, {s['jpql']} JPQL), "
          f"{s['unavailable']} unavailable, {s['problems']} problems -> {out}")
    return 2 if result["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
