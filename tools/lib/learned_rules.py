#!/usr/bin/env python3
"""Learned rules: what the reviews keep finding, kept as rules the design skills read.

A finding the six review perspectives raise on project A is raised again on project B unless
something carries it forward. This store does (rules/learned-rules.md): `review-synthesizer`
proposes a rule from a recurring finding, a person accepts or rejects it, and the design skills
read the accepted rules for their phase before they decide anything.

Store: `work/learned-rules.json` in the project, or the path `options.learned_rules_path` of
`work/pipeline-progress.json` names — a file shared across projects, so a consultancy running
the toolkit on many projects accumulates each lesson once. Every write is additive; a rule is
never deleted, only `rejected`.

    python3 tools/lib/learned_rules.py <project_dir> propose rule="…" scope=design-api,design-scalardb category=api-contract [anti_pattern="…"] [rationale="…"] [finding=SYN-004] [by=review-synthesizer]
    python3 tools/lib/learned_rules.py <project_dir> decide LR-001 accepted|rejected [by="Dana Architect"] [reason="…"]
    python3 tools/lib/learned_rules.py <project_dir> list [scope=<phase>] [status=accepted|proposed|rejected|all] [format=text|json]
    python3 tools/lib/learned_rules.py <project_dir> render

`propose` deduplicates on the rule text (case- and whitespace-insensitive): a rule already on
file gains an occurrence and the finding as another origin instead of a second id. Each
proposal and decision is an audit event (RULE_PROPOSED / RULE_ACCEPTED / RULE_REJECTED).
`render` writes the Markdown view `work/learned-rules.md`. Exit 0; 1 when a store the options
name cannot be read; 2 on a usage error (unknown id, bad status, missing field).
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import audit_log as AUDIT  # noqa: E402
except Exception:  # pragma: no cover
    AUDIT = None

STORE = os.path.join("work", "learned-rules.json")
VIEW = os.path.join("work", "learned-rules.md")
PROGRESS = os.path.join("work", "pipeline-progress.json")
STATUSES = ("proposed", "accepted", "rejected")
CATEGORIES = ("naming", "api-contract", "data-model", "transaction", "error-handling", "nfr",
              "security", "testing", "operations", "architecture", "process")
DECISION_EVENT = {"accepted": "RULE_ACCEPTED", "rejected": "RULE_REJECTED"}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_name(project_dir):
    try:
        with open(os.path.join(project_dir, PROGRESS), encoding="utf-8") as fh:
            data = json.load(fh)
        name = data.get("project_name") if isinstance(data, dict) else None
        if isinstance(name, str) and name:
            return name
    except (OSError, ValueError):
        pass
    return os.path.basename(os.path.abspath(project_dir))


def store_path(project_dir):
    """The project's store, or the shared one `options.learned_rules_path` names (relative to the
    project when relative)."""
    try:
        with open(os.path.join(project_dir, PROGRESS), encoding="utf-8") as fh:
            options = (json.load(fh) or {}).get("options") or {}
    except (OSError, ValueError, AttributeError):
        options = {}
    shared = options.get("learned_rules_path") if isinstance(options, dict) else None
    if isinstance(shared, str) and shared:
        return shared if os.path.isabs(shared) else os.path.join(project_dir, shared)
    return os.path.join(project_dir, STORE)


def load(path):
    if not os.path.exists(path):
        return {"schema_version": 1, "rules": []}
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise ValueError("%s is not a learned-rules store" % path)
    return data


def save(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower().rstrip("."))


def _next_id(rules):
    numbers = [int(m.group(1)) for r in rules for m in [re.match(r"LR-(\d+)$", r.get("id", ""))] if m]
    return "LR-%03d" % (max(numbers) + 1 if numbers else 1)


def _audit(project_dir, event, rule, by, detail):
    if AUDIT is None:
        return
    try:
        AUDIT.append_event(project_dir, event, phase="review-synthesizer" if event == "RULE_PROPOSED" else None,
                           ref=rule["id"], actor=by, detail=detail)
    except Exception:
        pass


def propose(project_dir, rule, scope, category, anti_pattern=None, rationale=None, finding=None,
            by="review-synthesizer", path=None):
    """Add a proposed rule, or an occurrence of the rule already on file. Returns (rule, created)."""
    if not normalize(rule):
        raise ValueError("rule= is required")
    scope = [s.strip() for s in (scope.split(",") if isinstance(scope, str) else scope) if s.strip()]
    if not scope:
        raise ValueError("scope= must name at least one phase")
    if category not in CATEGORIES:
        raise ValueError("category must be one of %s" % ", ".join(CATEGORIES))
    path = path or store_path(project_dir)
    data = load(path)
    origin = {"finding": finding or None, "project": project_name(project_dir), "at": now_iso()}
    for existing in data["rules"]:
        if normalize(existing.get("rule")) == normalize(rule) and existing.get("status") != "rejected":
            existing["occurrences"] = int(existing.get("occurrences") or 0) + 1
            existing.setdefault("origin", []).append(origin)
            for s in scope:
                if s not in existing.setdefault("scope", []):
                    existing["scope"].append(s)
            save(path, data)
            _audit(project_dir, "RULE_PROPOSED", existing, by,
                   "occurrence %d of %s" % (existing["occurrences"], existing["id"]))
            return existing, False
    record = {
        "id": _next_id(data["rules"]), "status": "proposed", "scope": scope, "category": category,
        "rule": rule.strip(), "anti_pattern": (anti_pattern or "").strip() or None,
        "rationale": (rationale or "").strip() or None, "origin": [origin], "occurrences": 1,
        "proposed_at": origin["at"], "proposed_by": by, "decided_at": None, "decided_by": None,
        "decision_reason": None,
    }
    data["rules"].append(record)
    save(path, data)
    _audit(project_dir, "RULE_PROPOSED", record, by, record["rule"])
    return record, True


def decide(project_dir, rule_id, status, by=None, reason=None, path=None):
    if status not in DECISION_EVENT:
        raise ValueError("status must be accepted or rejected")
    path = path or store_path(project_dir)
    data = load(path)
    record = next((r for r in data["rules"] if r.get("id") == rule_id), None)
    if record is None:
        raise KeyError(rule_id)
    record["status"] = status
    record["decided_at"] = now_iso()
    record["decided_by"] = by or (AUDIT.actor_name(project_dir) if AUDIT else None)
    record["decision_reason"] = (reason or "").strip() or None
    save(path, data)
    _audit(project_dir, DECISION_EVENT[status], record, record["decided_by"], reason or record["rule"])
    return record


def select(data, scope=None, status="accepted"):
    rules = data.get("rules", [])
    if status != "all":
        rules = [r for r in rules if r.get("status") == status]
    if scope:
        rules = [r for r in rules if scope in (r.get("scope") or [])]
    return rules


def render_text(rules):
    if not rules:
        return "no rules"
    out = []
    for r in rules:
        out.append("%s [%s] (%s; %s; x%d) %s" % (r["id"], r["status"], r.get("category"),
                                                  ", ".join(r.get("scope") or []),
                                                  int(r.get("occurrences") or 0), r["rule"]))
        if r.get("anti_pattern"):
            out.append("    avoid: %s" % r["anti_pattern"])
        if r.get("rationale"):
            out.append("    because: %s" % r["rationale"])
    return "\n".join(out)


def render_markdown(project_dir, path=None):
    path = path or store_path(project_dir)
    data = load(path)
    lines = ["---", 'title: "Learned Rules"', "schema_version: 1", "skill: review-synthesizer",
             'generated_at: "%s"' % now_iso(), "input_files:", "  - %s" % os.path.relpath(path, project_dir),
             "---", "", "# Learned Rules", "",
             "Rules proposed from recurring review findings and decided by a person "
             "(rules/learned-rules.md). The design skills read the accepted ones for their phase.", ""]
    for status in STATUSES:
        rules = select(data, status=status)
        lines.append("## %s (%d)" % (status.capitalize(), len(rules)))
        lines.append("")
        if not rules:
            lines.append("_none_")
            lines.append("")
            continue
        lines.append("| ID | Category | Scope | Occurrences | Rule | Decided by |")
        lines.append("|----|----------|-------|-------------|------|------------|")
        for r in rules:
            lines.append("| %s | %s | %s | %d | %s | %s |" % (
                r["id"], r.get("category") or "", ", ".join(r.get("scope") or []),
                int(r.get("occurrences") or 0), (r["rule"] or "").replace("|", "\\|"),
                r.get("decided_by") or ""))
        lines.append("")
    view = os.path.join(project_dir, VIEW)
    os.makedirs(os.path.dirname(view), exist_ok=True)
    with open(view, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return view


def _kv(args, allowed):
    out = {}
    for arg in args:
        key, sep, value = arg.partition("=")
        if not sep or key not in allowed:
            raise ValueError("expected one of %s as key=value, got %r" % (", ".join(allowed), arg))
        out[key] = value
    return out


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    project, verb = argv[0], argv[1]
    if not os.path.isdir(project):
        sys.stderr.write("learned_rules: not a directory: %s\n" % project)
        return 2
    try:
        if verb == "propose":
            kv = _kv(argv[2:], ("rule", "scope", "category", "anti_pattern", "rationale", "finding", "by"))
            for required in ("rule", "scope", "category"):
                if required not in kv:
                    raise ValueError("%s= is required" % required)
            record, created = propose(project, kv["rule"], kv["scope"], kv["category"],
                                      kv.get("anti_pattern"), kv.get("rationale"), kv.get("finding"),
                                      kv.get("by") or "review-synthesizer")
            sys.stdout.write(json.dumps({"id": record["id"], "created": created,
                                         "occurrences": record["occurrences"], "status": record["status"]}) + "\n")
            return 0
        if verb == "decide":
            if len(argv) < 4:
                raise ValueError("decide needs <LR-id> accepted|rejected")
            kv = _kv(argv[4:], ("by", "reason"))
            record = decide(project, argv[2], argv[3], kv.get("by"), kv.get("reason"))
            sys.stdout.write(json.dumps({"id": record["id"], "status": record["status"],
                                         "decided_by": record["decided_by"]}) + "\n")
            return 0
        if verb == "list":
            kv = _kv(argv[2:], ("scope", "status", "format"))
            status = kv.get("status", "accepted")
            if status not in STATUSES + ("all",):
                raise ValueError("status must be accepted, proposed, rejected or all")
            rules = select(load(store_path(project)), kv.get("scope"), status)
            if kv.get("format", "text") == "json":
                sys.stdout.write(json.dumps(rules, ensure_ascii=False, indent=2) + "\n")
            else:
                sys.stdout.write(render_text(rules) + "\n")
            return 0
        if verb == "render":
            sys.stdout.write(os.path.relpath(render_markdown(project), project) + "\n")
            return 0
        raise ValueError("verb must be propose, decide, list or render")
    except KeyError as exc:
        sys.stderr.write("learned_rules: no rule %s\n" % exc.args[0])
        return 2
    except ValueError as exc:
        sys.stderr.write("learned_rules: %s\n" % exc)
        return 2
    except OSError as exc:
        sys.stderr.write("learned_rules: %s\n" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
