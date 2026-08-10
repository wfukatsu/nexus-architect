"""Shared data layer for the backlog-status dashboard tools.

Loads reports/backlog/backlog-manifest.json (written by /architect:export-backlog and
advanced by implement-backlog / review-issue / merge-issue / capture-followup), derives
each node's delivery status and Implemented/Reviewed/Merged stages, and builds the
Epic -> Sub-Epic -> Issue tree. Overlays live tracker labels fetched via glab / gh
("sync"); per the backlog contract the tracker wins over the manifest, and a node's
`labels` array is NEVER read as state — it is the creation seed.

Syncing covers every place the tracker keeps the tree. On GitLab that is two endpoints,
not one: Issues live in the project and Epics/Sub-Epics live in the *group*, so a
project-only fetch left every parent unsynced — and, worse, group Epic iids restart at 1
and collide with the project's Issue iids, so an iid-keyed cache silently gave Epic 1 the
status of Issue #1. Items are therefore keyed by a canonical URL (platform + kind + path
+ iid), with iid lookups kept only as a fallback for manifests that record no URL.

The manifest header (platform / project / group) is inferred from the nodes' own remote
URLs when it is absent — early manifests were written as a bare node array, which used to
make sync fail with "unknown platform" and pin the whole tree at todo.

Consumed by tools/lib/backlog_status_report.py (one-shot / JSON / Markdown) and
tools/lib/backlog_status_view.py (the live dashboard's backlog tab). Display helpers (dw/pad/clip/
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
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import token_cost_data as D  # noqa: E402  (display helpers; no cost logic used)

STATUSES = ["todo", "doing", "review", "done", "blocked"]
FOLLOWUP_ID = re.compile(r"^I(\d+(?:\.\d+)*)\.F(\d+)$")

# Delivery-status glyphs. All Unicode picks are East Asian Ambiguous or Neutral and go
# through D.dw(), so --ambiguous-width=2 keeps columns honest; the ASCII set engages
# automatically in ASCII mode (--ascii, --lang=ja, or a non-UTF-8 stdout).
# `stale` is not a delivery status — it is the pipeline strip's invalidated-phase count,
# kept identical to the pipeline view's glyph so one symbol means one thing in both tabs.
STATUS_GLYPHS_UNICODE = {"todo": "○", "doing": "◐", "review": "◎", "done": "●",
                         "blocked": "✗", "followup": "F", "drift": "↯", "current": "▶",
                         "stale": "↺"}
STATUS_GLYPHS_ASCII = {"todo": "o", "doing": "~", "review": "?", "done": "*",
                       "blocked": "x", "followup": "F", "drift": "!", "current": ">",
                       "stale": "@"}
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
        "no_match": "no item matches %s", "clear_filter": "press f to clear it",
        "pipeline": "pipeline", "checked": "checked", "every": "every %ss",
        "synced": "tracker synced", "not_synced": "tracker not synced (s)",
        "syncing": "syncing tracker...", "sync_failed": "tracker sync failed",
        "status": "status", "stages": "stages", "issue": "issue", "pr": "pr",
        "origin": "origin", "updated": "updated", "impl_files": "files",
        "decisions": "decisions", "review_doc": "review", "queue": "follow-up queue",
        "queued_entries": "%d unflushed entries", "drift": "tracker %s / manifest %s - tracker wins",
        "drift_rollup": "tracker says %s / children add up to %s - the children win",
        "sync_partial": "partly synced", "no_tracker": "no tracker in manifest",
        "unreached": "%d item(s) the tracker did not return, shown from the manifest: %s",
        "stages_note": "stages from manifest - body checkboxes are the authoritative rendering",
        "source": "source", "copied": "copied", "shown": "command",
        "no_clipboard": "clipboard unavailable - command shown above",
        "paste_hint": "(paste into Claude Code)",
        "exec_hint": "run with --exec to launch claude from here",
        "actions": "actions", "keys": " ^v/jk select | <> fold | Enter actions | Tab view"
                                     " | a ask | s sync | f filter | o url | c copy"
                                     " | r refresh",
        "menu_keys": "Enter copy | e run via claude | Esc close",
        "filter": "filter", "all": "all", "unparented": "(unparented)",
        "too_small": "terminal too small", "empty": "nothing to show",
        "unknown_epic": "unknown epic: %s", "known_epics": "epics in this manifest: %s",
        "help_glyphs": "backlog glyphs",
        "help_stages": "implemented / reviewed / merged",
        "help_followup": "follow-up item (captured mid-delivery)",
        "help_drift": "drift: the tracker and the manifest disagree (tracker wins)",
        "ask_why": "Why is this item still %s?",
        "ask_next": "What should I run next on this item, and why?",
        "ask_summary": "Summarize what has happened on this item so far.",
    },
    "ja": {
        "title": "バックログデリバリー", "live": "LIVE", "issues": "Issue", "done": "完了",
        "detail": "詳細", "no_manifest": "バックログマニフェストがありません",
        "no_match": "%s に一致する項目はありません", "clear_filter": "f で解除",
        "pipeline": "パイプライン", "checked": "確認", "every": "%s秒毎",
        "synced": "トラッカー同期", "not_synced": "トラッカー未同期 (s)",
        "syncing": "トラッカー同期中...", "sync_failed": "トラッカー同期失敗",
        "status": "状態", "stages": "ステージ", "issue": "Issue", "pr": "PR",
        "origin": "起源", "updated": "更新", "impl_files": "ファイル",
        "decisions": "決定", "review_doc": "レビュー", "queue": "フォローアップキュー",
        "queued_entries": "未処理 %d 件", "drift": "トラッカー %s / マニフェスト %s - トラッカー優先",
        "drift_rollup": "トラッカー %s / 子アイテム集計 %s - 子アイテム優先",
        "sync_partial": "一部のみ同期", "no_tracker": "マニフェストにトラッカー情報なし",
        "unreached": "トラッカーが返さなかった %d 件はマニフェスト由来の表示: %s",
        "stages_note": "ステージはマニフェスト由来 - 正式な表示は本文のチェックボックス",
        "source": "情報源", "copied": "コピー済", "shown": "コマンド",
        "no_clipboard": "クリップボード利用不可 - 上記コマンドを使用",
        "paste_hint": "(Claude Code に貼り付け)",
        "exec_hint": "--exec 付きで起動すると claude をここから実行できます",
        "actions": "アクション", "keys": " ^v/jk 選択 | <> 開閉 | Enter アクション"
                                        " | Tab ビュー | a 質問 | s 同期 | f フィルタ"
                                        " | o URL | c コピー | r 更新",
        "menu_keys": "Enter コピー | e claude 実行 | Esc 閉じる",
        "filter": "フィルタ", "all": "全て", "unparented": "(親なし)",
        "too_small": "画面が小さすぎます", "empty": "表示するものがありません",
        "unknown_epic": "存在しない Epic: %s",
        "known_epics": "このマニフェストの Epic: %s",
        "help_glyphs": "バックログの記号",
        "help_stages": "実装 / レビュー / マージ",
        "help_followup": "フォローアップ項目 (デリバリー中に発見)",
        "help_drift": "ドリフト: トラッカーとマニフェストの食い違い (トラッカー優先)",
        "ask_why": "この項目がまだ %s なのはなぜ？",
        "ask_next": "この項目について次に実行すべきことは？その理由は？",
        "ask_summary": "この項目でこれまでに起きたことを要約して。",
    },
}


def labels(lang):
    table = BS_LABELS.get(lang, BS_LABELS["en"])
    if D.ASCII_ONLY:
        return {k: D.plain(v) for k, v in table.items()}
    return table


# ----------------------------------------------------------------- tracker URLs
# GitLab paths carry the `/-/` separator and name the kind; a group Epic additionally
# sits under /groups/. GitLab renders an Issue as either /-/issues/N or /-/work_items/N
# depending on version and entry point, so both fold onto the same canonical kind.
GITLAB_URL = re.compile(
    r"^(?P<scheme>https?)://(?P<host>[^/]+)/(?P<path>.+?)/-/"
    r"(?P<kind>issues|work_items|epics)/(?P<iid>\d+)")
GITHUB_URL = re.compile(
    r"^(?P<scheme>https?)://(?P<host>[^/]+)/(?P<path>[^/]+/[^/]+)/"
    r"(?:issues|pull)/(?P<iid>\d+)")


def parse_remote_url(url):
    """(platform, kind, path, iid) for a tracker item URL, or None.

    `kind` is "epic" or "issue" — never the URL's own spelling — and `path` is the
    group/project path with GitLab's /groups/ prefix stripped, so the value matches what
    the manifest header and the CLI flags call the same container.
    """
    if not url:
        return None
    m = GITLAB_URL.match(url)
    if m:
        kind = "epic" if m.group("kind") == "epics" else "issue"
        path = re.sub(r"^groups/", "", m.group("path"))
        return ("gitlab", kind, path, int(m.group("iid")))
    m = GITHUB_URL.match(url)
    if m:  # GitHub has no Epic type: the whole tree is issues in one repository
        return ("github", "issue", m.group("path"), int(m.group("iid")))
    return None


def tracker_key(url):
    """The cache key both sides of a sync agree on, or None for an unparseable URL."""
    parsed = parse_remote_url(url)
    if parsed is None:
        return None
    return "%s:%s:%s#%d" % parsed


# ----------------------------------------------------------------- manifest loading
def load_manifest(path, project_dir=None):
    """The manifest as {platform, project, group, nodes}; None when unreadable.

    A bare node array — and a header missing platform/project/group — is completed from
    the nodes' own remote URLs, falling back to the project's git remote. Without this
    the manifests written before the header existed can be drawn but never synced.
    """
    raw = D.load_json(path)
    if raw is None:
        return None
    if isinstance(raw, list):  # tolerate a bare node array
        raw = {"nodes": raw}
    raw.setdefault("nodes", [])
    for key in ("platform", "project", "group"):
        raw.setdefault(key, "")
    if project_dir is None:
        # <project>/reports/backlog/backlog-manifest.json
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(path))))
    infer_tracker(raw, project_dir)
    return raw


def infer_tracker(manifest, project_dir=None):
    """Fill in absent platform/project/group from the nodes; recorded values are kept."""
    for platform, kind, path, _ in filter(None, (
            parse_remote_url((n.get("remote") or {}).get("url"))
            for n in manifest.get("nodes") or [])):
        manifest["platform"] = manifest.get("platform") or platform
        if manifest["platform"] != platform:
            continue
        slot = "group" if kind == "epic" else "project"
        manifest[slot] = manifest.get(slot) or path
        if manifest.get("project") and (manifest.get("group") or platform != "gitlab"):
            return manifest
    if not manifest.get("project") and project_dir:
        remote = git_remote(project_dir)
        if remote:
            manifest["platform"] = manifest.get("platform") or remote[0]
            if manifest["platform"] == remote[0]:
                manifest["project"] = remote[1]
    return manifest


def git_remote(project_dir):
    """(platform, path) of the project's origin remote, or None when there is none."""
    try:
        proc = subprocess.run(["git", "-C", project_dir, "remote", "get-url", "origin"],
                              capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    url = proc.stdout.decode("utf-8", "replace").strip()
    m = re.match(r"^(?:https?://(?:[^@/]+@)?|(?:ssh://)?git@)([^/:]+)[/:](.+?)(?:\.git)?$",
                 url)
    if not m:
        return None
    host, path = m.group(1).lower(), m.group(2)
    platform = "gitlab" if "gitlab" in host else "github" if "github" in host else None
    return (platform, path) if platform else None


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
def tracker_lookup(node, sync_cache):
    """This node's synced tracker entry, or None.

    Matched on the canonical URL first: on GitLab a group Epic and a project Issue can
    both be number 1, so the bare iid is only consulted for manifests that recorded no
    URL — and then only under this node's own kind.
    """
    if not sync_cache:
        return None
    remote = node.get("remote") or {}
    url, iid = remote.get("url"), remote.get("iid")
    kind = (parse_remote_url(url) or (None, None))[1] or (
        "epic" if node.get("level") in ("epic", "sub-epic") else "issue")
    keys = [tracker_key(url)]
    if iid is not None:
        keys += ["%s#%s" % (kind, iid), iid]
    for key in keys:
        if key is not None and key in sync_cache:
            return sync_cache[key]
    return None


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
    entry = tracker_lookup(node, sync_cache)
    if entry:
        tracker_status = entry.get("status")
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
        "rollup": False,
    }


