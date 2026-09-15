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
    buf, delimiter = [], ";"
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
        oracle_block = dialect == "oracle" and re.match(r"\s*(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:PROCEDURE|FUNCTION|PACKAGE|TRIGGER|TYPE\s+BODY)|DECLARE|BEGIN)\b", "".join(buf), re.I)
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


class Reader:
    def __init__(self, tokens, fold):
        self.t, self.i, self.fold = tokens, 0, fold

    def peek(self):
        return self.t[self.i].upper() if self.i < len(self.t) else ""

    def take(self, value):
        if self.peek() == value:
            self.i += 1
            return True
        return False

    def need(self, value):
        if not self.take(value):
            raise ValueError("unsupported syntax")

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
            token = self.t[self.i]
            self.i += 1
            depth += (token == "(") - (token == ")")
            if depth == 0:
                return self.t[start:self.i - 1]
        raise ValueError("unclosed group")

    def names(self):
        return [Reader(g, self.fold).ident() for g in groups(self.group())]


def groups(tokens):
    part, depth = [], 0
    for token in tokens:
        if token == "," and depth == 0:
            yield part
            part = []
        else:
            part.append(token)
            depth += (token == "(") - (token == ")")
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
    return out


def parse_design(paths, adapter, schema):
    result = {"objects": [], "evidence": [], "collections": [], "findings": []}
    pending, seen = [], set()
    fold = adapter["fold"]
    for path in paths:
        raw = Path(path).read_bytes()
        text = raw.decode("utf-8-sig")
        digest = hashlib.sha256(raw).hexdigest()
        for sql, first, last, broken in statements(text, adapter["id"]):
            if not sql.strip():
                continue
            eid = "E" + str(len(result["evidence"]) + 1)
            result["evidence"].append({"id": eid, "kind": "file", "path": str(path), "sha256": digest, "lines": [first, last]})
            status = {"id": eid, "status": "ok", "row_count": 0, "truncated": False, "evidence_ids": [eid]}
            result["collections"].append(status)
            if broken:
                status["status"] = "error"
                continue
            r = Reader(TOKEN.findall(sql), fold)
            try:
                if r.take("COMMENT"):
                    # Preserve provenance, not potentially sensitive comment contents.
                    status["status"] = "not_collected"
                    status["reason"] = "comment text withheld; see source"
                    continue
                if r.take("ALTER"):
                    r.need("TABLE")
                    owner, name = r.qualified(schema)
                    r.need("ADD")
                    c = constraint(r, owner)
                    if r.i != len(r.t):
                        raise ValueError("constraint options need review")
                    pending.append((owner, name, c, status))
                    continue
                r.need("CREATE")
                if r.take("OR"):
                    r.need("REPLACE")
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
                    status.update(status="not_collected", reason="outside requested schema")
                    continue
                obj = {"id": object_id(owner, name, kind), "catalog": None, "schema": owner, "name": name, "kind": kind, "evidence_ids": [eid], "columns": [], "constraints": [], "extensions": {}}
                if obj["id"] in seen:
                    status["status"] = "error"
                    result["findings"].append({"code": "duplicate_definition", "evidence_ids": [eid], "object_id": obj["id"]})
                    continue
                if kind == "table":
                    body = r.group()
                    for ordinal, group in enumerate(groups(body), 1):
                        col = Reader(group, fold)
                        if col.peek() in {"CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK"}:
                            obj["constraints"].append(constraint(col, owner))
                            if col.i < len(col.t):
                                status["status"] = "unsupported"
                            continue
                        column = col.ident()
                        typ, depth = [], 0
                        while col.i < len(col.t):
                            if depth == 0 and col.peek() in {"NOT", "NULL", "DEFAULT", "PRIMARY", "REFERENCES", "UNIQUE", "CHECK", "CONSTRAINT", "GENERATED", "COLLATE", "AUTO_INCREMENT"}:
                                break
                            token = col.t[col.i]
                            typ.append(token)
                            depth += (token == "(") - (token == ")")
                            col.i += 1
                        if not typ:
                            raise ValueError("column type missing")
                        nullable = None
                        while col.i < len(col.t):
                            if col.take("NOT"):
                                col.need("NULL")
                                nullable = False
                            elif col.take("NULL"):
                                nullable = True
                            elif col.take("DEFAULT"):
                                status["status"] = "not_collected"
                                status["reason"] = "default expression withheld"
                                while col.i < len(col.t) and col.peek() not in {"NOT", "NULL", "PRIMARY", "UNIQUE", "REFERENCES", "CHECK", "CONSTRAINT"}:
                                    col.i += 1
                            elif col.peek() in {"PRIMARY", "UNIQUE", "REFERENCES", "CHECK", "CONSTRAINT"}:
                                c = constraint(col, owner, column)
                                obj["constraints"].append(c)
                                if c["kind"] == "primary_key":
                                    nullable = False
                            else:
                                status["status"] = "unsupported"
                                break
                        obj["columns"].append({"name": column, "type": " ".join(typ), "ordinal": len(obj["columns"]) + 1, "nullable": nullable, "evidence_ids": [eid]})
                    if r.i < len(r.t):
                        status["status"] = "unsupported"
                elif kind == "index":
                    r.need("ON")
                    ts, tn = r.qualified(owner)
                    index_cols = r.names()
                    obj["extensions"] = {"table_schema": ts, "table": tn, "columns": index_cols, "unique": unique}
                    if r.i < len(r.t):
                        status["status"] = "unsupported"
                else:
                    status.update(status="not_collected", reason="object inventoried; definition and dependencies require source review")
                result["objects"].append(obj)
                seen.add(obj["id"])
                status["row_count"] = 1
            except (ValueError, IndexError):
                status["status"] = "unsupported"
    for owner, name, c, status in pending:
        obj = next((o for o in result["objects"] if o["schema"] == owner and o["name"] == name and o["kind"] == "table"), None)
        if obj:
            obj["constraints"].append(c)
            obj["evidence_ids"].extend(status["evidence_ids"])
            status["row_count"] = 1
        else:
            status.update(status="unsupported", reason="ALTER target unresolved or out of scope")
    for obj in result["objects"]:
        for c in obj["constraints"]:
            ref = c.get("references")
            if ref and object_id(ref["schema"], ref["name"], "table") not in seen:
                result["findings"].append({"code": "unresolved_reference", "object_id": obj["id"], "evidence_ids": obj["evidence_ids"]})
    return result
