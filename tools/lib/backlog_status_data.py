"""Shared data layer for the backlog-status dashboard tools.

Loads reports/backlog/backlog-manifest.json (written by /architect:export-backlog and
advanced by implement-backlog / review-issue / merge-issue / capture-followup), derives
each node's delivery status and Implemented/Reviewed/Merged stages, and builds the
Epic -> Sub-Epic -> Issue tree. Optionally overlays live tracker labels fetched via
glab / gh ("sync"); per the backlog contract the tracker wins over the manifest, and a
node's `labels` array is NEVER read as state — it is the creation seed.

Consumed by tools/lib/backlog_status_report.py (one-shot / JSON / Markdown) and
tools/lib/backlog_status_tui.py (live dashboard). Generic display helpers (dw/pad/clip/
bar/glyphs/ASCII detection) are imported from token_cost_data, which reads the same NX_*
environment the launcher exports.
"""

import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import token_cost_data as D  # noqa: E402  (display helpers; no cost logic used)

STATUSES = ["todo", "doing", "review", "done", "blocked"]
FOLLOWUP_ID = re.compile(r"^I(\d+(?:\.\d+)*)\.F(\d+)$")

# Delivery-status glyphs. All Unicode picks are East Asian Ambiguous or Neutral and go
# through D.dw(), so --ambiguous-width=2 keeps columns honest; the ASCII set engages
# automatically in ASCII mode (--ascii, --lang=ja, or a non-UTF-8 stdout).
STATUS_GLYPHS_UNICODE = {"todo": "○", "doing": "◐", "review": "◎", "done": "●",
                         "blocked": "✗", "followup": "F", "drift": "↯", "current": "▶"}
STATUS_GLYPHS_ASCII = {"todo": "o", "doing": "~", "review": "?", "done": "*",
                       "blocked": "x", "followup": "F", "drift": "!", "current": ">"}
SG = STATUS_GLYPHS_ASCII if D.ASCII_ONLY else STATUS_GLYPHS_UNICODE

# Tree-drawing glyphs, kept local (not added to token_cost_data's tables).
TREE_UNICODE = {"tee": "├─ ", "elbow": "└─ ", "pipe": "│  ", "gap": "   "}
TREE_ASCII = {"tee": "+- ", "elbow": "`- ", "pipe": "|  ", "gap": "   "}
TG = TREE_ASCII if D.ASCII_ONLY else TREE_UNICODE

STATUS_STYLE = {"todo": "dim", "doing": "warn", "review": "head", "done": "accent",
                "blocked": "alert"}

BS_LABELS = {
    "en": {
        "title": "Backlog Delivery", "live": "LIVE", "issues": "Issues", "done": "done",
        "detail": "Detail", "no_manifest": "no backlog manifest",
        "pipeline": "pipeline", "checked": "checked", "every": "every %ss",
        "synced": "tracker synced", "not_synced": "tracker not synced (s)",
        "syncing": "syncing tracker...", "sync_failed": "tracker sync failed",
        "status": "status", "stages": "stages", "issue": "issue", "pr": "pr",
        "origin": "origin", "updated": "updated", "impl_files": "files",
        "decisions": "decisions", "review_doc": "review", "queue": "follow-up queue",
        "queued_entries": "%d unflushed entries", "drift": "tracker %s / manifest %s - tracker wins",
        "stages_note": "stages from manifest - body checkboxes are the authoritative rendering",
        "source": "source", "copied": "copied", "shown": "command",
        "no_clipboard": "clipboard unavailable - command shown above",
        "paste_hint": "(paste into Claude Code)",
        "exec_hint": "run with --exec to launch claude from here",
        "actions": "actions", "keys": " ^v/jk select | <> fold | Enter actions | s sync"
                                     " | f filter | o url | c copy | r refresh | q quit",
        "menu_keys": "Enter copy | e run via claude | Esc close",
        "filter": "filter", "all": "all", "unparented": "(unparented)",
        "too_small": "terminal too small",
    },
    "ja": {
        "title": "バックログデリバリー", "live": "LIVE", "issues": "Issues", "done": "done",
        "detail": "詳細", "no_manifest": "バックログマニフェストがありません",
        "pipeline": "パイプライン", "checked": "確認", "every": "%s秒毎",
        "synced": "トラッカー同期", "not_synced": "トラッカー未同期 (s)",
        "syncing": "トラッカー同期中...", "sync_failed": "トラッカー同期失敗",
        "status": "状態", "stages": "ステージ", "issue": "issue", "pr": "pr",
        "origin": "起源", "updated": "更新", "impl_files": "ファイル",
        "decisions": "決定", "review_doc": "レビュー", "queue": "フォローアップキュー",
        "queued_entries": "未処理 %d 件", "drift": "トラッカー %s / マニフェスト %s - トラッカー優先",
        "stages_note": "ステージはマニフェスト由来 - 正式な表示は本文のチェックボックス",
        "source": "情報源", "copied": "コピー済", "shown": "コマンド",
        "no_clipboard": "クリップボード利用不可 - 上記コマンドを使用",
        "paste_hint": "(Claude Code に貼り付け)",
        "exec_hint": "--exec 付きで起動すると claude をここから実行できます",
        "actions": "アクション", "keys": " ^v/jk 選択 | <> 開閉 | Enter アクション | s 同期"
                                        " | f フィルタ | o URL | c コピー | r 更新 | q 終了",
        "menu_keys": "Enter コピー | e claude 実行 | Esc 閉じる",
        "filter": "フィルタ", "all": "全て", "unparented": "(親なし)",
        "too_small": "画面が小さすぎます",
    },
}