def aggregate_status(kid_states):
    """One status for a parent from its children's."""
    if all(s == "done" for s in kid_states):
        return "done"
    if any(s == "blocked" for s in kid_states):
        return "blocked"
    if any(s == "review" for s in kid_states):
        return "review"
    if any(s in ("doing", "done") for s in kid_states):
        return "doing"
    return "todo"


def rollup_state(node, children, states, sync_cache=None):
    """Parent status: own impl.status (merge-issue writes roll-ups) else child aggregate.

    A parent's own tracker label is read but does not win here, which is where a parent
    differs from an Issue. An Epic's `status::*` label is set by hand at creation and
    then left behind — every one of this project's Epics still says todo while its
    Issues are closed — so believing it would report a finished Sub-Epic as untouched.
    What its children actually delivered is the honest answer; a label that disagrees is
    surfaced as drift instead of overriding it. A parent with no children in the manifest
    has nothing to aggregate, so there the tracker wins as usual.
    """
    own = derive_state(node, sync_cache)
    kid_states = [states[c["local_id"]]["status"] for c in children]
    manifest_status = (node.get("impl") or {}).get("status")
    manifest_status = manifest_status if manifest_status in STATUSES else None
    if not kid_states:
        agg = own["status"]
    elif manifest_status:
        agg, own["source"] = manifest_status, "manifest"
    else:
        agg, own["source"] = aggregate_status(kid_states), "rollup"
    own["drift"] = bool(own["tracker_status"]) and own["tracker_status"] != agg
    own["status"] = agg
    own["rollup"] = True
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
                states[n["local_id"]] = rollup_state(n, kids, states, sync_cache)
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
    """Phase progress strip data for the backlog header, or None.

    Derived by the pipeline view's own state layer rather than counted off the registry,
    so this strip cannot contradict the pipeline tab sitting one Tab away: the manifest
    supplies the phase total (not "however many the registry happens to mention"), the
    filesystem fills in phases no skill recorded, and an invalidated phase leaves the
    completed count the same way it does there.

    Returns None when the project has no pipeline at all. If the pipeline module is
    unusable for any reason the registry count stands in, so the backlog view keeps
    working on its own.
    """
    try:
        import pipeline_status_data as P
        state = P.derive_all(project_dir)
        if not state["has_progress"] and not any(
                p["written"] for p in state["phases"].values()):
            return None
        s = state["summary"]
        return {"total": s["total"], "completed": s["completed"],
                "current": state["current"], "stale": s["stale"],
                "next": state["next"]}
    except Exception:
        return _pipeline_from_registry(project_dir)


