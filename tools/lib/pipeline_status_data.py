"""Shared data layer for the pipeline view of the nexus status dashboard.

Answers "where is this project in the product / architect pipeline, right now?" from
three sources, in this order of authority:

  1. `<project>/work/pipeline-progress.json` — the progress registry the orchestrators
     write (`pending|in_progress|completed|failed|skipped` per phase).
  2. The declared `outputs:` of each phase in the plugin's `skill-dependencies.yaml`,
     checked against the real filesystem — this is what makes a phase show progress
     *while it runs* (3 of 4 outputs written) and what covers projects whose skills only
     ever wrote "completed" at the end.
  3. `<project>/work/token-usage.{json,jsonl}` — per-phase cost, and the heartbeat that
     says which phase produced tokens in the last few minutes.

The registry wins on status; the filesystem drives the output bar and raises a drift
flag when the two disagree (claimed completed with nothing written, or every output
present while still pending). Phases with no registry entry — notably the architect
manual extension tier — are derived from the filesystem alone.

Consumed by tools/lib/pipeline_status_report.py (one-shot / JSON / Markdown) and
tools/lib/pipeline_status_view.py (the live dashboard's pipeline tab). Display helpers
(dw/pad/clip/bar/glyphs/ASCII detection) come from token_cost_data, which reads the same
NX_* environment the launcher exports. Contract asserted by pipeline_status_data.test.py.
"""

import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import token_cost_data as D  # noqa: E402  (display helpers + load_json/parse_ts)

PHASE_STATUSES = ["pending", "in_progress", "completed", "failed", "skipped"]

# Phase-status glyphs. Same rules as the backlog set: Ambiguous/Neutral width only, and
# the ASCII table engages automatically in ASCII mode.
PHASE_GLYPHS_UNICODE = {"pending": "○", "in_progress": "◐", "completed": "●",
                        "failed": "✗", "skipped": "–", "current": "▶", "drift": "↯",
                        "active": "•", "gate": "G"}
PHASE_GLYPHS_ASCII = {"pending": "o", "in_progress": "~", "completed": "*",
                      "failed": "x", "skipped": "-", "current": ">", "drift": "!",
                      "active": ".", "gate": "G"}
PG = PHASE_GLYPHS_ASCII if D.ASCII_ONLY else PHASE_GLYPHS_UNICODE

PHASE_STYLE = {"pending": "dim", "in_progress": "warn", "completed": "accent",
               "failed": "alert", "skipped": "dim"}

# A phase counts as "running now" when the project produced tokens or wrote one of its
# outputs within this many seconds.
ACTIVE_WINDOW = 300