def labels(lang):
    table = BS_LABELS.get(lang, BS_LABELS["en"])
    if D.ASCII_ONLY:
        return {k: D.plain(v) for k, v in table.items()}
    return table


# ----------------------------------------------------------------- manifest loading
def load_manifest(path):
    """The manifest as {platform, project, group, nodes}; None when unreadable."""
    raw = D.load_json(path)
    if raw is None:
        return None
    if isinstance(raw, list):  # tolerate a bare node array
        return {"platform": "", "project": "", "group": "", "nodes": raw}
    raw.setdefault("nodes", [])
    return raw


def sort_key(local_id):
    """Order children: positional numeric tuples first, F-nodes after their siblings.

    The follow-up flag leads the key — siblings share a parent, so comparing the
    numeric tuples alone would let the F-node's shorter stem sort first.
    """
    m = FOLLOWUP_ID.match(local_id)
    if m:
        return (1, int(m.group(2)), ())
    nums = re.findall(r"\d+", local_id)
    return (0, 0, tuple(int(n) for n in nums))


def build_tree(nodes):
    """parent local_id -> ordered child nodes; orphans under the synthetic None root."""
    by_id = {n.get("local_id"): n for n in nodes if n.get("local_id")}
    children = {}
    for n in nodes:
        lid = n.get("local_id")
        if not lid:
            continue
        parent = n.get("parent_local_id")
        if parent is not None and parent not in by_id:
            parent = "?"  # orphan bucket — shown, never dropped
        children.setdefault(parent, []).append(n)
    for kids in children.values():
        kids.sort(key=lambda n: sort_key(n["local_id"]))
    return by_id, children


# ----------------------------------------------------------------- state derivation
def derive_state(node, sync_cache=None):
    """Delivery status + stages for one node, manifest-first, tracker-wins.

    Returns {status, source, drift, tracker_status, stages: {implemented, reviewed,
    merged}, followup}. The node's `labels` array is deliberately never consulted:
    it is the creation seed, not live state (deliver-backlog contract).
    """
    impl = node.get("impl") or {}
    manifest_status = impl.get("status") if impl.get("status") in STATUSES else None
    status = manifest_status or "todo"
    source = "manifest" if manifest_status else "seed"

    tracker_status = None
    drift = False
    iid = (node.get("remote") or {}).get("iid")
    if sync_cache and iid in sync_cache:
        tracker_status = sync_cache[iid].get("status")
        if tracker_status in STATUSES:
            drift = tracker_status != status and manifest_status is not None
            status = tracker_status
            source = "tracker"

    pr = node.get("pr") or {}
    merged = bool(pr.get("merged")) or status == "done"
    reviewed = merged or bool(pr.get("url"))
    implemented = reviewed or status in ("review", "done")
    return {
        "status": status, "source": source, "drift": drift,
        "tracker_status": tracker_status,
        "stages": {"implemented": implemented, "reviewed": reviewed, "merged": merged},
        "followup": bool(FOLLOWUP_ID.match(node.get("local_id") or "")),
    }


def rollup_state(node, children, states):
    """Parent status: own impl.status (merge-issue writes roll-ups) else child aggregate."""
    own = derive_state(node)
    kid_states = [states[c["local_id"]]["status"] for c in children]
    if own["source"] != "seed" or not kid_states:
        agg = own["status"]
    elif all(s == "done" for s in kid_states):
        agg = "done"
    elif any(s == "blocked" for s in kid_states):
        agg = "blocked"
    elif any(s == "review" for s in kid_states):
        agg = "review"
    elif any(s in ("doing", "done") for s in kid_states):
        agg = "doing"
    else:
        agg = "todo"
    own["status"] = agg
    own["stages"] = {
        "implemented": bool(kid_states) and all(
            states[c["local_id"]]["stages"]["implemented"] for c in children),
        "reviewed": False,  # not a parent-level stage (per checklist contract)
        "merged": agg == "done",
    }
    return own