def _pipeline_from_registry(project_dir):
    """Fallback strip: the raw registry counts, with no manifest or filesystem input."""
    data = D.load_json(os.path.join(project_dir, "work", "pipeline-progress.json"))
    if not isinstance(data, dict) or not isinstance(data.get("phases"), dict):
        return None
    phases = data["phases"]
    completed = sum(1 for p in phases.values()
                    if (p or {}).get("status") in ("completed", "skipped"))
    current = next((name for name, p in phases.items()
                    if (p or {}).get("status") == "in_progress"), None)
    return {"total": len(phases), "completed": completed, "current": current,
            "stale": 0, "next": None}


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
def tracker_sources(manifest):
    """[(label, argv, kind, prefix, sep)] — every endpoint holding part of this tree.

    GitLab keeps Issues in the project and Epics in the group, so a GitLab manifest with
    both recorded has two sources; GitHub keeps everything in one repository.
    """
    platform = manifest.get("platform") or ""
    project = manifest.get("project") or ""
    group = manifest.get("group") or ""
    out = []
    if platform == "gitlab":
        if project:
            out.append(("issues",
                        ["glab", "issue", "list", "--output", "json", "--all",
                         "--per-page", "200", "-R", project],
                        "issue", "status::", "::"))
        if group:
            out.append(("epics",
                        ["glab", "api",
                         "groups/%s/epics?per_page=100" % quote(group, safe="")],
                        "epic", "status::", "::"))
    elif platform == "github":
        if project:
            out.append(("issues",
                        ["gh", "issue", "list", "--state", "all", "--limit", "1000",
                         "--json", "number,labels,state,url", "--repo", project],
                        "issue", "status:", ":"))
    return out