PS_LABELS = {
    "en": {
        "title": "Pipeline Progress", "phases": "Phases", "done": "done",
        "no_progress": "no work/pipeline-progress.json",
        "status": "status",
        "outputs": "outputs", "declared": "declared outputs", "deps": "depends on",
        "blocked_by": "waiting on", "model": "model", "cost": "cost",
        "gate": "gate", "verdict": "verdict", "open_assumptions": "open assumptions",
        "next": "next", "current": "running", "active": "active",
        "ago": "%s ago", "never": "no activity recorded",
        "started": "started", "completed_at": "completed", "updated": "updated",
        "note": "note", "summary": "summary", "errors": "errors", "warnings": "warnings",
        "drift_missing": "recorded completed, but no declared output exists",
        "drift_present": "every declared output exists, but still recorded pending",
        "source": "source", "source_progress": "progress registry",
        "source_derived": "derived from outputs", "source_condition": "condition",
        "optional": "optional", "rerunnable": "rerunnable", "standalone": "standalone",
        "gate_phase": "validation gate", "skipped_option": "excluded by skip_phases",
        "skipped_condition": "excluded by project options",
        "backlog": "backlog", "issues_done": "%d/%d issues done",
        "total_cost": "total cost", "unassigned": "unassigned",
        "keys": " ^v/jk select | <> fold | Enter actions | Tab view | a ask"
                " | f filter | o open | c copy | r refresh | ? help | q quit",
        "group_requirements": "Requirements", "group_investigation": "Investigation",
        "group_analysis": "Analysis", "group_evaluation": "Evaluation",
        "group_design": "Design", "group_review": "Review", "group_reporting": "Reporting",
        "group_extension": "Extensions (manual tier)", "group_core": "Product Core",
        "group_validation": "Validation Gate", "group_ux": "UX Foundation",
        "group_spec": "Specification", "group_codegen": "Code Generation",
        "group_domain": "Domain & API", "group_quality": "Quality & NFR",
        "group_adaptation": "Adaptation",
        "group_other": "Recorded outside the manifest",
        "help_glyphs": "pipeline glyphs",
        "help_outputs": "declared outputs that exist on disk",
        "help_drift": "drift: the registry and the filesystem disagree",
        "help_active": "active: tokens or an output written in the last 5 minutes",
        "help_optional": "optional phase (not part of the required path)",
        "ask_free": "free input...",
        "ask_why": "Why is this phase still %s?",
        "ask_next": "What should I run next, and why?",
        "ask_summary": "Summarize this phase's outputs.",
    },
    "ja": {
        "title": "パイプライン進捗", "phases": "フェーズ", "done": "完了",
        "no_progress": "work/pipeline-progress.json がありません",
        "status": "状態",
        "outputs": "出力", "declared": "宣言された出力", "deps": "依存",
        "blocked_by": "未充足の依存", "model": "モデル", "cost": "コスト",
        "gate": "ゲート", "verdict": "判定", "open_assumptions": "未検証の前提",
        "next": "次", "current": "実行中", "active": "稼働中",
        "ago": "%s前", "never": "稼働記録なし",
        "started": "開始", "completed_at": "完了", "updated": "更新",
        "note": "メモ", "summary": "要約", "errors": "エラー", "warnings": "警告",
        "drift_missing": "completed 記録だが宣言された出力が1つも無い",
        "drift_present": "宣言された出力は全て存在するが pending 記録のまま",
        "source": "情報源", "source_progress": "進捗レジストリ",
        "source_derived": "出力から導出", "source_condition": "条件",
        "optional": "任意", "rerunnable": "再実行可", "standalone": "独立実行",
        "gate_phase": "検証ゲート", "skipped_option": "skip_phases で除外",
        "skipped_condition": "プロジェクト設定で除外",
        "backlog": "バックログ", "issues_done": "Issue %d/%d 完了",
        "total_cost": "合計コスト", "unassigned": "未割当",
        "keys": " ^v/jk 選択 | <> 開閉 | Enter アクション | Tab ビュー | a 質問"
                " | f フィルタ | o 開く | c コピー | r 更新 | ? ヘルプ | q 終了",
        "group_requirements": "要件定義", "group_investigation": "調査",
        "group_analysis": "分析", "group_evaluation": "評価",
        "group_design": "設計", "group_review": "レビュー", "group_reporting": "レポート",
        "group_extension": "拡張ティア (手動実行)", "group_core": "プロダクトコア",
        "group_validation": "検証ゲート", "group_ux": "UX 基盤",
        "group_spec": "仕様化", "group_codegen": "コード生成",
        "group_domain": "ドメイン & API", "group_quality": "品質 & NFR",
        "group_adaptation": "変更適応",
        "group_other": "マニフェスト外の記録",
        "help_glyphs": "パイプラインの記号",
        "help_outputs": "宣言された出力のうち実在するもの",
        "help_drift": "ドリフト: 進捗レジストリと実ファイルが食い違っている",
        "help_active": "稼働中: 直近5分にトークン消費または出力の書き込みがあった",
        "help_optional": "任意フェーズ (必須の経路ではない)",
        "ask_free": "自由入力...",
        "ask_why": "このフェーズがまだ %s なのはなぜ？",
        "ask_next": "次に実行すべきことは？その理由は？",
        "ask_summary": "このフェーズの出力を要約して。",
    },
}


def labels(lang):
    table = PS_LABELS.get(lang, PS_LABELS["en"])
    if D.ASCII_ONLY:
        return {k: D.plain(v) for k, v in table.items()}
    return table


