#!/usr/bin/env python3
"""Claims and worktrees for backlog delivery by more than one person at a time.

`reports/backlog/claims.json` records who is working on which Issue, in which worktree and on
which branch, and toward which integration branch. `/architect:deliver-backlog` claims an Issue
before it starts it and skips Issues someone else holds; `/architect:implement-backlog` works in
the Issue's own worktree so two Issues of one Epic never share a checkout; `/architect:merge-issue`
releases the claim after the merge (skills/common/backlog-claims.md).

    python3 tools/lib/backlog_claims.py <project_dir> claim <item> [by=…] [branch=…] [worktree=…] [integration=…] [steal=true]
    python3 tools/lib/backlog_claims.py <project_dir> release <item> [by=…] [reason=…]
    python3 tools/lib/backlog_claims.py <project_dir> list [active=true|false] [format=text|json]
    python3 tools/lib/backlog_claims.py <project_dir> worktree add <item> [root=…] [branch=…] [base=…]
    python3 tools/lib/backlog_claims.py <project_dir> worktree remove <item>

`claim` exits 3 when another person holds the item (the holder is printed) unless `steal=true`,
which records the previous holder in the new claim's `stolen_from`. The default `by` is
`git config user.name`. `worktree add` creates `<root>/<item>` (`root` defaults to
`../<project>-worktrees`) on `branch` (default `feat/<item>`), from `base` (default the current
branch of the project) — a new branch, or the existing one when it already exists — and records
the path and branch on the item's claim. Every claim, release and worktree is an audit event
(ITEM_CLAIMED / ITEM_RELEASED). Exit 0; 1 when the project is not a git repository or git fails;
2 on a usage error; 3 on a contested claim.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import audit_log as AUDIT  # noqa: E402
except Exception:  # pragma: no cover
    AUDIT = None

CLAIMS = os.path.join("reports", "backlog", "claims.json")
ITEM_RE = re.compile(r"^[A-Za-z0-9#][A-Za-z0-9._#-]*$")


class Contested(Exception):
    def __init__(self, holder):
        super().__init__("held by %s" % holder["claimed_by"])
        self.holder = holder


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def claims_path(project_dir):
    return os.path.join(project_dir, CLAIMS)


def load(project_dir):
    path = claims_path(project_dir)
    if not os.path.exists(path):
        return {"schema_version": 1, "claims": []}
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
        raise ValueError("%s is not a claims file" % path)
    return data


def save(project_dir, data):
    path = claims_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def actor(project_dir, by=None):
    if by:
        return by
    name = AUDIT.actor_name(project_dir) if AUDIT else None
    return name or "unknown"


def active(data, item):
    return next((c for c in data["claims"] if c["item"] == item and not c.get("released_at")), None)


def _audit(project_dir, event, item, who, detail):
    if AUDIT is None:
        return
    try:
        AUDIT.append_event(project_dir, event, phase=item, actor=who, detail=detail)
    except Exception:
        pass


def claim(project_dir, item, by=None, branch=None, worktree=None, integration=None, steal=False):
    if not ITEM_RE.match(item or ""):
        raise ValueError("item must be a backlog id such as I1.2.3 or #42")
    who = actor(project_dir, by)
    data = load(project_dir)
    current = active(data, item)
    stolen_from = None
    if current and current["claimed_by"] != who:
        if not steal:
            raise Contested(current)
        current["released_at"] = now_iso()
        current["released_by"] = who
        current["reason"] = "stolen"
        stolen_from = current["claimed_by"]
    elif current:
        # The same person again: refresh what they told us, keep the claim.
        for key, value in (("branch", branch), ("worktree", worktree), ("integration_branch", integration)):
            if value:
                current[key] = value
        current["updated_at"] = now_iso()
        save(project_dir, data)
        return current, False
    record = {"item": item, "claimed_by": who, "claimed_at": now_iso(), "updated_at": now_iso(),
              "branch": branch or None, "worktree": worktree or None,
              "integration_branch": integration or None, "stolen_from": stolen_from,
              "released_at": None, "released_by": None, "reason": None}
    data["claims"].append(record)
    save(project_dir, data)
    _audit(project_dir, "ITEM_CLAIMED", item, who,
           "stolen from %s" % stolen_from if stolen_from else (branch or "claimed"))
    return record, True


def release(project_dir, item, by=None, reason=None):
    data = load(project_dir)
    current = active(data, item)
    if current is None:
        raise KeyError(item)
    who = actor(project_dir, by)
    current["released_at"] = now_iso()
    current["released_by"] = who
    current["reason"] = (reason or "").strip() or "released"
    save(project_dir, data)
    _audit(project_dir, "ITEM_RELEASED", item, who, current["reason"])
    return current


def listing(project_dir, only_active=True):
    data = load(project_dir)
    return [c for c in data["claims"] if not only_active or not c.get("released_at")]


def render_text(claims):
    if not claims:
        return "no claims"
    out = []
    for c in claims:
        state = "released %s (%s)" % (c["released_at"], c.get("reason")) if c.get("released_at") else "active"
        out.append("%-10s %-20s %s  branch=%s  worktree=%s%s  [%s]" % (
            c["item"], c["claimed_by"], c["claimed_at"], c.get("branch") or "-", c.get("worktree") or "-",
            ("  -> %s" % c["integration_branch"]) if c.get("integration_branch") else "", state))
    return "\n".join(out)


# ---------------------------------------------------------------------------- worktrees
def _git(project_dir, *args):
    return subprocess.run(["git", "-C", project_dir] + list(args), capture_output=True, text=True)


def _branch_exists(project_dir, branch):
    return _git(project_dir, "show-ref", "--verify", "--quiet", "refs/heads/%s" % branch).returncode == 0


def worktree_add(project_dir, item, root=None, branch=None, base=None):
    if not ITEM_RE.match(item or ""):
        raise ValueError("item must be a backlog id such as I1.2.3 or #42")
    top = _git(project_dir, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise OSError("not a git repository: %s" % project_dir)
    project_dir = top.stdout.strip()
    root = root or os.path.join(os.path.dirname(project_dir), os.path.basename(project_dir) + "-worktrees")
    root = root if os.path.isabs(root) else os.path.normpath(os.path.join(project_dir, root))
    safe = item.replace("#", "issue-")
    path = os.path.join(root, safe)
    branch = branch or "feat/%s" % safe
    if base is None:
        head = _git(project_dir, "rev-parse", "--abbrev-ref", "HEAD")
        base = head.stdout.strip() if head.returncode == 0 else "HEAD"
    os.makedirs(root, exist_ok=True)
    if _branch_exists(project_dir, branch):
        result = _git(project_dir, "worktree", "add", path, branch)
    else:
        result = _git(project_dir, "worktree", "add", "-b", branch, path, base)
    if result.returncode != 0:
        raise OSError((result.stderr or result.stdout).strip())
    data = load(project_dir)
    current = active(data, item)
    if current:
        current["worktree"], current["branch"], current["updated_at"] = path, branch, now_iso()
        save(project_dir, data)
    return {"item": item, "worktree": path, "branch": branch, "base": base}


def worktree_remove(project_dir, item):
    data = load(project_dir)
    current = active(data, item) or next(
        (c for c in reversed(data["claims"]) if c["item"] == item and c.get("worktree")), None)
    if not current or not current.get("worktree"):
        raise KeyError(item)
    result = _git(project_dir, "worktree", "remove", "--force", current["worktree"])
    if result.returncode != 0:
        raise OSError((result.stderr or result.stdout).strip())
    current["worktree"] = None
    current["updated_at"] = now_iso()
    save(project_dir, data)
    return {"item": item, "removed": True}


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
        sys.stderr.write("backlog_claims: not a directory: %s\n" % project)
        return 2
    try:
        if verb == "claim":
            if len(argv) < 3:
                raise ValueError("claim needs <item>")
            kv = _kv(argv[3:], ("by", "branch", "worktree", "integration", "steal"))
            record, created = claim(project, argv[2], kv.get("by"), kv.get("branch"), kv.get("worktree"),
                                    kv.get("integration"), kv.get("steal", "").lower() == "true")
            sys.stdout.write(json.dumps({"item": record["item"], "claimed_by": record["claimed_by"],
                                         "created": created, "stolen_from": record.get("stolen_from")}) + "\n")
            return 0
        if verb == "release":
            if len(argv) < 3:
                raise ValueError("release needs <item>")
            kv = _kv(argv[3:], ("by", "reason"))
            record = release(project, argv[2], kv.get("by"), kv.get("reason"))
            sys.stdout.write(json.dumps({"item": record["item"], "released_by": record["released_by"],
                                         "reason": record["reason"]}) + "\n")
            return 0
        if verb == "list":
            kv = _kv(argv[2:], ("active", "format"))
            claims = listing(project, kv.get("active", "true").lower() != "false")
            if kv.get("format", "text") == "json":
                sys.stdout.write(json.dumps(claims, ensure_ascii=False, indent=2) + "\n")
            else:
                sys.stdout.write(render_text(claims) + "\n")
            return 0
        if verb == "worktree":
            if len(argv) < 4 or argv[2] not in ("add", "remove"):
                raise ValueError("worktree needs add|remove <item>")
            if argv[2] == "add":
                kv = _kv(argv[4:], ("root", "branch", "base"))
                sys.stdout.write(json.dumps(worktree_add(project, argv[3], kv.get("root"), kv.get("branch"),
                                                         kv.get("base"))) + "\n")
            else:
                sys.stdout.write(json.dumps(worktree_remove(project, argv[3])) + "\n")
            return 0
        raise ValueError("verb must be claim, release, list or worktree")
    except Contested as exc:
        sys.stderr.write("backlog_claims: %s is held by %s since %s (steal=true to take it)\n" % (
            argv[2], exc.holder["claimed_by"], exc.holder["claimed_at"]))
        return 3
    except KeyError as exc:
        sys.stderr.write("backlog_claims: no active claim on %s\n" % exc.args[0])
        return 2
    except ValueError as exc:
        sys.stderr.write("backlog_claims: %s\n" % exc)
        return 2
    except OSError as exc:
        sys.stderr.write("backlog_claims: %s\n" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