def _run_json(cmd, timeout):
    """The command's stdout as a JSON list; RuntimeError with a one-line reason."""
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
    return items if isinstance(items, list) else []


def item_status(item, prefix, sep):
    """The status a tracker item reports, or None when it reports nothing.

    A `status::*` label is the contract and wins. A closed item carrying no such label
    still says something unambiguous — it is done — and reading that is what keeps a
    tree that was closed outside the deliver-backlog flow from showing as todo.
    """
    status = None
    for lab in item.get("labels") or []:
        name = lab.get("name") if isinstance(lab, dict) else lab
        if name and name.startswith(prefix):
            candidate = name.split(sep)[-1]
            if candidate in STATUSES:
                status = candidate
    if status is None and str(item.get("state") or "").lower() in ("closed", "merged"):
        status = "done"
    return status


def sync_tracker(manifest, timeout=15):
    """Fetch live status from every tracker source: (cache, warnings).

    The cache maps canonical URL keys — plus "<kind>#<iid>" and bare-iid aliases for
    manifests without URLs — to {status, state, url, fetched_at}. A source that fails
    becomes a warning so one unreachable endpoint (a group whose Epics need a licence
    tier, say) cannot blank out the rest; RuntimeError is raised only when nothing at
    all could be fetched, and the caller then keeps its previous cache.
    """
    platform = manifest.get("platform") or ""
    if platform not in ("gitlab", "github"):
        raise RuntimeError("unknown platform in manifest: %r" % platform)
    sources = tracker_sources(manifest)
    if not sources:
        raise RuntimeError("manifest names no %s project or group to sync from"
                           % platform)
    found, errors, now = [], [], datetime.now()
    for label, cmd, kind, prefix, sep in sources:
        try:
            items = _run_json(cmd, timeout)
        except RuntimeError as exc:
            errors.append("%s: %s" % (label, exc))
            continue
        found += _entries(items, kind, prefix, sep, now)
    if errors and len(errors) == len(sources):
        raise RuntimeError("; ".join(errors))
    cache = _index(found)
    return cache, errors + unreached(manifest, cache)