def group_title(T, key):
    return T.get("group_%s" % key, key)


# ------------------------------------------------------------------- mini YAML reader
# skill-dependencies.yaml is authored by hand in a deliberately small subset: nested
# mappings by indentation, `- item` block lists, `[a, b]` inline lists (which may wrap
# across lines), `{k: v}` inline maps, `#` comments. PyYAML is not guaranteed to be
# installed next to a python3 that can run a curses dashboard, so we parse that subset
# here rather than take the dependency. Both real manifests are parsed by the test.
_INLINE_OPEN = {"[": "]", "{": "}"}


def _strip_comment(line):
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(text):
    text = text.strip()
    if not text:
        return None
    if text[0] in _INLINE_OPEN:
        return _inline(text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    low = text.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~"):
        return None
    if re.match(r"^-?\d+$", text):
        return int(text)
    if re.match(r"^-?\d*\.\d+$", text):
        return float(text)
    return text


def _split_top(body):
    """Split an inline list/map body on commas that are not nested or quoted."""
    parts, depth, quote, cur = [], 0, None, []
    for ch in body:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur))
    return [p.strip() for p in parts]


def _inline(text):
    close = _INLINE_OPEN[text[0]]
    body = text[1:text.rindex(close)] if close in text else text[1:]
    items = _split_top(body)
    if text[0] == "[":
        return [_scalar(i) for i in items]
    out = {}
    for item in items:
        if ":" in item:
            k, v = item.split(":", 1)
            out[k.strip()] = _scalar(v)
    return out


def _balanced(text):
    depth, quote = 0, None
    for ch in text:
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
    return depth <= 0


def _logical_lines(text):
    """(indent, content) pairs, with wrapped inline lists/maps joined into one line."""
    out, pending, indent = [], None, 0
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if pending is not None:
            pending += " " + line.strip()
            if _balanced(pending):
                out.append((indent, pending))
                pending = None
            continue
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        if not _balanced(content):
            pending = content
            continue
        out.append((indent, content))
    if pending is not None:
        out.append((indent, pending))
    return out


def parse_yaml(text):
    """The skill-dependencies.yaml subset as nested dicts/lists. Never raises."""
    lines = _logical_lines(text)

    def block(start, indent):
        """Parse every line at `indent`; returns (value, next_index)."""
        i = start
        is_list = lines[i][1].startswith("- ") or lines[i][1] == "-"
        container = [] if is_list else {}
        while i < len(lines):
            ind, content = lines[i]
            if ind < indent:
                break
            if ind > indent:  # tolerate ragged authoring
                i += 1
                continue
            if isinstance(container, list):
                if not content.startswith("-"):
                    break
                container.append(_scalar(content[1:].strip()))
                i += 1
                continue
            if content.startswith("- "):
                break
            key, _, rest = content.partition(":")
            key, rest = key.strip(), rest.strip()
            i += 1
            if rest:
                container[key] = _scalar(rest)
                continue
            if i < len(lines) and lines[i][0] > ind:
                container[key], i = block(i, lines[i][0])
            elif i < len(lines) and lines[i][0] == ind and lines[i][1].startswith("- "):
                container[key], i = block(i, ind)
            else:
                container[key] = None
        return container, i

    if not lines:
        return {}
    value, _ = block(0, lines[0][0])
    return value if isinstance(value, dict) else {}


# ------------------------------------------------------------------- plugin manifests
PLUGINS = {
    "architect": {
        "manifest": os.path.join("skills", "common", "skill-dependencies.yaml"),
        "prefix": "/architect:",
        "orchestrator": "/architect:pipeline",
    },
    "product": {
        "manifest": os.path.join("skills", "product", "common", "skill-dependencies.yaml"),
        "prefix": "/product:",
        "orchestrator": "/product:start",
    },
}

