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

The registry wins on status, with two exceptions. `pending` is the value every phase is
born with, so an entry still sitting there while its declared outputs exist on disk is a
skill that forgot to stamp itself, not a phase that never ran — the filesystem wins and
the status is derived. And both pipelines write this one registry, keyed by bare phase
name, so an entry under a name both manifests define (`map-domains`, `design-api`,
`create-domain-story`, `report`) is only trusted to say *this* phase finished when this
phase's own outputs exist to corroborate it. The filesystem also drives the output bar,
and raises a drift flag whenever the two disagree (claimed completed with nothing written,
every output present while still recorded pending, or that shared-name ambiguity). Phases
with no registry entry — notably the architect manual extension tier — are derived from
the filesystem alone.

`completed` is not permanent: a phase whose upstream was rerun or hand-edited afterwards
is reported as **stale**, and the invalidation propagates down the dependency graph, so
fixing an early phase visibly un-completes everything derived from it instead of leaving
a tree that claims to be finished.

product and architect are two separate pipelines, and code generation is neither — so a
state describes one `plugin` and one `section` ("pipeline" or "codegen"), which is what
the dashboard's Product / Architect / Code Generation tabs each ask for. derive_codegen
merges both plugins' codegen sections into the single tree that tab shows.

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
from api_style_decisions import MAX_DOCUMENT_BYTES, validate_document  # noqa: E402
from graphql_design_manifest import load_and_validate  # noqa: E402
import token_cost_data as D  # noqa: E402  (display helpers + load_json/parse_ts)

PHASE_STATUSES = ["pending", "in_progress", "completed", "failed", "skipped"]

# `stale` is not a registry status — no skill ever writes it. It is derived (see
# mark_stale) and shown in the status column in place of `completed`, so the displayed
# set is one wider than the recorded set.
STALE = "stale"
DISPLAY_STATUSES = PHASE_STATUSES + [STALE]

# Phase-status glyphs. Same rules as the backlog set: Ambiguous/Neutral width only, and
# the ASCII table engages automatically in ASCII mode.
PHASE_GLYPHS_UNICODE = {"pending": "○", "in_progress": "◐", "completed": "●",
                        "failed": "✗", "skipped": "–", "current": "▶", "drift": "↯",
                        "active": "•", "gate": "G", "stale": "↺"}
PHASE_GLYPHS_ASCII = {"pending": "o", "in_progress": "~", "completed": "*",
                      "failed": "x", "skipped": "-", "current": ">", "drift": "!",
                      "active": ".", "gate": "G", "stale": "@"}
PG = PHASE_GLYPHS_ASCII if D.ASCII_ONLY else PHASE_GLYPHS_UNICODE

PHASE_STYLE = {"pending": "dim", "in_progress": "warn", "completed": "accent",
               "failed": "alert", "skipped": "dim", "stale": "warn"}

# A phase counts as "running now" when the project produced tokens or wrote one of its
# outputs within this many seconds.
ACTIVE_WINDOW = 300

# An upstream output has to be this many seconds newer than the phase's own newest output
# before it counts as an upstream change. It only absorbs same-run write ordering (a
# dependency's directory mtime settling a moment after the phase that consumed it); a
# real rerun or a hand edit is minutes or hours newer, never seconds.
STALE_GRACE = 5.0