def derive_all(manifest, sync_cache=None):
    """states[local_id] for every node, parents rolled up bottom-up; plus tree maps."""
    nodes = manifest["nodes"]
    by_id, children = build_tree(nodes)
    states = {}
    for n in nodes:  # issues first
        if n.get("level") == "issue":
            states[n["local_id"]] = derive_state(n, sync_cache)
    for level in ("sub-epic", "epic"):
        for n in nodes:
            if n.get("level") == level:
                kids = [c for c in children.get(n["local_id"], [])
                        if c["local_id"] in states]
                states[n["local_id"]] = rollup_state(n, kids, states)
    return by_id, children, states


def descendant_issue_counts(node, children, states):
    """(done, total) over all descendant Issues of `node`."""
    done = total = 0
    stack = list(children.get(node["local_id"], []))
    while stack:
        n = stack.pop()
        if n.get("level") == "issue":
            total += 1
            if states[n["local_id"]]["status"] == "done":
                done += 1
        stack.extend(children.get(n["local_id"], []))
    return done, total


def overall_summary(manifest, states):
    """Issue-level counts per status."""
    counts = {s: 0 for s in STATUSES}
    for n in manifest["nodes"]:
        if n.get("level") == "issue" and n.get("local_id") in states:
            counts[states[n["local_id"]]["status"]] += 1
    total = sum(counts.values())
    return {"by_status": counts, "issues_total": total, "issues_done": counts["done"]}


# ----------------------------------------------------------------- side inputs
def load_pipeline(project_dir):
    """Phase progress strip data from work/pipeline-progress.json, or None."""
    data = D.load_json(os.path.join(project_dir, "work", "pipeline-progress.json"))
    if not isinstance(data, dict) or not isinstance(data.get("phases"), dict):
        return None
    phases = data["phases"]
    completed = sum(1 for p in phases.values()
                    if (p or {}).get("status") in ("completed", "skipped"))
    current = next((name for name, p in phases.items()
                    if (p or {}).get("status") == "in_progress"), None)
    return {"total": len(phases), "completed": completed, "current": current}