# The architect manual extension tier: real skills that /architect:pipeline never runs,
# so they have no entry in skill-dependencies.yaml. Their outputs are listed here so the
# dashboard can derive their state from the filesystem when the registry is silent.
# (generate-docs writes into the target project's own source tree, which this tool
# cannot locate — it is shown, but only the registry can give it a status.)
EXTENSION_PHASES = {
    "investigate-security": dict(category="extension", model="sonnet", depends_on=["investigate"],
                                 outputs=["reports/before/{project}/architect:investigate-security.md"]),
    "select-scalardb-edition": dict(category="extension", model="sonnet", depends_on=[],
                                    outputs=["reports/03_design/scalardb-edition-selection.md"]),
    "design-scalardb-analytics": dict(category="extension", model="opus", depends_on=["design-scalardb"],
                                      outputs=["reports/03_design/scalardb-analytics-design.md"]),
    "design-implementation": dict(category="extension", model="opus", depends_on=["design-api"],
                                  outputs=["reports/06_implementation/"]),
    "generate-test-specs": dict(category="extension", model="sonnet", depends_on=["design-implementation"],
                                outputs=["reports/07_test-specs/"]),
    "generate-scalardb-code": dict(category="extension", model="sonnet", depends_on=["design-implementation"],
                                   outputs=["generated/*/src/main/java/"]),
    "generate-infra-code": dict(category="extension", model="sonnet", depends_on=["design-infrastructure"],
                                outputs=["generated/infrastructure/"]),
    "generate-docs": dict(category="extension", model="sonnet", depends_on=[], outputs=[]),
    "design-infrastructure": dict(category="extension", model="sonnet", depends_on=["design-microservices"],
                                  outputs=["reports/08_infrastructure/infrastructure-architecture.md",
                                           "reports/08_infrastructure/deployment-guide.md"]),
    "design-security": dict(category="extension", model="sonnet", depends_on=[],
                            outputs=["reports/08_infrastructure/security-design.md"]),
    "design-observability": dict(category="extension", model="sonnet", depends_on=[],
                                 outputs=["reports/08_infrastructure/observability-design.md"]),
    "design-disaster-recovery": dict(category="extension", model="sonnet", depends_on=[],
                                     outputs=["reports/08_infrastructure/disaster-recovery-design.md"]),
    "estimate-cost": dict(category="extension", model="sonnet", depends_on=[],
                          outputs=["reports/05_estimate/cost-summary.md"]),
    "estimate-token-cost": dict(category="extension", model="sonnet", depends_on=[],
                                outputs=["reports/05_estimate/token-cost-estimate.md"]),
}

_manifest_cache = {}