def unreached(manifest, cache):
    """[warning] when exported nodes were not in what the tracker returned.

    `gh issue list --limit 1000` and `glab --per-page 200` return a window, not the
    whole tracker, and an item outside it looks exactly like an item with nothing to
    say — it falls back to the manifest and renders as todo. That is the failure this
    whole change is about, so it is reported rather than absorbed.
    """
    missing = [n.get("local_id") for n in manifest.get("nodes") or []
               if (n.get("remote") or {}).get("url") or (n.get("remote") or {}).get("iid")
               if tracker_lookup(n, cache) is None]
    if not missing:
        return []
    T = labels(os.environ.get("NX_LANG", "en"))
    return [T["unreached"] % (len(missing), ", ".join(filter(None, missing[:5])))]


def _entries(items, kind, prefix, sep, now):
    """[(kind, iid, entry)] for one source's items.

    Everything fetched is indexed, including items reporting no status (an open Issue
    with no `status::*` label), because the cache answers two different questions: what
    the tracker says about an item, and whether the tracker returned the item at all.
    Conflating them made a node the fetch never reached indistinguishable from an
    unlabelled one — both silently read as todo.
    """
    out = []
    for item in items:
        iid = item.get("iid") if item.get("iid") is not None else item.get("number")
        if iid is None:
            continue
        out.append((kind, iid, {
            "status": item_status(item, prefix, sep), "state": item.get("state"),
            "url": item.get("web_url") or item.get("url"), "fetched_at": now}))
    return out


def _index(found):
    """Key every entry by canonical URL and "<kind>#<iid>"; add the bare iid only when
    it is unambiguous across the whole sync (group Epic 1 vs project Issue 1 is not)."""
    cache = {}
    for kind, iid, entry in found:
        for key in (tracker_key(entry["url"]), "%s#%s" % (kind, iid)):
            if key:
                cache[key] = entry
    counts = {}
    for _, iid, _ in found:
        counts[iid] = counts.get(iid, 0) + 1
    for kind, iid, entry in found:
        if counts[iid] == 1:
            cache[iid] = entry
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
    # Orphans belong to no Epic, so an epic filter excludes them entirely.
    if not epic_filter:
        for orphan in children.get("?", []):
            if matches(orphan):
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