def followup_queue_count(project_dir):
    """Number of `status: queued` entries in reports/backlog/followup-queue.md."""
    path = os.path.join(project_dir, "reports", "backlog", "followup-queue.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip() == "- status: queued")
    except OSError:
        return 0


def latest_review(project_dir, node):
    """(path, round) of the highest-round review doc for this Issue, or None."""
    iid = (node.get("remote") or {}).get("iid")
    candidates = set()
    for key in (node.get("local_id"), iid):
        if key is None:
            continue
        pattern = os.path.join(project_dir, "reports", "backlog", "reviews",
                               "review-%s-round*.md" % key)
        candidates.update(glob.glob(pattern))
    best = None
    for path in candidates:
        m = re.search(r"round(\d+)\.md$", path)
        rnd = int(m.group(1)) if m else 0
        if best is None or rnd > best[1]:
            best = (path, rnd)
    return best


def impl_log_path(project_dir, node):
    path = os.path.join(project_dir, "reports", "backlog", "impl-log",
                        "%s.md" % node.get("local_id"))
    return path if os.path.isfile(path) else None


# ----------------------------------------------------------------- tracker sync
def sync_tracker(manifest, timeout=15):
    """Fetch live status labels: {iid: {status, fetched_at}}. Raises RuntimeError
    with a one-line reason on failure; the caller keeps its previous cache."""
    platform = manifest.get("platform") or ""
    project = manifest.get("project") or ""
    if platform == "gitlab":
        cmd = ["glab", "issue", "list", "--output", "json", "--all", "--per-page", "200"]
        if project:
            cmd += ["-R", project]
        prefix, sep = "status::", "::"
    elif platform == "github":
        cmd = ["gh", "issue", "list", "--state", "all", "--limit", "1000",
               "--json", "number,labels"]
        if project:
            cmd += ["--repo", project]
        prefix, sep = "status:", ":"
    else:
        raise RuntimeError("unknown platform in manifest: %r" % platform)
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError("%s not found on PATH" % cmd[0])
    except subprocess.TimeoutExpired:
        raise RuntimeError("%s timed out after %ds" % (cmd[0], timeout))
    if proc.returncode != 0:
        line = (proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        raise RuntimeError(line[0] if line else "%s exited %d" % (cmd[0], proc.returncode))
    try:
        items = json.loads(proc.stdout.decode("utf-8", "replace"))
    except ValueError:
        raise RuntimeError("unparseable %s output" % cmd[0])
    if isinstance(items, dict):  # some glab versions wrap the list
        items = items.get("issues") or items.get("items") or []
    cache, now = {}, datetime.now()
    for item in items:
        iid = item.get("iid") or item.get("number")
        if iid is None:
            continue
        status = None
        for lab in item.get("labels") or []:
            name = lab.get("name") if isinstance(lab, dict) else lab
            if name and name.startswith(prefix):
                candidate = name.split(sep)[-1]
                if candidate in STATUSES:
                    status = candidate
        if status:
            cache[iid] = {"status": status, "fetched_at": now}
    return cache


# ----------------------------------------------------------------- actions & clipboard
def actions_for(node, state, queue_count=0):
    """(key, label, command) entries for the action menu / default `c` copy."""
    lid = node.get("local_id")
    url = (node.get("remote") or {}).get("url")
    level = node.get("level")
    out = []
    if level == "issue":
        out += [("implement", "/architect:implement-backlog %s" % lid),
                ("review", "/architect:review-issue %s" % lid),
                ("merge", "/architect:merge-issue %s" % lid),
                ("deliver", "/architect:deliver-backlog --issue=%s" % lid)]
    elif level == "sub-epic":
        epic = node.get("parent_local_id") or ""
        out += [("implement", "/architect:implement-backlog %s" % lid)]
        if epic:
            out += [("deliver epic", "/architect:deliver-backlog --epic=%s" % epic)]
    elif level == "epic":
        out += [("deliver", "/architect:deliver-backlog --epic=%s" % lid)]
    if url:
        out += [("open URL", url)]
    if queue_count:
        out += [("flush follow-ups (%d)" % queue_count,
                 "/architect:capture-followup --flush")]
    return out


def default_action(node, state, queue_count=0):
    """The status-appropriate default command (for the `c` quick-copy key)."""
    acts = actions_for(node, state, queue_count)
    if not acts:
        return None
    prefer = {"todo": "implement", "doing": "implement",
              "review": "merge" if (node.get("pr") or {}).get("url") else "review",
              "blocked": "deliver", "done": "open URL"}.get(state["status"])
    for label, cmd in acts:
        if prefer and label.startswith(prefer):
            return (label, cmd)
    return acts[0]


def clipboard_tool():
    """The first available clipboard command, probed once; None when there is none."""
    if sys.platform == "darwin" and _which("pbcopy"):
        return ["pbcopy"]
    if os.environ.get("WAYLAND_DISPLAY") and _which("wl-copy"):
        return ["wl-copy"]
    if _which("xclip"):
        return ["xclip", "-selection", "clipboard"]
    if _which("xsel"):
        return ["xsel", "-ib"]
    return None


def _which(name):
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d and os.access(os.path.join(d, name), os.X_OK):
            return True
    return False


def copy_clipboard(tool, text):
    """True when the copy succeeded; never raises."""
    if not tool:
        return False
    try:
        subprocess.run(tool, input=text.encode("utf-8"), timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def open_url(url):
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    try:
        subprocess.Popen([opener, url], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


# ----------------------------------------------------------------- rendering helpers
def stage_boxes(stages):
    """[I][R][M] with the unmet letters replaced by a middle dot (ASCII: period)."""
    dot = "." if D.ASCII_ONLY else "·"
    return "[%s][%s][%s]" % (
        "I" if stages["implemented"] else dot,
        "R" if stages["reviewed"] else dot,
        "M" if stages["merged"] else dot)


def flatten_tree(children, states, collapsed=None, status_filter=None, epic_filter=None):
    """Visible (node, depth, is_last_stack) rows in draw order.

    is_last_stack is the per-depth "last child" flags used to draw the tree lines.
    A status filter keeps parents whose subtree contains a match.
    """
    collapsed = collapsed or set()
    rows = []

    def matches(node):
        if status_filter and states[node["local_id"]]["status"] != status_filter:
            kids = children.get(node["local_id"], [])
            return any(matches(k) for k in kids)
        return True

    def walk(node, depth, stack):
        rows.append((node, depth, tuple(stack)))
        if node["local_id"] in collapsed:
            return
        kids = [k for k in children.get(node["local_id"], []) if matches(k)]
        for i, kid in enumerate(kids):
            walk(kid, depth + 1, stack + [i == len(kids) - 1])

    roots = [n for n in children.get(None, []) if matches(n)]
    if epic_filter:
        roots = [n for n in roots if n["local_id"] == epic_filter]
    for i, root in enumerate(roots):
        walk(root, 0, [])
    for orphan in children.get("?", []):
        rows.append((orphan, 0, ()))
    return rows


def tree_prefix(depth, last_stack):
    """The box-drawing prefix for one tree row."""
    if depth == 0:
        return ""
    parts = []
    for is_last in last_stack[:-1]:
        parts.append(TG["gap"] if is_last else TG["pipe"])
    parts.append(TG["elbow"] if last_stack[-1] else TG["tee"])
    return "".join(parts)