def plugin_root():
    """The nexus-architect checkout that ships the skills (env override wins)."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("NX_PLUGIN_ROOT")
    if env_root and os.path.isdir(env_root):
        return env_root
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_phase_manifest(plugin, root=None):
    """{phase_name: spec} in file order, extension tier appended for architect."""
    root = root or plugin_root()
    key = (plugin, root)
    if key in _manifest_cache:
        return _manifest_cache[key]
    path = os.path.join(root, PLUGINS[plugin]["manifest"])
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = parse_yaml(f.read())
    except OSError:
        data = {}
    phases = {}
    for name, spec in (data.get("phases") or {}).items():
        spec = dict(spec or {})
        spec.setdefault("category", "core")
        spec["outputs"] = _as_list(spec.get("outputs"))
        spec["depends_on"] = _as_list(spec.get("depends_on"))
        spec["conditions"] = _as_list(spec.get("conditions"))
        spec["tier"] = "core"
        phases[name] = spec
    if plugin == "architect":
        for name, spec in EXTENSION_PHASES.items():
            if name in phases:
                continue
            spec = dict(spec)
            spec.update(outputs=list(spec["outputs"]), depends_on=list(spec["depends_on"]),
                        conditions=[], tier="extension")
            phases[name] = spec
    _manifest_cache[key] = phases
    return phases


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v is not None]
    return [value]


# ------------------------------------------------------------------- project inputs
def load_progress(project_dir):
    """work/pipeline-progress.json as a dict, or None when absent/unreadable."""
    data = D.load_json(os.path.join(project_dir, "work", "pipeline-progress.json"))
    return data if isinstance(data, dict) else None


def normalize_progress(progress):
    """Make a hand-written registry safe to read.

    The registry is written by the agent mid-run, so the dashboard has to survive a
    half-written or loosely-shaped file rather than die on it: a phase recorded as a
    bare string (`"investigate": "completed"`) is read as that status, anything else
    unusable becomes an empty entry, and non-dict `options` / non-list `errors` are
    dropped instead of raising.
    """
    if not isinstance(progress, dict):
        return None
    phases = progress.get("phases")
    clean = {}
    if isinstance(phases, dict):
        for name, entry in phases.items():
            if isinstance(entry, dict):
                clean[name] = entry
            elif isinstance(entry, str):
                clean[name] = {"status": entry}
            else:
                clean[name] = {}
    out = dict(progress)
    out["phases"] = clean
    options = progress.get("options")
    out["options"] = options if isinstance(options, dict) else {}
    for key in ("errors", "warnings"):
        value = progress.get(key)
        out[key] = [str(v) for v in value] if isinstance(value, list) else (
            [str(value)] if value else [])
    return out


def detect_plugin(progress, project_dir, override=None):
    """Which pipeline this project is running: 'product' or 'architect'."""
    if override in PLUGINS:
        return override
    names = set((progress or {}).get("phases") or {})
    if names:
        scores = {p: len(names & set(load_phase_manifest(p))) for p in PLUGINS}
        best = max(scores, key=lambda p: scores[p])
        if scores[best]:
            return best
    if isinstance((progress or {}).get("gates"), dict):
        return "product"
    if os.path.isdir(os.path.join(project_dir, "reports", "00_core")):
        return "product"
    return "architect"


def _tree_mtime(path, limit=500):
    """Newest mtime of any file under a directory; None when it holds no files."""
    newest, seen = None, 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                stamp = os.path.getmtime(os.path.join(root, name))
            except OSError:
                continue
            newest = stamp if newest is None else max(newest, stamp)
            seen += 1
            if seen >= limit:
                return newest
    return newest


def resolve_output(project_dir, pattern, project_name=None):
    """(exists, mtime, resolved_path) for one declared output path.

    A directory counts as written only when it holds at least one file — an empty
    `reports/04_stories/` is the skill not having run, not an output. `{project}` and
    `{service}` placeholders and any literal `*` are globbed; the concrete path that
    matched is returned so the dashboard can open it.
    """
    rel = pattern.replace("{project}", project_name or "*").replace("{service}", "*")
    want_dir = rel.endswith("/")
    for path in sorted(glob.glob(os.path.join(project_dir, rel.rstrip("/")))):
        rel_path = os.path.relpath(path, project_dir)
        if os.path.isdir(path):
            newest = _tree_mtime(path)
            if newest is not None:
                return True, newest, rel_path
            continue
        if want_dir:
            continue
        try:
            return True, os.path.getmtime(path), rel_path
        except OSError:
            continue
    return False, 0.0, None


def load_cost(project_dir):
    """{phase: usd} from work/token-usage.json, joined "a+b" keys split evenly."""
    ledger = D.load_json(os.path.join(project_dir, "work", "token-usage.json"))
    if not isinstance(ledger, dict):
        return {}, 0.0, 0.0
    per_phase, unassigned = {}, 0.0
    for key, entry in (ledger.get("phases") or {}).items():
        cost = float((entry or {}).get("cost_usd") or 0.0)
        if key.startswith("_"):
            unassigned += cost
            continue
        names = [n for n in key.split("+") if n]
        for name in names:
            per_phase[name] = per_phase.get(name, 0.0) + cost / len(names)
    total = float(ledger.get("total_cost_usd") or 0.0)
    return per_phase, total, unassigned


def load_activity(project_dir, tail=80):
    """({phase: epoch}, latest_epoch) from the tail of work/token-usage.jsonl."""
    path = os.path.join(project_dir, "work", "token-usage.jsonl")
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-tail:]
    except OSError:
        return {}, 0.0
    per_phase, latest = {}, 0.0
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        stamp = D.parse_ts(rec.get("ts"))
        if not stamp:
            continue
        epoch = stamp.timestamp()
        latest = max(latest, epoch)
        names = set(rec.get("in_progress") or [])
        target = rec.get("attributed_to") or ""
        if target and not target.startswith("_"):
            names.update(n for n in target.split("+") if n)
        for name in names:
            per_phase[name] = max(per_phase.get(name, 0.0), epoch)
    return per_phase, latest


# ------------------------------------------------------------------- state derivation
def _conditions_ok(conditions, options):
    for cond in conditions:
        if cond == "scalardb_enabled" and not options.get("scalardb_enabled", True):
            return False
        if cond == "scalardb_disabled" and options.get("scalardb_enabled", True):
            return False
    return True


def derive_phase(name, spec, entry, project_dir, options, project_name,
                 costs, activity, now):
    """One phase's full state. The registry wins on status; files drive the bar."""
    outputs = []
    written = 0
    last_write = 0.0
    for pattern in spec.get("outputs") or []:
        exists, mtime, resolved = resolve_output(project_dir, pattern, project_name)
        outputs.append({"path": pattern, "exists": exists, "mtime": mtime,
                        "resolved": resolved})
        if exists:
            written += 1
            last_write = max(last_write, mtime)
    declared = len(outputs)

    recorded = (entry or {}).get("status")
    recorded = recorded if recorded in PHASE_STATUSES else None
    excluded = None
    if name in _as_list(options.get("skip_phases")):
        excluded = "option"
    elif not _conditions_ok(spec.get("conditions") or [], options):
        excluded = "condition"

    if recorded:
        status, source = recorded, "progress"
    elif excluded:
        status, source = "skipped", "condition"
    elif declared and written == declared:
        status, source = "completed", "derived"
    elif written:
        status, source = "in_progress", "derived"
    else:
        status, source = "pending", "derived"

    drift = None
    if source == "progress" and declared:
        if status == "completed" and written == 0:
            drift = "outputs-missing"
        elif status == "pending" and written == declared:
            drift = "outputs-present"

    last_activity = max(last_write, activity.get(name, 0.0))
    return {
        "name": name,
        "category": spec.get("category") or "core",
        "tier": spec.get("tier") or "core",
        "model": spec.get("model"),
        "optional": bool(spec.get("optional")),
        "rerunnable": bool(spec.get("rerunnable")),
        "standalone": bool(spec.get("standalone")),
        "gate": bool(spec.get("gate")),
        "depends_on": list(spec.get("depends_on") or []),
        "conditions": list(spec.get("conditions") or []),
        "status": status, "source": source, "excluded": excluded, "drift": drift,
        "outputs": outputs, "written": written, "declared": declared,
        "started_at": (entry or {}).get("started_at"),
        "completed_at": (entry or {}).get("completed_at"),
        "updated_at": (entry or {}).get("updated_at"),
        "note": (entry or {}).get("note"),
        "summary": (entry or {}).get("summary"),
        "cost_usd": costs.get(name),
        "last_activity": last_activity or None,
        "active": bool(last_activity and now - last_activity <= ACTIVE_WINDOW),
        "blocked_by": [],   # filled in by derive_all, once every status is known
        "runnable": False,
    }