PS_LABELS = {
    "en": {
        "title": "Pipeline Progress", "phases": "Phases", "done": "done",
        "tab_product": "Product", "tab_architect": "Architect",
        "tab_codegen": "Code Generation",
        "title_product": "Product Pipeline", "title_architect": "Architect Pipeline",
        "title_codegen": "Code Generation",
        "no_product": "the product pipeline has not run in this project",
        "no_architect": "the architect pipeline has not run in this project",
        "no_codegen": "no code-generation phase is available yet",
        "no_progress": "no work/pipeline-progress.json",
        "status": "status",
        "outputs": "outputs", "declared": "declared outputs", "deps": "depends on",
        "blocked_by": "waiting on", "model": "model", "cost": "cost",
        "gate": "gate", "gate_of": "%s gate", "verdict": "verdict",
        "open_assumptions": "open assumptions",
        "next": "next", "current": "running", "active": "active",
        "ago": "%s ago", "never": "no activity recorded",
        "started": "started", "completed_at": "completed", "updated": "updated",
        "note": "note", "summary": "summary", "errors": "errors", "warnings": "warnings",
        "drift_missing": "recorded completed, but no declared output exists",
        "drift_present": "every declared output exists, but the registry was never "
                         "stamped — completed here is derived from the files",
        "drift_shared": "both pipelines define this phase name and the registry keys "
                        "phases by name, so the recorded status may be the other "
                        "pipeline's — nothing is written here, so it is not read as done",
        "stale_upstream": "upstream changed after this phase finished: %s",
        "stale_inherited": "upstream is stale: %s",
        "stale_changed": "changed",
        "stale_hint": "rerun this phase to pick the change up",
        "source": "source", "source_progress": "progress registry",
        "source_derived": "derived from outputs", "source_condition": "condition",
        "optional": "optional", "rerunnable": "rerunnable", "standalone": "standalone",
        "gate_phase": "validation gate", "skipped_option": "excluded by skip_phases",
        "skipped_condition": "excluded by project options",
        "backlog": "backlog", "issues_done": "%d/%d issues done",
        "total_cost": "total cost", "unassigned": "unassigned",
        "empty": "nothing to show", "unknown_phase": "unknown phase: %s",
        "filter": "filter", "failed_phases": "failed",
        "no_match": "no phase matches %s", "clear_filter": "press f to clear it",
        "known_phases": "phases in the %s pipeline: %s",
        "no_extension_tier": "the product pipeline has no manual extension tier",
        "keys": " ^v/jk select | <> fold | Enter actions | Tab view | a ask"
                " | f filter | o open | c copy | r refresh",
        "group_requirements": "Requirements", "group_investigation": "Investigation",
        "group_analysis": "Analysis", "group_evaluation": "Evaluation",
        "group_design": "Design", "group_review": "Review", "group_reporting": "Reporting",
        "group_extension": "Extensions (manual tier)", "group_core": "Product Core",
        "group_validation": "Validation Gate", "group_ux": "UX Foundation",
        "group_spec": "Specification", "group_codegen": "Code Generation",
        "group_domain": "Domain & API", "group_quality": "Quality & NFR",
        "group_adaptation": "Adaptation",
        "group_product": "Product (frontend)",
        "group_architect": "Architect (services & infrastructure)",
        "group_other": "Recorded outside the manifest",
        "help_glyphs": "pipeline glyphs",
        "help_outputs": "declared outputs that exist on disk",
        "help_drift": "drift: the registry and the filesystem disagree",
        "help_stale": "stale: an upstream phase changed after this one finished",
        "help_active": "active: tokens or an output written in the last 5 minutes",
        "help_optional": "optional phase (not part of the required path)",
        "ask_free": "free input...",
        "ask_why": "Why is this phase still %s?",
        "ask_next": "What should I run next, and why?",
        "ask_summary": "Summarize this phase's outputs.",
        "ask_stale": "Which upstream change invalidated this phase, and what has to "
                     "be rerun?",
    },
    "ja": {
        "title": "パイプライン進捗", "phases": "フェーズ", "done": "完了",
        "tab_product": "プロダクト", "tab_architect": "アーキテクト",
        "tab_codegen": "コード生成",
        "title_product": "プロダクトパイプライン",
        "title_architect": "アーキテクトパイプライン",
        "title_codegen": "コード生成",
        "no_product": "このプロジェクトでは product パイプラインは実行されていません",
        "no_architect": "このプロジェクトでは architect パイプラインは実行されていません",
        "no_codegen": "実行可能なコード生成フェーズがまだありません",
        "no_progress": "work/pipeline-progress.json がありません",
        "status": "状態",
        "outputs": "出力", "declared": "宣言された出力", "deps": "依存",
        "blocked_by": "未充足の依存", "model": "モデル", "cost": "コスト",
        "gate": "ゲート", "gate_of": "%sのゲート", "verdict": "判定",
        "open_assumptions": "未検証の前提",
        "next": "次", "current": "実行中", "active": "稼働中",
        "ago": "%s前", "never": "稼働記録なし",
        "started": "開始", "completed_at": "完了", "updated": "更新",
        "note": "メモ", "summary": "要約", "errors": "エラー", "warnings": "警告",
        "drift_missing": "completed 記録だが宣言された出力が1つも無い",
        "drift_present": "宣言された出力は全て存在するがレジストリが未更新 — "
                         "ここでの completed は実ファイルから導出",
        "drift_shared": "このフェーズ名は両パイプラインが定義しており、レジストリは"
                        "フェーズ名をキーにしているため記録された状態はもう一方の"
                        "ものかもしれない — 出力が無いので完了とは読まない",
        "stale_upstream": "このフェーズの完了後に上流が更新された: %s",
        "stale_inherited": "上流が stale: %s",
        "stale_changed": "更新",
        "stale_hint": "このフェーズを再実行すると変更が反映される",
        "source": "情報源", "source_progress": "進捗レジストリ",
        "source_derived": "出力から導出", "source_condition": "条件",
        "optional": "任意", "rerunnable": "再実行可", "standalone": "独立実行",
        "gate_phase": "検証ゲート", "skipped_option": "skip_phases で除外",
        "skipped_condition": "プロジェクト設定で除外",
        "backlog": "バックログ", "issues_done": "Issue %d/%d 完了",
        "total_cost": "合計コスト", "unassigned": "未割当",
        "empty": "表示するものがありません", "unknown_phase": "存在しないフェーズ: %s",
        "filter": "フィルタ", "failed_phases": "失敗",
        "no_match": "%s に一致するフェーズはありません", "clear_filter": "f で解除",
        "known_phases": "%s パイプラインのフェーズ: %s",
        "no_extension_tier": "product パイプラインに手動拡張ティアはありません",
        "keys": " ^v/jk 選択 | <> 開閉 | Enter アクション | Tab ビュー | a 質問"
                " | f フィルタ | o 開く | c コピー | r 更新",
        "group_requirements": "要件定義", "group_investigation": "調査",
        "group_analysis": "分析", "group_evaluation": "評価",
        "group_design": "設計", "group_review": "レビュー", "group_reporting": "レポート",
        "group_extension": "拡張ティア (手動実行)", "group_core": "プロダクトコア",
        "group_validation": "検証ゲート", "group_ux": "UX 基盤",
        "group_spec": "仕様化", "group_codegen": "コード生成",
        "group_domain": "ドメイン & API", "group_quality": "品質 & NFR",
        "group_adaptation": "変更適応",
        "group_product": "プロダクト (フロントエンド)",
        "group_architect": "アーキテクト (サービス & インフラ)",
        "group_other": "マニフェスト外の記録",
        "help_glyphs": "パイプラインの記号",
        "help_outputs": "宣言された出力のうち実在するもの",
        "help_drift": "ドリフト: 進捗レジストリと実ファイルが食い違っている",
        "help_stale": "stale: 完了後に上流フェーズが更新された (再実行が必要)",
        "help_active": "稼働中: 直近5分にトークン消費または出力の書き込みがあった",
        "help_optional": "任意フェーズ (必須の経路ではない)",
        "ask_free": "自由入力...",
        "ask_why": "このフェーズがまだ %s なのはなぜ？",
        "ask_next": "次に実行すべきことは？その理由は？",
        "ask_summary": "このフェーズの出力を要約して。",
        "ask_stale": "どの上流の変更でこのフェーズは無効になった？何を再実行すべき？",
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
# dashboard can derive their state from the filesystem when the registry is silent, and
# are kept in step with each skill's own Output table — every file the skill promises, so
# the output bar measures real progress instead of collapsing to 0/1.
#
# Two members declare nothing on purpose: `generate-docs` writes into the target
# project's own source tree, which this tool cannot locate, and `report-token-cost` only
# renders to a terminal. Both are listed so the tier is complete, and both can only take
# a status from the registry.
EXTENSION_PHASES = {
    "investigate-security": dict(category="extension", model="sonnet", depends_on=["investigate"],
                                 outputs=["reports/before/{project}/security-assessment.md"]),
    "select-scalardb-edition": dict(category="extension", model="sonnet", depends_on=[],
                                    outputs=["reports/03_design/scalardb-edition-selection.md"]),
    "design-scalardb-analytics": dict(category="extension", model="opus", depends_on=["design-scalardb"],
                                      outputs=["reports/03_design/scalardb-analytics-design.md"]),
    "design-implementation": dict(category="extension", model="opus",
                                  depends_on=["design-api", "design-graphql"],
                                  outputs=["reports/06_implementation/api-layer-spec.md",
                                           "reports/06_implementation/domain-services-spec.md",
                                           "reports/06_implementation/repository-interfaces-spec.md",
                                           "reports/06_implementation/value-objects-spec.md",
                                           "reports/06_implementation/exception-mapping-spec.md"]),
    "generate-test-specs": dict(category="extension", model="sonnet", depends_on=["design-implementation"],
                                outputs=["reports/07_test-specs/contract-test-specs.md",
                                         "reports/07_test-specs/unit-test-specs.md",
                                         "reports/07_test-specs/integration-test-specs.md",
                                         "reports/07_test-specs/performance-test-specs.md",
                                         "reports/07_test-specs/bdd-scenarios/"]),
    "generate-scalardb-code": dict(category="extension", model="sonnet", depends_on=["design-implementation"],
                                   outputs=["generated/*/src/main/java/",
                                            "generated/*/build.gradle",
                                            "generated/*/scalardb.properties",
                                            "generated/*/Dockerfile"]),
    "generate-api-code": dict(category="extension", model="opus", depends_on=["design-implementation"],
                              conditions=["api_style_rest"],
                              outputs=["generated/*/src/main/java/",
                                       "reports/06_implementation/api-contract-map.md",
                                       "reports/06_implementation/api-contract-map.json"]),
    # Conditioned like its design phase: `design-graphql` being *skipped* satisfies the
    # dependency (skipped counts as done), so without this the codegen view would offer
    # GraphQL generation on a project whose canonical decision is REST-only.
    "generate-graphql-code": dict(category="extension", model="opus",
                                  depends_on=["design-implementation", "design-graphql"],
                                  conditions=["api_style_graphql"],
                                  outputs=["reports/06_implementation/graphql-code-generation.md"]),
    "generate-contract-tests": dict(category="extension", model="sonnet",
                                    depends_on=["design-implementation"],
                                    outputs=["generated/*/src/test/java/",
                                             "reports/07_test-specs/contract-test-coverage.md"]),
    "generate-infra-code": dict(category="extension", model="sonnet", depends_on=["design-infrastructure"],
                                outputs=["generated/infrastructure/k8s/",
                                         "generated/infrastructure/helm/",
                                         "generated/infrastructure/terraform/"]),
    "generate-docs": dict(category="extension", model="sonnet", depends_on=[], outputs=[]),
    # Verification runs against whatever code exists — a generated scaffold or a backlog-delivered
    # source tree — so it declares no dependency on a particular codegen phase.
    "verify-implementation": dict(category="extension", model="opus", depends_on=["design-implementation"],
                                  outputs=["reports/09_verification/design-code-conformance.md",
                                           "reports/09_verification/design-code-conformance.json"]),
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
                          outputs=["reports/05_estimate/cost-summary.md",
                                   "reports/05_estimate/infrastructure-detail.md",
                                   "reports/05_estimate/scalardb-sizing.md"]),
    "estimate-token-cost": dict(category="extension", model="sonnet", depends_on=[],
                                outputs=["reports/05_estimate/token-cost-estimate.md"]),
    "report-token-cost": dict(category="extension", model="sonnet", depends_on=[], outputs=[]),
}

# Code generation is its own dashboard tab, not a step of either pipeline. These phases
# emit runnable code — or the documentation for code that exists — into the target
# project rather than a design report, they are run by hand after the pipeline that
# designed them, and they are the same kind of work whichever plugin they belong to.
# Naming them here is what takes them out of their plugin's pipeline tab and collects
# them, both plugins together, in the codegen tab.
#
# `generate-test-specs` deliberately stays in the architect pipeline: it writes
# specifications under reports/, not code.
CODEGEN_PHASES = {
    "architect": ("generate-scalardb-code", "generate-api-code", "generate-graphql-code",
                  "generate-contract-tests",
                  "generate-infra-code", "generate-docs"),
    "product": ("generate-frontend",),
}

SECTIONS = ("pipeline", "codegen")

# Tab order for anything that shows both plugins side by side.
PLUGIN_ORDER = ("product", "architect")

_manifest_cache = {}


def plugin_root():
    """The nexus-architect checkout that ships the skills (env override wins)."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("NX_PLUGIN_ROOT")
    if env_root and os.path.isdir(env_root):
        return env_root
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_phase_manifest(plugin, root=None):
    """{phase_name: spec} in file order, extension tier appended for architect.

    Every spec carries a `section` — "pipeline" or "codegen" — which is what splits the
    manifest across the dashboard's tabs (see CODEGEN_PHASES).
    """
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
        # Artefacts this phase writes that other phases also write (the ADR log, the domain
        # event catalog). Declared so the writer is known, but deliberately NOT part of
        # `outputs`: they are not counted toward the bar and their mtime is not this phase's
        # last_write — a later append by another skill must not mark this phase's dependents
        # stale, and a phase completed before the shared artefact existed must not drop below
        # full.
        spec["shared_outputs"] = _as_list(spec.get("shared_outputs"))
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
                        conditions=_as_list(spec.get("conditions")), tier="extension")
            phases[name] = spec
    codegen = set(CODEGEN_PHASES.get(plugin, ()))
    for name, spec in phases.items():
        spec["section"] = "codegen" if name in codegen else "pipeline"
    _manifest_cache[key] = phases
    return phases


def exclusive_phases(plugin, root=None):
    """The phase names only this plugin's manifest defines.

    The two manifests share several names (`map-domains`, `design-api`, `report`,
    `create-domain-story`, ...), so a registry entry under a shared name says nothing
    about which pipeline wrote it. Only the names one manifest alone defines can settle
    that, which is what tells the dashboard whether a plugin's tab has anything behind it.
    """
    own = set(load_phase_manifest(plugin, root))
    for other in PLUGINS:
        if other != plugin:
            own -= set(load_phase_manifest(other, root))
    return own


def shared_phase_names(root=None):
    """The phase names more than one plugin's manifest defines.

    The inverse of exclusive_phases, and the reason it exists: both pipelines write the
    same `work/pipeline-progress.json` and it keys phases by bare name, so an entry under
    one of these names carries no evidence of which pipeline wrote it. `derive_phase`
    refuses to read such an entry as this plugin's phase being finished.
    """
    seen, shared = set(), set()
    for plugin in PLUGINS:
        names = set(load_phase_manifest(plugin, root))
        shared |= seen & names
        seen |= names
    return shared


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


def resolve_ledger_key(key, plugin, shared):
    """(phase_name, kind) for one bucket name written by the token-usage hook.

    Buckets under a name both manifests define are namespaced `<plugin>:<phase>`, so
    the two pipelines' spend on `map-domains` stays separable. `kind` is:

    - `mine`      — this view's phase; attribute it.
    - `other`     — the neighbouring pipeline's phase. Not this view's to show, and not
                    unassigned either: it is attributed on its own tab.
    - `ambiguous` — a bare bucket under a shared name, written before the hook carried
                    the plugin. No longer attributable to either side, so it is reported
                    as unassigned instead of charged to whichever tab happens to be open.
    """
    prefix, sep, rest = key.partition(":")
    if sep and prefix in PLUGINS:
        return rest, "mine" if (plugin is None or prefix == plugin) else "other"
    if plugin and key in shared:
        return key, "ambiguous"
    return key, "mine"


def load_cost(project_dir, plugin=None):
    """{phase: usd} from work/token-usage.json, joined "a+b" keys split evenly."""
    ledger = D.load_json(os.path.join(project_dir, "work", "token-usage.json"))
    if not isinstance(ledger, dict):
        return {}, 0.0, 0.0
    shared = shared_phase_names()
    per_phase, unassigned = {}, 0.0
    for key, entry in (ledger.get("phases") or {}).items():
        cost = float((entry or {}).get("cost_usd") or 0.0)
        if key.startswith("_"):
            unassigned += cost
            continue
        names = [n for n in key.split("+") if n]
        for name in names:
            resolved, kind = resolve_ledger_key(name, plugin, shared)
            if kind == "mine":
                per_phase[resolved] = per_phase.get(resolved, 0.0) + cost / len(names)
            elif kind == "ambiguous":
                unassigned += cost / len(names)
    total = float(ledger.get("total_cost_usd") or 0.0)
    return per_phase, total, unassigned


def load_activity(project_dir, tail=80, plugin=None):
    """({phase: epoch}, latest_epoch) from the tail of work/token-usage.jsonl.

    The records carry the same bucket names as the ledger, so they resolve the same
    way — the neighbouring pipeline's activity must not light up this view's phase.
    """
    path = os.path.join(project_dir, "work", "token-usage.jsonl")
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-tail:]
    except OSError:
        return {}, 0.0
    shared = shared_phase_names()
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
            resolved, kind = resolve_ledger_key(name, plugin, shared)
            if kind == "mine":
                per_phase[resolved] = max(per_phase.get(resolved, 0.0), epoch)
    return per_phase, latest


# ------------------------------------------------------------------- state derivation
def _stamp(value):
    """An ISO timestamp from the registry as an epoch, 0.0 when unusable."""
    parsed = D.parse_ts(value) if value else None
    return parsed.timestamp() if parsed else 0.0


def _conditions_ok(conditions, options):
    """Whether a phase's declared conditions hold.

    `scalardb_enabled` defaults to true (ScalarDB is the default path); every other
    condition **fails closed** — an option nobody set does not enable the phase. A new
    condition added to either manifest therefore needs someone to set its option, or to be
    derived like `api_style_graphql` / `api_style_rest` in canonical_api_style_options().
    """
    for cond in conditions:
        if cond == "scalardb_enabled" and not options.get("scalardb_enabled", True):
            return False
        if cond == "scalardb_disabled" and options.get("scalardb_enabled", True):
            return False
        if cond not in ("scalardb_enabled", "scalardb_disabled") and not options.get(cond, False):
            return False
    return True


STYLE_CONDITIONS = ("api_style_graphql", "api_style_rest")


def canonical_api_style_options(project_dir, options):
    """Derive per-style enablement from the canonical API-style contract when present.

    The progress option is retained only as a pre-design/legacy fallback. Invalid canonical
    input marks the conditional phases failed (fail closed against silently skipping GraphQL design)
    and returns an actionable error.

    The two styles are not symmetric when the contract is **absent**. `api_style_rest`
    defaults to true because REST codegen predates this artifact: every project that never
    ran the current `design-api` would otherwise lose `generate-api-code` from its codegen
    view. GraphQL has no such history, so an absent contract leaves it to the legacy option
    — which is normally unset, and unset means not selected.
    """
    effective = dict(options)
    effective.setdefault("api_style_rest", True)
    path = os.path.join(project_dir, "reports", "03_design", "api-style-decisions.json")
    if not os.path.isfile(path):
        return effective, [], []
    try:
        if os.path.getsize(path) > MAX_DOCUMENT_BYTES:
            return _invalid_api_style(
                effective,
                ["invalid canonical API-style decision: input exceeds %d bytes" %
                 MAX_DOCUMENT_BYTES])
    except OSError as exc:
        return _invalid_api_style(effective, ["invalid canonical API-style decision: %s" % exc])
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError) as exc:
        return _invalid_api_style(effective, ["invalid canonical API-style decision: %s" % exc])

    repository_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    okf_root = os.path.join(repository_root, "knowledge", "okf-scalardb-scalardl", "okf")
    errors = validate_document(document, project_dir=project_dir, okf_root=okf_root)
    if errors:
        return _invalid_api_style(effective, ["invalid canonical API-style decision: %s" % error
                                              for error in errors])

    styles = [surface["selected_style"] for surface in document["surfaces"]]
    selected = any(style in ("graphql", "hybrid") for style in styles)
    warnings = []
    copied = options.get("api_style_graphql")
    if isinstance(copied, bool) and copied != selected:
        warnings.append(
            "ignored stale options.api_style_graphql=%s; canonical API-style decision is %s" %
            (str(copied).lower(), str(selected).lower()))
    effective["api_style_graphql"] = selected
    # `graphql` is the one style that carries no REST surface; every other value the
    # validator admits — rest, hybrid, grpc, asyncapi — is served by the REST/API generator.
    effective["api_style_rest"] = any(style != "graphql" for style in styles)
    if selected:
        manifest_errors = load_and_validate(project_dir, document)
        if manifest_errors:
            effective["_invalid_conditions"] = ["api_style_graphql"]
            return effective, manifest_errors, warnings
    return effective, [], warnings


def _invalid_api_style(effective, errors):
    """A decision nobody can read enables nothing: fail both style conditions closed."""
    for condition in STYLE_CONDITIONS:
        effective[condition] = True
    effective["_invalid_conditions"] = list(STYLE_CONDITIONS)
    return effective, errors, []


def derive_phase(name, spec, entry, project_dir, options, project_name,
                 costs, activity, now, plugin=None):
    """One phase's full state. The registry wins on status; files drive the bar."""
    outputs = []
    written = 0
    last_write = 0.0
    # `conditional_outputs` holds "<condition>:<path>" entries — a file the skill writes only
    # when the project's options say so. Counting one the run will never produce pins the
    # phase below full forever, which reads as unfinished rather than as nothing to write.
    declared_patterns = list(spec.get("outputs") or [])
    for declaration in spec.get("conditional_outputs") or []:
        condition, _, pattern = str(declaration).partition(":")
        if pattern and _conditions_ok([condition], options):
            declared_patterns.append(pattern)
    for pattern in declared_patterns:
        exists, mtime, resolved = resolve_output(project_dir, pattern, project_name)
        outputs.append({"path": pattern, "exists": exists, "mtime": mtime,
                        "resolved": resolved})
        if exists:
            written += 1
            last_write = max(last_write, mtime)
    declared = len(outputs)

    recorded = (entry or {}).get("status")
    recorded = recorded if recorded in PHASE_STATUSES else None
    # An entry that names its own pipeline settles the shared-name question outright:
    # the neighbour's entry is not this phase's status at all, whatever it says.
    owner = (entry or {}).get("plugin")
    if owner in PLUGINS and plugin in PLUGINS and owner != plugin:
        recorded, entry = None, None
    condition_error = any(
        condition in _as_list(options.get("_invalid_conditions"))
        for condition in spec.get("conditions") or [])
    excluded = None
    if condition_error:
        excluded = "condition-error"
    elif name in _as_list(options.get("skip_phases")):
        excluded = "option"
    elif not _conditions_ok(spec.get("conditions") or [], options):
        excluded = "condition"

    # `pending` is the registry's initial value, not a claim: every phase starts there and
    # only leaves it if a skill remembers to stamp itself. Files on disk are evidence that
    # it ran, so they outrank an entry still sitting at the default. Every other recorded
    # status is a statement some skill actually made, and keeps its authority.
    unstamped = recorded == "pending" and written > 0

    # A handful of phase names live in both manifests (`map-domains`, `design-api`,
    # `create-domain-story`, `report`) and the registry keys phases by bare name, so a
    # `completed` entry under one of them may be the *other* pipeline's phase. An entry
    # that names its own `plugin` has already been resolved above; this is the fallback
    # for one that does not. When this phase declares outputs and none of them exist, the
    # entry has nothing corroborating it here: read it as the neighbour's stamp and derive
    # from the filesystem instead. `in_progress` is deliberately exempt — the registry is
    # the only thing that can say a phase is running, and a running phase legitimately has
    # nothing written yet. A recorded `skipped` is only suspect when this project gives no
    # reason to skip it.
    ambiguous = (
        not owner
        and name in shared_phase_names()
        and declared and written == 0
        and (recorded == "completed" or (recorded == "skipped" and not excluded)))

    if condition_error:
        status, source = "failed", "condition"
    elif recorded and not unstamped and not ambiguous:
        status, source = recorded, "progress"
    elif excluded:
        status, source = "skipped", "condition"
    elif declared and written == declared:
        status, source = "completed", "derived"
    elif written:
        status, source = "in_progress", "derived"
    else:
        status, source = "pending", "derived"

    # Drift is judged against what the registry *recorded*, not against the status shown:
    # the unstamped case is exactly a disagreement, so resolving it in the filesystem's
    # favour must not also hide it.
    drift = None
    if recorded and declared:
        if ambiguous:
            drift = "shared-name"
        elif recorded == "completed" and written == 0:
            drift = "outputs-missing"
        elif recorded == "pending" and written == declared:
            drift = "outputs-present"

    last_activity = max(last_write, activity.get(name, 0.0))
    # When the phase last produced something, for the upstream-change comparison. Files
    # are the truth; the registry stamp stands in only for a phase that declares no
    # inspectable output at all (generate-docs writes into the target project's own
    # tree). A phase that declares outputs and wrote none is left without a timestamp:
    # that is drift, and a claim already contradicted by the filesystem is no basis for
    # deciding what it is older than.
    finished_at = last_write or (0.0 if declared else
                                 _stamp((entry or {}).get("completed_at"))
                                 or _stamp((entry or {}).get("updated_at")))
    return {
        "name": name,
        "plugin": plugin,
        "category": spec.get("category") or "core",
        "tier": spec.get("tier") or "core",
        "section": spec.get("section") or "pipeline",
        # The group header this phase is filed under; set by whoever builds the groups.
        "group": None,
        "model": spec.get("model"),
        "optional": bool(spec.get("optional")),
        "rerunnable": bool(spec.get("rerunnable")),
        "standalone": bool(spec.get("standalone")),
        "gate": bool(spec.get("gate")),
        "depends_on": list(spec.get("depends_on") or []),
        "conditions": list(spec.get("conditions") or []),
        "status": status, "source": source, "excluded": excluded, "drift": drift,
        # `stale` and the display status are filled in by mark_stale, once every phase's
        # timestamp is known.
        "stale": False, "stale_by": [], "stale_inherited": [], "stale_at": None,
        "display_status": status,
        "last_write": last_write or None, "finished_at": finished_at or None,
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


def mark_stale(phases, grace=STALE_GRACE):
    """Invalidate every `completed` phase an upstream change has overtaken.

    Fixing an earlier phase does not un-write the reports the later ones already
    produced, so nothing in the registry ever contradicts itself — `completed` simply
    stays `completed`, and the tree keeps claiming the project is finished from work
    that no longer reflects its own inputs. That is what this pass corrects.

    A completed phase is stale when a direct dependency **wrote an output after it
    finished** (a rerun, or a hand edit of the report), or when that dependency is itself
    stale — so a single edit at the top of the pipeline invalidates the whole chain below
    it in one topological sweep. `phases` must therefore be in dependency order, which is
    what order_phases produces.

    Deliberately not stale: a phase whose dependency never ran or is excluded (there is
    no newer input to miss), and one with no timestamp to compare (a foreign or
    undeclared output tree) — an unknowable answer is left as recorded rather than
    guessed at.
    """
    for state in phases.values():
        if state["status"] != "completed" or state["excluded"]:
            continue
        own = state["finished_at"]
        if not own:
            continue
        newer, inherited, newest = [], [], 0.0
        for dep in state["depends_on"]:
            up = phases.get(dep)
            if up is None or up["excluded"] or up["status"] in ("skipped", "pending"):
                continue
            # Only real writes invalidate: an upstream registry stamp says when it was
            # recorded, not that the artefact this phase read has actually changed.
            up_write = up["last_write"] or 0.0
            if up_write > own + grace:
                newer.append(dep)
                newest = max(newest, up_write)
            elif up["stale"]:
                inherited.append(dep)
                newest = max(newest, up["stale_at"] or 0.0)
        if not newer and not inherited:
            continue
        state.update(stale=True, stale_by=newer, stale_inherited=inherited,
                     stale_at=newest or None, display_status=STALE)
    return phases


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


def derive_all(project_dir, plugin=None, progress=None, section="pipeline"):
    """Everything the renderers need: phases, groups, summary, gate, next command.

    `plugin` picks which pipeline is being described — the dashboard shows product and
    architect as separate tabs, so it always names one rather than letting detection
    choose. `section` picks which half of that manifest: "pipeline" (the design phases,
    the default) or "codegen" (the code-generation phases, which have their own tab).

    Both sections are derived together first — dependencies and staleness cross the
    boundary, and a codegen phase's `blocked_by` is meaningless without the design phase
    it reads — and only the grouping, the summary and the next-command pick are narrowed
    to the requested section.
    """
    raw = progress if progress is not None else load_progress(project_dir)
    progress = normalize_progress(raw)
    detected = detect_plugin(progress, project_dir)
    plugin = plugin if plugin in PLUGINS else detected
    manifest = load_phase_manifest(plugin)
    # `options` is what the project set and is reported as such; `effective` adds the
    # conditions derived from the canonical API-style contract, which drive phase
    # exclusion but are nobody's setting and must not be reported back as one.
    options = (progress or {}).get("options") or {}
    if not isinstance(options, dict):
        options = {}
    if plugin == "architect":
        effective, canonical_errors, canonical_warnings = canonical_api_style_options(
            project_dir, options)
    else:
        effective, canonical_errors, canonical_warnings = dict(options), [], []
    project_name = (progress or {}).get("project_name") or os.path.basename(
        os.path.abspath(project_dir))
    entries = ((progress or {}).get("phases") or {})
    costs, total_cost, unassigned_cost = load_cost(project_dir, plugin)
    activity, latest_activity = load_activity(project_dir, plugin=plugin)
    now = datetime.now(timezone.utc).timestamp()

    phases = {}
    for name in order_phases(manifest):
        phases[name] = derive_phase(name, manifest[name], entries.get(name), project_dir,
                                    effective, project_name, costs, activity, now, plugin)

    # Registry entries for phases this plugin's manifest does not know (hand-written or
    # renamed) are still shown, so nothing recorded is silently dropped — except the ones
    # the *other* plugin's manifest does know. Both pipelines write the same registry, and
    # a product phase listed among the architect tree's unmanifested leftovers is not a
    # finding, it is the tab next door.
    foreign = set()
    for other in PLUGINS:
        if other != plugin:
            foreign |= set(load_phase_manifest(other))
    for name, entry in entries.items():
        if name not in phases and name not in foreign:
            phases[name] = derive_phase(name, {"category": "other", "tier": "other"},
                                        entry, project_dir, effective, project_name,
                                        costs, activity, now, plugin)

    mark_stale(phases)

    done = ("completed", "skipped")
    for state in phases.values():
        # An optional dependency that never ran does not block: the user may decline it
        # (`/architect:start` asks, `/architect:pipeline` may skip it) without stamping
        # `skipped`, and a phase that waits on a phase nobody will run waits forever. It
        # blocks while actually running or after failing — then its outputs are in flux.
        state["blocked_by"] = [d for d in state["depends_on"]
                               if d in phases and phases[d]["status"] not in done
                               and not (phases[d]["optional"]
                                        and phases[d]["status"] == "pending")]
        # A stale phase is work to redo, so it is runnable again — but it is not
        # *blocking* its dependents, which already hold outputs and are stale themselves.
        state["runnable"] = ((state["status"] in ("pending", "failed") or state["stale"])
                             and not state["blocked_by"] and not state["excluded"])

    visible = {n: s for n, s in phases.items() if s["section"] == section}

    groups = []
    index = {}
    for name, state in visible.items():
        key = "extension" if state["tier"] == "extension" else state["category"]
        state["group"] = key
        if key not in index:
            index[key] = {"key": key, "phases": []}
            groups.append(index[key])
        index[key]["phases"].append(state)

    # What the progress fraction is measured over. On the pipeline section that is the
    # required path — the manual extension tier is opt-in work, not outstanding work. The
    # codegen section is entirely manual, so there every phase counts.
    countable = [s for s in visible.values()
                 if section != "pipeline" or s["tier"] == "core"]
    counts = {s: 0 for s in DISPLAY_STATUSES}
    for state in countable:
        counts[state["display_status"]] += 1
    stale = [s["name"] for s in visible.values() if s["stale"]]
    summary = {
        "by_status": counts,
        "total": sum(counts.values()),
        # Stale phases leave the done column on purpose: the fraction has to fall when an
        # upstream fix invalidates work, or the bar keeps reporting a finished pipeline
        # that no longer matches its own inputs.
        "completed": counts["completed"] + counts["skipped"],
        "stale": len(stale),
        "total_cost_usd": total_cost,
        "unassigned_cost_usd": unassigned_cost,
        "latest_activity": latest_activity or None,
    }
    current = next((s["name"] for s in countable if s["status"] == "in_progress"), None)
    # The suggested next phase prefers the required path: an optional phase (a greenfield
    # entry point, an on-demand skill) is runnable from the start and would otherwise
    # always win, which is not what "what do I run next" means mid-pipeline.
    runnable = [s["name"] for s in countable if s["runnable"]]
    nxt = next((n for n in runnable if not phases[n]["optional"]),
               runnable[0] if runnable else None)
    # Redoing invalidated work comes first, and from the top of the chain: rerunning the
    # earliest stale phase is what lets everything below it stop being stale at all.
    nxt = next((n for n in runnable if phases[n]["stale"]), nxt)

    # Whether this plugin's section has anything behind it, which is what decides if the
    # dashboard offers its tab at all: an output actually on disk, or a registry entry
    # under a name no other plugin's manifest also defines.
    exclusive = exclusive_phases(plugin)
    evidence = any(s["written"] for s in visible.values()) or any(
        n in entries for n in visible if n in exclusive)
    return {
        "plugin": plugin, "detected_plugin": detected, "section": section,
        "project": project_name, "project_dir": project_dir,
        "has_progress": progress is not None, "options": options, "evidence": evidence,
        # `phases` is the section on screen; `all_phases` keeps the whole manifest, which
        # is what dependency and staleness answers were computed against.
        "phases": visible, "all_phases": phases,
        "groups": groups, "summary": summary,
        "current": current, "next": nxt, "stale": stale,
        "gate": read_gate(progress) if section == "pipeline" else None,
        "errors": list((progress or {}).get("errors") or []) + canonical_errors,
        "warnings": list((progress or {}).get("warnings") or []) + canonical_warnings,
        "backlog": backlog_summary(project_dir) if section == "pipeline" else None,
        "updated_at": (progress or {}).get("updated_at"),
    }


def codegen_plugins(project_dir, progress=None):
    """Which plugins the codegen tab shows a group for: those whose pipeline ran.

    A project that never ran the product pipeline has no frontend to generate, and one
    that never ran architect has no services to scaffold — listing both regardless would
    fill the tab with phases that cannot start. When neither pipeline has left a trace
    yet the detected one stands in, so a freshly initialized project still has a tab.
    """
    raw = progress if progress is not None else load_progress(project_dir)
    found = [p for p in PLUGIN_ORDER
             if derive_all(project_dir, plugin=p, progress=raw)["evidence"]]
    return found or [detect_plugin(normalize_progress(raw), project_dir)]


def derive_codegen(project_dir, progress=None, plugins=None):
    """The code-generation tab's state: both plugins' codegen phases in one tree.

    Code generation is not a step of one pipeline — architect scaffolds the services and
    the infrastructure, product scaffolds the React frontend — so the tab is assembled
    from both manifests and grouped by the plugin each phase came from, rather than by
    category. Otherwise it is an ordinary pipeline state and every renderer walks it the
    same way; `state["plugin"]` is "codegen" (not a real plugin), which is the signal to
    take each command's prefix from the phase instead of from the view.

    Pass `plugins` when the caller already knows which pipelines ran (the dashboard does
    — its two pipeline tabs derived exactly that a moment earlier) to avoid re-deriving.
    """
    raw = progress if progress is not None else load_progress(project_dir)
    if plugins is None:
        plugins = codegen_plugins(project_dir, raw)
    parts = [(p, derive_all(project_dir, plugin=p, progress=raw, section="codegen"))
             for p in PLUGIN_ORDER if p in plugins]
    if not parts:
        parts = [(PLUGIN_ORDER[0], derive_all(project_dir, plugin=PLUGIN_ORDER[0],
                                              progress=raw, section="codegen"))]

    phases, groups, everything = {}, [], {}
    for plugin, part in parts:
        everything.update(part["all_phases"])
        group = {"key": plugin, "phases": []}
        for name, phase in part["phases"].items():
            phase["group"] = plugin
            phases.setdefault(name, phase)
            group["phases"].append(phase)
        if group["phases"]:
            groups.append(group)

    counts = {s: 0 for s in DISPLAY_STATUSES}
    for phase in phases.values():
        counts[phase["display_status"]] += 1
    stale = [p["name"] for p in phases.values() if p["stale"]]
    cost = sum(p["cost_usd"] or 0 for p in phases.values())
    activity = [p["last_activity"] for p in phases.values() if p["last_activity"]]
    summary = {
        "by_status": counts, "total": sum(counts.values()),
        "completed": counts["completed"] + counts["skipped"], "stale": len(stale),
        "total_cost_usd": cost or None, "unassigned_cost_usd": None,
        "latest_activity": max(activity) if activity else None,
    }
    runnable = [p["name"] for p in phases.values() if p["runnable"]]
    base = parts[0][1]
    return dict(base,
                plugin="codegen", section="codegen", phases=phases, groups=groups,
                all_phases=everything, summary=summary, gate=None, backlog=None,
                stale=stale,
                current=next((p["name"] for p in phases.values()
                              if p["status"] == "in_progress"), None),
                next=next((n for n in runnable if phases[n]["stale"]),
                          runnable[0] if runnable else None),
                evidence=any(part["evidence"] for _, part in parts))


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
    # The gate is the *product* pipeline's, and it is shown on the architect tab too —
    # requirements resting on an unvalidated premise is exactly what an architect wants to
    # know. But an unlabelled "gate: no-go" over the architect tree reads as architect's
    # own verdict, so the owner travels with it and the views name it when it is not theirs.
    return {"verdict": entry.get("verdict") or "pending",
            "plugin": "product",
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
    # The tier filter is a statement about the architect pipeline's core/extension split,
    # so it has nothing to say about the codegen tab, whose groups are plugins.
    if state.get("section", "pipeline") == "pipeline":
        if tier_filter == "core":
            groups = [g for g in groups if g["key"] != "extension"]
        elif tier_filter == "extension":
            groups = [g for g in groups if g["key"] == "extension"]
    visible = []
    for group in groups:
        phases = [p for p in group["phases"]
                  if not status_filter or p["display_status"] == status_filter]
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
    """(done, total) for a group header — stale phases are not done."""
    total = len(group["phases"])
    done = sum(1 for p in group["phases"]
               if p["display_status"] in ("completed", "skipped"))
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
def phase_plugin(state, phase):
    """Which plugin's slash commands a phase answers to.

    The view's plugin normally decides, but the codegen tab spans both, so there
    `state["plugin"]` is not a real plugin and the phase carries its own.
    """
    if state.get("plugin") in PLUGINS:
        return state["plugin"]
    return phase.get("plugin") or PLUGIN_ORDER[-1]


def actions_for(state, phase):
    """(label, command) entries for the action menu / default `c` copy."""
    plugin = phase_plugin(state, phase)
    prefix = PLUGINS[plugin]["prefix"]
    orchestrator = PLUGINS[plugin]["orchestrator"]
    name = phase["name"]
    label = "rerun phase" if phase["stale"] else "run phase"
    out = [(label, "%s%s" % (prefix, name))]
    if plugin == "architect":
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
    elif phase["stale"]:
        prefer = "rerun phase"
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
    bits = ["%s %s" % (phase_plugin(state, phase), phase["name"]),
            phase["display_status"]]
    if phase["declared"]:
        bits.append("%d/%d %s" % (phase["written"], phase["declared"], T["outputs"]))
    if phase["stale"]:
        bits.append(T["stale_upstream"] % ", ".join(phase["stale_by"]
                                                    + phase["stale_inherited"]))
    if phase["blocked_by"]:
        bits.append("%s %s" % (T["blocked_by"], ", ".join(phase["blocked_by"])))
    return " / ".join(bits)
