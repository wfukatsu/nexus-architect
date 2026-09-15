"""Bounded DDL reader. Never executes input; unsupported constructs retain evidence."""
import hashlib
import json
import re
from pathlib import Path


def object_id(schema, name, kind, catalog=None):
    return json.dumps([catalog, schema, kind, name], ensure_ascii=False, separators=(",", ":"))


def statements(text, dialect):
    """Scan strings/comments before separators, preserving source line ranges."""
    i, line, start = 0, 1, 1
    buf, delimiter, oracle_block = [], ";", False
    while i < len(text):
        if i == 0 or text[i - 1] == "\n":
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            current = text[i:end].strip()
            if dialect == "mysql" and current.upper().startswith("DELIMITER "):
                delimiter = current.split(None, 1)[1]
                i = end
                continue
            if dialect == "oracle" and current == "/":
                if "".join(buf).strip():
                    yield "".join(buf), start, line, False
                buf = []
                oracle_block = False
                i = end
                continue
        c = text[i]
        if not buf and c.isspace():
            line += c == "\n"
            i += 1
            continue
        if not buf:
            start = line
        if text.startswith("--", i) or (dialect == "mysql" and c == "#"):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            buf.append(" ")
            continue
        if text.startswith("/*", i):
            # Nested block comments are legal in PostgreSQL.
            j, depth = i + 2, 1
            while j < len(text) and depth:
                if text.startswith("/*", j):
                    depth += 1
                    j += 2
                elif text.startswith("*/", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            chunk = text[i:j]
            line += chunk.count("\n")
            # Executable MySQL comments must not be silently discarded.
            buf.append(" UNSUPPORTED_EXECUTABLE_COMMENT " if chunk.startswith("/*!") else " ")
            if depth:
                yield "".join(buf), start, line, True
                return
            i = j
            continue
        dollar = re.match(r"\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$", text[i:]) if dialect == "postgresql" else None
        qquote = re.match(r"[qQ]'(.)", text[i:]) if dialect == "oracle" else None
        if c in "'\"`" or dollar or qquote:
            if dollar or qquote:
                opening = dollar.group() if dollar else qquote.group()
                closing = opening if dollar else {"[": "]", "(": ")", "{": "}", "<": ">"}.get(qquote[1], qquote[1]) + "'"
                j = text.find(closing, i + len(opening))
                j = len(text) if j < 0 else j + len(closing)
                closed = text[i:j].endswith(closing) and j > i + len(opening)
            else:
                j, closed = i + 1, False
                while j < len(text):
                    if text[j] == c:
                        if j + 1 < len(text) and text[j + 1] == c:
                            j += 2
                            continue
                        j += 1
                        closed = True
                        break
                    if text[j] == "\\" and (dialect == "mysql" or (dialect == "postgresql" and i > 0 and text[i - 1] in "eE")):
                        j += 2
                    else:
                        j += 1
            chunk = text[i:j]
            line += chunk.count("\n")
            buf.append(chunk if c in '\"`' and not dollar and not qquote else "'REDACTED'")
            i = j
            if not closed:
                yield "".join(buf), start, line, True
                return
            continue
        if dialect == "oracle" and not oracle_block and len(buf) < 120:
            # DBMS_METADATA emits EDITIONABLE / NONEDITIONABLE between REPLACE and the kind.
            oracle_block = bool(re.match(r"\s*(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:(?:NON)?EDITIONABLE\s+)?(?:PROCEDURE|FUNCTION|PACKAGE|TRIGGER|TYPE\s+BODY)|DECLARE|BEGIN)\b", "".join(buf), re.I))
        if text.startswith(delimiter, i) and not oracle_block:
            yield "".join(buf), start, line, False
            buf = []
            i += len(delimiter)
            continue
        buf.append(c)
        line += c == "\n"
        i += 1
    if "".join(buf).strip():
        yield "".join(buf), start, line, False


TOKEN = re.compile(r'"(?:""|[^"])*"|`(?:``|[^`])*`|\'(?:\'\'|[^\'])*\'|[\w$#]+|[^\s]', re.UNICODE)
OBJECT_KINDS = {"table", "index", "view", "function", "procedure", "trigger", "sequence", "package"}
# Ordered by how much a statement's outcome limits coverage; a statement keeps its worst.
SEVERITY = ("ok", "empty", "not_collected", "unsupported", "error")
COLUMN_ATTRIBUTES = {"NOT", "NULL", "DEFAULT", "PRIMARY", "REFERENCES", "UNIQUE", "CHECK", "CONSTRAINT", "GENERATED", "COLLATE", "AUTO_INCREMENT", "COMMENT", "ON"}
CONSTRAINT_HEADS = {"CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK"}
REFERENTIAL_ACTIONS = {("CASCADE",): "cascade", ("RESTRICT",): "restrict", ("SET", "NULL"): "set null", ("SET", "DEFAULT"): "set default", ("NO", "ACTION"): "no action"}
SET_CONFIG = re.compile(r"\s*SELECT\s+(?:pg_catalog\s*\.\s*)?set_config\s*\([^;]*\)\s*$", re.I)
NAME_RESOLUTION = re.compile(r"search_path|current_schema|\bSET\s+SCHEMA\b", re.I)
CLEARED_SEARCH_PATH = re.compile(r"set_config\s*\(\s*'search_path'\s*,\s*''\s*,", re.I)


def mark(status, outcome, reason=None):
    """Record an outcome without letting a milder one hide a worse one or its reason."""
    current, new = SEVERITY.index(status["status"]), SEVERITY.index(outcome)
    if new > current:
        status["status"] = outcome
        status.pop("reason", None)
    if new >= current and reason and "reason" not in status:
        status["reason"] = reason


def withhold(status, what):
    """Deliberately omitted content (policy), distinct from a coverage gap (status)."""
    if what not in status.setdefault("withheld", []):
        status["withheld"].append(what)


def native_type(lexemes):
    out = ""
    for lexeme in lexemes:
        if out and lexeme not in {"(", ")", ","} and out[-1] not in "(,":
            out += " "
        out += lexeme
    return out


class Reader:
    def __init__(self, lexemes, fold):
        self.t, self.i, self.fold = lexemes, 0, fold

    def peek(self, offset=0):
        i = self.i + offset
        return self.t[i].upper() if i < len(self.t) else ""

    def take(self, value):
        if self.peek() == value:
            self.i += 1
            return True
        return False

    def need(self, value):
        if not self.take(value):
            raise ValueError("unsupported syntax")

    def done(self):
        return self.i >= len(self.t)

    def ident(self):
        if self.i >= len(self.t):
            raise ValueError("missing identifier")
        s = self.t[self.i]
        self.i += 1
        if s[0] in '\"`':
            return s[1:-1].replace(s[0] * 2, s[0])
        if not re.fullmatch(r"[\w$#]+", s):
            raise ValueError("invalid identifier")
        return s.upper() if self.fold == "upper" else s.lower() if self.fold == "lower" else s

    def qualified(self, schema):
        name = self.ident()
        if self.take("."):
            return name, self.ident()
        return schema, name

    def group(self):
        self.need("(")
        start, depth = self.i, 1
        while self.i < len(self.t):
            lexeme = self.t[self.i]
            self.i += 1
            depth += (lexeme == "(") - (lexeme == ")")
            if depth == 0:
                return self.t[start:self.i - 1]
        raise ValueError("unclosed group")

    def names(self):
        names = []
        for group in groups(self.group()):
            item = Reader(group, self.fold)
            names.append(item.ident())
            if item.i != len(item.t):
                raise ValueError("expression or ordering requires source review")
        return names


def groups(lexemes):
    part, depth = [], 0
    for lexeme in lexemes:
        if lexeme == "," and depth == 0:
            yield part
            part = []
        else:
            part.append(lexeme)
            depth += (lexeme == "(") - (lexeme == ")")
    if part:
        yield part


def constraint(r, schema, column=None):
    name = r.ident() if r.take("CONSTRAINT") else None
    if r.take("PRIMARY"):
        r.need("KEY")
        kind = "primary_key"
    elif r.take("FOREIGN"):
        r.need("KEY")
        kind = "foreign_key"
    elif r.take("UNIQUE"):
        kind = "unique"
        # MySQL spells a table constraint UNIQUE [KEY|INDEX] [index_name] (columns).
        r.take("KEY") or r.take("INDEX")
        if not column and r.peek() not in {"(", ""}:
            name = name or r.ident()
    elif r.take("CHECK"):
        r.group()
        return {"kind": "check", "name": name, "columns": [column] if column else [], "expression": "[definition withheld]"}
    elif r.peek() == "REFERENCES" and column:
        kind = "foreign_key"
    else:
        raise ValueError("unsupported constraint")
    out = {"kind": kind, "name": name, "columns": [column] if column else r.names()}
    if kind == "foreign_key":
        r.need("REFERENCES")
        owner, table = r.qualified(schema)
        cols = r.names() if r.peek() == "(" else []
        out["references"] = {"schema": owner, "name": table, "columns": cols}
        while r.peek() == "ON" and r.peek(1) in {"DELETE", "UPDATE"}:
            words = (r.peek(2), r.peek(3))
            action = REFERENTIAL_ACTIONS.get(words) or REFERENTIAL_ACTIONS.get(words[:1])
            if action is None:
                break  # left in place: the caller reports the unread clause as unsupported
            out["on_" + r.peek(1).lower()] = action
            r.i += 2 + len(action.split())
    return out


def parse_design(paths, adapter, schema):
    result = {"objects": [], "evidence": [], "collections": [], "findings": []}
    pending, seen = [], set()
    fold = adapter["fold"]
    # Where index names are table-local (MySQL), IDs are table-qualified like the live adapter's.
    table_scoped_indexes = adapter.get("index_scope") == "table"
    inline_indexes = adapter.get("inline_indexes", False)

    def new_object(owner, name, kind, eid):
        return {"id": object_id(owner, name, kind), "catalog": None, "schema": owner, "name": name, "kind": kind, "evidence_ids": [eid], "columns": [], "constraints": [], "extensions": {}}

    def index_object(owner, table, name, columns, unique, eid, **extra):
        obj = new_object(owner, table + "." + name if table_scoped_indexes else name, "index", eid)
        obj["extensions"] = dict({"table_schema": owner, "table": table, "columns": columns, "unique": unique}, **extra)
        return obj

    def add(obj, status):
        if obj["id"] in seen:
            mark(status, "error")
            result["findings"].append({"code": "duplicate_definition", "evidence_ids": obj["evidence_ids"][:1], "object_id": obj["id"]})
            return False
        result["objects"].append(obj)
        seen.add(obj["id"])
        status["row_count"] += 1
        return True

    def session_setting(status, sql, source):
        if NAME_RESOLUTION.search(source) and not CLEARED_SEARCH_PATH.search(source):
            mark(status, "not_collected", "session changes name resolution; confirm unqualified names belong to the requested schema")
        else:
            mark(status, "empty", "session setting; no schema structure")

    def inline_index(col, owner, table, eid, status):
        word = col.t[col.i].upper()
        col.i += 1
        if word in {"FULLTEXT", "SPATIAL"}:
            col.take("KEY") or col.take("INDEX")
        name = col.ident() if col.peek() != "(" else None
        try:
            columns = col.names()
        except ValueError:
            mark(status, "unsupported", "index expression or prefix length requires source review")
            return None
        if not col.done():
            mark(status, "unsupported")
        extra = {"type": word.lower()} if word in {"FULLTEXT", "SPATIAL"} else {}
        return index_object(owner, table, name or columns[0], columns, False, eid, **extra)

    def column(col, owner, obj, eid, status):
        name = col.ident()
        typ, depth = [], 0
        while not col.done():
            if depth == 0 and col.peek() in COLUMN_ATTRIBUTES:
                break
            lexeme = col.t[col.i]
            typ.append(lexeme)
            depth += (lexeme == "(") - (lexeme == ")")
            col.i += 1
        if not typ:
            raise ValueError("column type missing")
        # SQL columns are nullable unless declared otherwise; that is only a fact once every
        # attribute has been read, so a column whose attributes stop being understood is unknown.
        nullable, explicit = True, False
        while not col.done():
            if col.take("NOT"):
                col.need("NULL")
                nullable, explicit = False, True
            elif col.take("NULL"):
                nullable, explicit = True, True
            elif col.take("DEFAULT"):
                withhold(status, "default_expression")
                depth = 0
                while not col.done() and not (depth == 0 and col.peek() in COLUMN_ATTRIBUTES - {"DEFAULT"}):
                    depth += (col.t[col.i] == "(") - (col.t[col.i] == ")")
                    col.i += 1
            elif col.peek() in {"PRIMARY", "UNIQUE", "REFERENCES", "CHECK", "CONSTRAINT"}:
                c = constraint(col, owner, name)
                obj["constraints"].append(c)
                if c["kind"] == "check":
                    withhold(status, "check_expression")
                if c["kind"] == "primary_key":
                    nullable, explicit = False, True
            else:
                mark(status, "unsupported")
                if not explicit:
                    nullable = None
                break
        return {"name": name, "type": native_type(typ), "ordinal": len(obj["columns"]) + 1, "nullable": nullable, "evidence_ids": [eid]}

    for path in paths:
        raw = Path(path).read_bytes()
        text = raw.decode("utf-8-sig")
        lines = text.splitlines()
        digest = hashlib.sha256(raw).hexdigest()
        for sql, first, last, broken in statements(text, adapter["id"]):
            if not sql.strip():
                continue
            eid = "E" + str(len(result["evidence"]) + 1)
            result["evidence"].append({"id": eid, "kind": "file", "path": str(path), "sha256": digest, "lines": [first, last]})
            status = {"id": eid, "status": "ok", "row_count": 0, "truncated": False, "evidence_ids": [eid]}
            result["collections"].append(status)
            if broken:
                mark(status, "error")
                continue
            # Raw source is consulted only for a yes/no pattern; its literals are never stored.
            source = "\n".join(lines[first - 1:last])
            r = Reader(TOKEN.findall(sql), fold)
            try:
                if r.take("COMMENT"):
                    # Preserve provenance, not potentially sensitive comment contents.
                    mark(status, "empty")
                    withhold(status, "comment_text")
                    continue
                if r.peek() == "SET" or SET_CONFIG.match(sql):
                    session_setting(status, sql, source)
                    continue
                if r.take("ALTER"):
                    if r.take("SESSION"):
                        session_setting(status, sql, source)
                        continue
                    target = r.peek().lower()
                    if target not in OBJECT_KINDS:
                        raise ValueError("unsupported object")
                    r.i += 1
                    r.take("ONLY")  # PostgreSQL inheritance qualifier; pg_dump always emits it
                    owner, name = r.qualified(schema)
                    if r.take("OWNER"):
                        r.need("TO")
                        r.ident()
                        if not r.done():
                            raise ValueError("unsupported syntax")
                        mark(status, "empty", "ownership change; no schema structure")
                        continue
                    if target != "table":
                        raise ValueError("unsupported alter")
                    if r.take("ALTER"):
                        r.take("COLUMN")
                        r.ident()
                        r.need("SET")
                        r.need("DEFAULT")
                        mark(status, "empty")
                        withhold(status, "default_expression")
                        continue
                    r.need("ADD")
                    c = constraint(r, owner)
                    if c["kind"] == "check":
                        withhold(status, "check_expression")
                    if not r.done():
                        mark(status, "unsupported", "constraint options need review")
                    pending.append((owner, name, c, status))
                    continue
                r.need("CREATE")
                if r.take("OR"):
                    r.need("REPLACE")
                r.take("EDITIONABLE") or r.take("NONEDITIONABLE")
                unique = r.take("UNIQUE")
                kind = r.peek().lower()
                if kind not in OBJECT_KINDS:
                    raise ValueError("unsupported object")
                r.i += 1
                if r.take("IF"):
                    r.need("NOT")
                    r.need("EXISTS")
                owner, name = r.qualified(schema)
                if owner != schema:
                    if owner.casefold() == schema.casefold():
                        # Identifier folding made the owner differ from the requested spelling:
                        # almost certainly the same schema, so say so instead of dropping it quietly.
                        mark(status, "not_collected", "owner differs from the requested schema only by letter case; pass the exact folded spelling")
                        result["findings"].append({"code": "schema_case_mismatch", "evidence_ids": [eid]})
                    else:
                        mark(status, "empty", "outside requested schema")
                    continue
                if kind == "table":
                    obj, indexes = new_object(owner, name, kind, eid), []
                    for group in groups(r.group()):
                        col = Reader(group, fold)
                        head = col.peek()
                        if inline_indexes and (head in {"KEY", "INDEX"} or (head in {"FULLTEXT", "SPATIAL"} and col.peek(1) in {"KEY", "INDEX"})):
                            index = inline_index(col, owner, name, eid, status)
                            if index:
                                indexes.append(index)
                            continue
                        if head in CONSTRAINT_HEADS:
                            c = constraint(col, owner)
                            obj["constraints"].append(c)
                            if c["kind"] == "check":
                                withhold(status, "check_expression")
                            if inline_indexes and c["kind"] == "unique":
                                indexes.append(index_object(owner, name, c["name"] or c["columns"][0], c["columns"], True, eid))
                            if not col.done():
                                mark(status, "unsupported")
                            continue
                        obj["columns"].append(column(col, owner, obj, eid, status))
                    if not r.done():
                        mark(status, "unsupported")
                    if add(obj, status):
                        for index in indexes:
                            add(index, status)
                elif kind == "index":
                    r.need("ON")
                    r.take("ONLY")
                    table_schema, table = r.qualified(owner)
                    extra = {"method": r.ident().lower()} if r.take("USING") else {}
                    obj = index_object(owner, table, name, r.names(), unique, eid, **extra)
                    obj["extensions"]["table_schema"] = table_schema
                    if not r.done():
                        mark(status, "unsupported")
                    add(obj, status)
                else:
                    withhold(status, "definition")
                    add(new_object(owner, name, kind, eid), status)
            except (ValueError, IndexError):
                mark(status, "unsupported")
    for owner, name, c, status in pending:
        obj = next((o for o in result["objects"] if o["schema"] == owner and o["name"] == name and o["kind"] == "table"), None)
        if obj:
            obj["constraints"].append(c)
            obj["evidence_ids"].extend(e for e in status["evidence_ids"] if e not in obj["evidence_ids"])
            status["row_count"] = 1
        else:
            mark(status, "unsupported", "ALTER target unresolved or out of scope")
    for obj in result["objects"]:
        required = {name for c in obj["constraints"] if c["kind"] == "primary_key" for name in c["columns"]}
        for col in obj["columns"]:
            if col["name"] in required:
                col["nullable"] = False
        for c in obj["constraints"]:
            ref = c.get("references")
            if ref and object_id(ref["schema"], ref["name"], "table") not in seen:
                result["findings"].append({"code": "unresolved_reference", "object_id": obj["id"], "evidence_ids": obj["evidence_ids"]})
    return result