def order_phases(manifest):
    """Dependency order, stable within the manifest's own order; cycles kept last."""
    remaining = list(manifest)
    placed, order = set(), []
    while remaining:
        progressed = False
        for name in list(remaining):
            deps = [d for d in manifest[name].get("depends_on") or [] if d in manifest]
            if all(d in placed for d in deps):
                order.append(name)
                placed.add(name)
                remaining.remove(name)
                progressed = True
        if not progressed:            # dependency cycle: keep the file order
            order.extend(remaining)
            break
    return order


def derive_all(project_dir, plugin=None, progress=None):
    """Everything the renderers need: phases, groups, summary, gate, next command."""
    raw = progress if progress is not None else load_progress(project_dir)
    progress = normalize_progress(raw)
    plugin = detect_plugin(progress, project_dir, plugin)
    manifest = load_phase_manifest(plugin)
    options = (progress or {}).get("options") or {}
    project_name = (progress or {}).get("project_name") or os.path.basename(
        os.path.abspath(project_dir))
    entries = ((progress or {}).get("phases") or {})
    costs, total_cost, unassigned_cost = load_cost(project_dir)
    activity, latest_activity = load_activity(project_dir)
    now = datetime.now(timezone.utc).timestamp()

    phases = {}
    for name in order_phases(manifest):
        phases[name] = derive_phase(name, manifest[name], entries.get(name), project_dir,
                                    options, project_name, costs, activity, now)

    # Registry entries for phases this plugin's manifest does not know (hand-written or
    # renamed) are still shown, so nothing recorded is silently dropped.
    for name, entry in entries.items():
        if name not in phases:
            phases[name] = derive_phase(name, {"category": "other", "tier": "other"},
                                        entry, project_dir, options, project_name,
                                        costs, activity, now)

    done = ("completed", "skipped")
    for state in phases.values():
        state["blocked_by"] = [d for d in state["depends_on"]
                               if d in phases and phases[d]["status"] not in done]
        state["runnable"] = (state["status"] in ("pending", "failed")
                             and not state["blocked_by"] and not state["excluded"])

    groups = []
    index = {}
    for name, state in phases.items():
        key = "extension" if state["tier"] == "extension" else state["category"]
        if key not in index:
            index[key] = {"key": key, "phases": []}
            groups.append(index[key])
        index[key]["phases"].append(state)

    counts = {s: 0 for s in PHASE_STATUSES}
    for state in phases.values():
        if state["tier"] == "core":
            counts[state["status"]] += 1
    core_total = sum(counts.values())
    summary = {
        "by_status": counts,
        "total": core_total,
        "completed": counts["completed"] + counts["skipped"],
        "total_cost_usd": total_cost,
        "unassigned_cost_usd": unassigned_cost,
        "latest_activity": latest_activity or None,
    }
    current = next((s["name"] for s in phases.values()
                    if s["tier"] == "core" and s["status"] == "in_progress"), None)
    # The suggested next phase prefers the required path: an optional phase (a greenfield
    # entry point, an on-demand skill) is runnable from the start and would otherwise
    # always win, which is not what "what do I run next" means mid-pipeline.
    runnable = [s["name"] for s in phases.values()
                if s["tier"] == "core" and s["runnable"]]
    nxt = next((n for n in runnable if not phases[n]["optional"]),
               runnable[0] if runnable else None)
    return {
        "plugin": plugin, "project": project_name, "project_dir": project_dir,
        "has_progress": progress is not None, "options": options,
        "phases": phases, "groups": groups, "summary": summary,
        "current": current, "next": nxt,
        "gate": read_gate(progress),
        "errors": (progress or {}).get("errors") or [],
        "warnings": (progress or {}).get("warnings") or [],
        "backlog": backlog_summary(project_dir),
        "updated_at": (progress or {}).get("updated_at"),
    }


def backlog_summary(project_dir):
    """(done, total) Issues from the backlog manifest, or None.

    A backlog that has not started — or a manifest that is malformed or half-written —
    must not take the pipeline view down with it, so every failure here is "no backlog
    line", never an exception.
    """
    path = os.path.join(project_dir, "reports", "backlog", "backlog-manifest.json")
    try:
        import backlog_status_data as B
        manifest = B.load_manifest(path)
        if manifest is None:
            return None
        _, _, states = B.derive_all(manifest)
        summary = B.overall_summary(manifest, states)
    except Exception:
        return None
    if not summary["issues_total"]:
        return None
    return summary["issues_done"], summary["issues_total"]


def read_gate(progress):
    """The product validation gate, or None (architect has no gate)."""
    gates = (progress or {}).get("gates")
    if not isinstance(gates, dict):
        return None
    entry = gates.get("validate-assumptions")
    if not isinstance(entry, dict):
        return None
    return {"verdict": entry.get("verdict") or "pending",
            "open_assumptions": _as_list(entry.get("open_assumptions"))}


# ------------------------------------------------------------------- rows & filtering
def flatten(state, collapsed=None, status_filter=None, group_filter=None,
            tier_filter=None):
    """Visible (row, depth, last_stack) in draw order — groups at depth 0, phases at 1.

    Rows are {"kind": "group"|"phase", ...}; the shapes the TUI and the one-shot
    renderer both walk. Empty groups (everything filtered out) are dropped.
    """
    collapsed = collapsed or set()
    rows = []
    groups = [g for g in state["groups"]
              if not group_filter or g["key"] == group_filter]
    if tier_filter == "core":
        groups = [g for g in groups if g["key"] != "extension"]
    elif tier_filter == "extension":
        groups = [g for g in groups if g["key"] == "extension"]
    visible = []
    for group in groups:
        phases = [p for p in group["phases"]
                  if not status_filter or p["status"] == status_filter]
        if phases:
            visible.append((group, phases))
    for group, phases in visible:
        header = {"kind": "group", "key": group["key"], "group": group,
                  "phases": phases}
        rows.append((header, 0, (True,)))
        if group["key"] in collapsed:
            continue
        for pi, phase in enumerate(phases):
            row = {"kind": "phase", "key": phase["name"], "phase": phase}
            # The group header carries no connector of its own, so the first stack slot
            # is always "last" — it renders as blank instead of a dangling pipe.
            rows.append((row, 1, (True, pi == len(phases) - 1)))
    return rows


def group_counts(group):
    """(completed_or_skipped, total) for a group header."""
    total = len(group["phases"])
    done = sum(1 for p in group["phases"]
               if p["status"] in ("completed", "skipped"))
    return done, total


def output_bar(phase, width=4):
    """A tiny [====] meter of declared outputs written; blank when nothing declared."""
    if not phase["declared"]:
        return " " * (width + 2)
    filled = int(round(width * phase["written"] / float(phase["declared"])))
    return "[%s%s]" % ("=" * filled, "." * (width - filled))


def rel_time(epoch, now=None):
    """'28s' / '4m' / '2h' / '3d' — the age of an activity stamp."""
    if not epoch:
        return None
    delta = max(0, int((now or datetime.now(timezone.utc).timestamp()) - epoch))
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if delta >= size:
            return "%d%s" % (delta // size, unit)
    return "%ds" % delta


# ------------------------------------------------------------------- actions
def actions_for(state, phase):
    """(label, command) entries for the action menu / default `c` copy."""
    prefix = PLUGINS[state["plugin"]]["prefix"]
    orchestrator = PLUGINS[state["plugin"]]["orchestrator"]
    name = phase["name"]
    out = [("run phase", "%s%s" % (prefix, name))]
    if state["plugin"] == "architect":
        out += [("resume from here", "%s --resume-from=%s" % (orchestrator, name)),
                ("rerun from here", "%s --rerun-from=%s" % (orchestrator, name))]
    else:
        out += [("resume pipeline", orchestrator)]
        if phase["name"] != "adapt-change":
            out += [("adapt to a change", "%sadapt-change --change=\"...\"" % prefix)]
    if phase["status"] == "failed" or phase["blocked_by"]:
        dep = phase["blocked_by"][0] if phase["blocked_by"] else name
        out += [("run blocking phase", "%s%s" % (prefix, dep))]
    existing = [o["resolved"] or o["path"] for o in phase["outputs"] if o["exists"]]
    if existing:
        out += [("open output", existing[0])]
    return out


def default_action(state, phase):
    """The status-appropriate default command (the `c` quick-copy key)."""
    acts = actions_for(state, phase)
    if not acts:
        return None
    if phase["blocked_by"]:
        prefer = "run blocking phase"
    elif phase["status"] in ("completed", "skipped"):
        prefer = "open output"
    else:
        prefer = "run phase"
    for label, cmd in acts:
        if label == prefer:
            return (label, cmd)
    return acts[0]


def phase_context(state, phase, T):
    """One-line context prefix for the ask feature: what the user is looking at."""
    bits = ["%s %s" % (state["plugin"], phase["name"]), phase["status"]]
    if phase["declared"]:
        bits.append("%d/%d %s" % (phase["written"], phase["declared"], T["outputs"]))
    if phase["blocked_by"]:
        bits.append("%s %s" % (T["blocked_by"], ", ".join(phase["blocked_by"])))
    return " / ".join(bits)
