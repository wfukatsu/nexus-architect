#!/usr/bin/env python3
"""Render the four Markdown views of a UI inventory — generated, never re-authored.

`/architect:analyze-ui` writes one canonical model, `ui-inventory.json`, plus its token file. The
four views a reader opens — the screen catalog, the features and tasks, the components and the
design-system extract — are projections of that model, so they are rendered here rather than
written by a model per run: the same inventory always yields the same views, the reference set's
views can be checked against a re-render, and a rerun costs no tokens.

Every figure the views show that a metric covers (depth, dead ends, orphans, task steps and
inputs, label drift) is taken from `ui_metrics.compute`, never re-derived. The output language
switches the UI strings only; labels, messages and names stay as the inventory holds them.

Usage:
    python3 tools/lib/ui_views.py <project_dir> [--project=<name>] [--lang=en|ja]
        (writes reports/before/<project>/ui-{screen-catalog,features,components,
         design-system-extract}.md; exit 1 when the inventory is missing or not well-formed)
"""

import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_inventory import is_alias, iter_tokens, token_extension  # noqa: E402
from ui_metrics import compute, load  # noqa: E402

LANGS = ("en", "ja")
VIEWS = ("ui-screen-catalog.md", "ui-features.md", "ui-components.md",
         "ui-design-system-extract.md")
MAX_DIAGRAM_SCREENS = 40

# (English, Japanese). Section headings render as the Japanese with the English canonical name in
# parentheses, so a heading is findable by its English name in either language.
T = {
    "title_catalog": ("UI Screen Catalog", "UI 画面カタログ"),
    "title_features": ("UI Features and Tasks", "UI 機能とタスク"),
    "title_components": ("UI Components", "UI 部品"),
    "title_design": ("Design-System Extract", "デザインシステム抽出"),
    "summary": ("Summary", "概要"),
    "diagram": ("Screen Transition Diagram", "画面遷移図"),
    "screen_list": ("Screen List", "画面一覧"),
    "screen_details": ("Screen Details", "画面詳細"),
    "code_map": ("Screen-to-Code Map", "画面とコードの対応"),
    "view_logic": ("Business Logic in the View Layer", "画面層の業務ロジック"),
    "unresolved": ("Unresolved Items and Open Questions", "未解決事項と未決事項"),
    "feature_list": ("Feature List", "機能一覧"),
    "tasks": ("Tasks", "タスク"),
    "actor_feature": ("Actor × Feature", "アクター × 機能"),
    "feature_entity": ("Feature × Entity", "機能 × エンティティ"),
    "criteria": ("Validation Rules as Acceptance-Criteria Candidates", "受入基準候補としての検証ルール"),
    "inventory": ("Component Inventory", "部品一覧"),
    "duplicates": ("Hand-Built Duplicates", "手作りの重複"),
    "unused": ("Unused Components", "未使用の部品"),
    "palette": ("Palette", "カラーパレット"),
    "typography": ("Typography", "タイポグラフィ"),
    "dimensions": ("Spacing, Radius, Borders and Shadow", "余白・角丸・罫線・影"),
    "fragmentation": ("Fragmentation", "断片化"),
    "semantic": ("Semantic Token Candidates", "セマンティックトークン候補"),
    "variants": ("Component Variants", "部品のバリアント"),
    "importing": ("Importing into a Design System", "デザインシステムへの取り込み"),
    # labels
    "input": ("INPUT", "INPUT（入力）"), "output": ("OUTPUT", "OUTPUT（出力）"),
    "actions": ("Actions", "操作"), "messages": ("Messages", "メッセージ"),
    "access": ("Access", "アクセス制御"),
    "id": ("ID", "ID"), "name": ("Name", "名前"), "route": ("Route", "ルート"),
    "roles": ("Roles", "ロール"), "inputs": ("Inputs", "入力"), "outputs": ("Outputs", "出力"),
    "depth": ("Depth", "深さ"), "source": ("Source", "出典"), "label": ("Label", "ラベル"),
    "control": ("Control", "コントロール"), "type": ("Type", "型"),
    "required": ("Required", "必須"), "validation": ("Validation", "検証"),
    "note": ("Note", "備考"), "kind": ("Kind", "種別"), "fields": ("Fields", "項目"),
    "command": ("Command", "コマンド"), "lands": ("Lands on / endpoint", "遷移先 / エンドポイント"),
    "sends": ("Sends", "送信する入力"), "destructive": ("Destructive", "破壊的"),
    "confirmation": ("Confirmation", "確認"), "guard": ("Guard", "ガード"),
    "handler": ("Handler", "ハンドラ"), "services": ("Services", "サービス"),
    "entities": ("Entities", "エンティティ"), "should_live": ("Should live in", "本来の置き場所"),
    "description": ("Description", "説明"), "ref": ("Reference", "対象"),
    "reason": ("Reason", "理由"), "oq": ("Open Question", "未決事項"),
    "question": ("Question", "質問"), "status": ("Status", "状態"),
    "screens": ("Screens", "画面"), "actors": ("Actors", "アクター"),
    "goal": ("Goal", "目的"), "path": ("Path", "経路"), "steps": ("Steps", "ステップ"),
    "required_inputs": ("Required inputs", "必須入力"), "feature": ("Feature", "機能"),
    "rule": ("Rule", "ルール"), "where": ("Where it runs", "実施場所"),
    "level": ("Level", "レベル"), "variants_col": ("Variants", "バリアント"),
    "states": ("States", "状態"), "used_by": ("Used by", "使用画面"),
    "rebuilds": ("Rebuilds", "元の部品"), "token": ("Token", "トークン"),
    "value": ("Value", "値"), "uses": ("Uses", "使用数"), "cluster": ("Cluster", "クラスタ"),
    "members": ("Members", "メンバー"), "proposal": ("Proposal", "提案"),
    "alias": ("Alias of", "参照先"), "metric": ("Metric", "指標"), "count": ("Count", "件数"),
    # phrases
    "yes": ("yes", "あり"), "no": ("no", "なし"),
    "view_only": ("view-only", "画面のみ"),
    "client_only": ("client only — the server accepts what it forbids",
                    "クライアントのみ — サーバーは受け付けてしまう"),
    "consolidate": ("Consolidate to %s (most used)", "%s（最多使用）に統合"),
    "none": ("None.", "なし。"),
    "legend": ("Dashed: orphan (nothing links to it). Red: dead end. Global chrome actions "
               "(logout, footer) are omitted.",
               "破線: 孤立画面（どこからもリンクされない）。赤: 行き止まり。共通ヘッダ・フッタの操作"
               "（ログアウトなど）は省略。"),
    "import_note": ("`/product:design-system` normalizes this file to the DTCG schema: the "
                    "`semantic.*` candidates map to its aliases, and each fragmented cluster "
                    "becomes a consolidation question.",
                    "`/product:design-system` がこのファイルを DTCG スキーマに正規化する。"
                    "`semantic.*` の候補はエイリアスに対応づけ、断片化したクラスタはそれぞれ統合の"
                    "質問になる。"),
    "screens_count": ("Screens", "画面数"), "entry_count": ("Entry screens", "入口画面"),
    "components_count": ("Components", "部品数"), "features_count": ("Features", "機能数"),
    "tasks_count": ("Tasks", "タスク数"), "logic_count": ("View-layer logic items", "画面層ロジック"),
    "unresolved_count": ("Unresolved items", "未解決事項"),
    "dead_ends": ("Dead ends", "行き止まり"), "orphans": ("Orphans", "孤立画面"),
    "max_depth": ("Maximum depth", "最大の深さ"),
    "diagram_for": ("Task: %s", "タスク: %s"),
}


class View:
    def __init__(self, lang):
        self.i = LANGS.index(lang) if lang in LANGS else 0

    def t(self, key):
        return T[key][self.i]

    def h(self, key):
        en, ja = T[key]
        return en if self.i == 0 else "%s（%s）" % (ja, en)


def cell(value):
    """A table cell: flattened to one line, pipes escaped, empty as a dash."""
    if value is None or value == "" or value == []:
        return "-"
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value)
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text.replace("|", "\\|")


def table(headers, rows):
    out = ["| %s |" % " | ".join(headers), "|%s|" % "|".join("---" for _ in headers)]
    out += ["| %s |" % " | ".join(cell(c) for c in row) for row in rows]
    return "\n".join(out)


def code(value):
    return "`%s`" % value if value else "-"


def mermaid_label(text):
    return re.sub(r'["\[\]{}()|<>#;]', " ", str(text)).strip() or "-"


def node(sid):
    return sid.replace("-", "")


def frontmatter(title, generated_at, inputs):
    lines = ["---", 'title: "%s"' % title.replace('"', "'"), "schema_version: 1",
             'phase: "Phase 1: Investigation"', "skill: analyze-ui",
             'generated_at: "%s"' % generated_at, "input_files:"]
    lines += ["  - %s" % p for p in inputs]
    return "\n".join(lines + ["---", ""])


def read_store(project_dir):
    """{OQ-id: {question, status}} from work/context.md § Open Questions, read by its header."""
    path = os.path.join(project_dir, "work", "context.md")
    if not os.path.isfile(path):
        return {}
    header, rows = None, {}
    for line in open(path, encoding="utf-8").read().splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0].lower() == "id":
            header = [c.lower() for c in cells]
            continue
        if header and cells and re.fullmatch(r"OQ-\d{3,}", cells[0]):
            row = dict(zip(header, cells))
            rows[cells[0]] = {"question": row.get("question", ""), "status": row.get("status", "")}
    return rows


# ------------------------------------------------------------------------------ catalog
def diagram(screens, edges, sids, metrics):
    nav = metrics["navigation"]
    lines = ["```mermaid", "flowchart LR"]
    for s in screens:
        if s["id"] in sids:
            lines.append('    %s["%s %s"]' % (node(s["id"]), s["id"], mermaid_label(s.get("name"))))
    for (a, b), label in sorted(edges.items()):
        if a in sids and b in sids:
            lines.append("    %s -->|%s| %s" % (node(a), mermaid_label(label), node(b)))
    lines.append("    classDef orphan stroke-dasharray: 5 5")
    lines.append("    classDef deadend fill:#fde2e2,stroke:#c0392b")
    for sid in nav["orphans"]:
        if sid in sids:
            lines.append("    class %s orphan" % node(sid))
    for sid in nav["dead_ends"]:
        if sid in sids:
            lines.append("    class %s deadend" % node(sid))
    lines.append("```")
    return "\n".join(lines)


def screen_catalog(v, inv, metrics, store):
    screens = inv["screens"]
    per = metrics["per_screen"]
    nav = metrics["navigation"]
    out = ["## %s" % v.h("summary"), ""]
    logic = sum(len(s.get("embedded_logic") or []) for s in screens)
    unresolved = (inv.get("coverage") or {}).get("unresolved") or []
    out.append(table([v.t("metric"), v.t("count")], [
        (v.t("screens_count"), len(screens)), (v.t("entry_count"), ", ".join(nav["entry"])),
        (v.t("components_count"), len(inv.get("components") or [])),
        (v.t("features_count"), len(inv.get("features") or [])),
        (v.t("tasks_count"), len(inv.get("tasks") or [])), (v.t("logic_count"), logic),
        (v.t("unresolved_count"), len(unresolved)),
        (v.t("dead_ends"), ", ".join(nav["dead_ends"]) or "-"),
        (v.t("orphans"), ", ".join(nav["orphans"]) or "-"),
        (v.t("max_depth"), nav["max_depth"])]))

    edges = {}
    for s in screens:
        for a in s.get("actions") or []:
            if a.get("target") and a.get("scope", "screen") != "global":
                edges.setdefault((s["id"], a["target"]), a.get("command") or a.get("label"))
    out += ["", "## %s" % v.h("diagram"), "", v.t("legend"), ""]
    if len(screens) <= MAX_DIAGRAM_SCREENS:
        out.append(diagram(screens, edges, {s["id"] for s in screens}, metrics))
    else:
        for task in inv.get("tasks") or []:
            out += ["", "### %s" % (v.t("diagram_for") % task.get("name")), "",
                    diagram(screens, edges, set(task.get("screens") or []), metrics)]

    out += ["", "## %s" % v.h("screen_list"), ""]
    out.append(table([v.t("id"), v.t("name"), v.t("route"), v.t("roles"), v.t("inputs"),
                      v.t("outputs"), v.t("actions"), v.t("depth"), v.t("source")],
                     [(s["id"], s.get("name"), code(s.get("route")), (s.get("access") or {}).get("roles"),
                       per[s["id"]]["inputs"], per[s["id"]]["outputs"], per[s["id"]]["actions"],
                       per[s["id"]]["depth"], code(s.get("source"))) for s in screens]))

    out += ["", "## %s" % v.h("screen_details")]
    for s in screens:
        out += ["", "### %s %s" % (s["id"], s.get("name")), ""]
        inputs = s.get("inputs") or []
        out += ["**%s**" % v.t("input"), ""]
        if inputs:
            rows = []
            for f in inputs:
                rules = ["%s%s @%s%s" % (r.get("rule"), "=%s" % r["value"] if r.get("value")
                                          not in (None, "") else "", r.get("where"),
                                          " (%s)" % r["enforcement"] if r.get("enforcement")
                                          not in (None, "reject") else "")
                         for r in f.get("validation") or []]
                note = "; ".join(x for x in (f.get("prefilled_from") and "prefill: %s" % f["prefilled_from"],
                                             f.get("redundant_with") and "redundant: %s" % f["redundant_with"])
                                 if x)
                rows.append((f.get("label"), code(f.get("name")), f.get("control"), f.get("type"),
                             v.t("yes") if f.get("required") else v.t("no"), rules, note))
            out.append(table([v.t("label"), v.t("name"), v.t("control"), v.t("type"),
                              v.t("required"), v.t("validation"), v.t("note")], rows))
        else:
            out.append(v.t("none"))
        outputs = s.get("outputs") or []
        out += ["", "**%s**" % v.t("output"), ""]
        out.append(table([v.t("label"), v.t("kind"), v.t("fields")],
                         [(o.get("label") or o.get("name"), o.get("kind"), o.get("fields"))
                          for o in outputs]) if outputs else v.t("none"))
        actions = s.get("actions") or []
        out += ["", "**%s**" % v.t("actions"), ""]
        if actions:
            rows = []
            for a in actions:
                lands = a.get("target") or a.get("endpoint") or a.get("unresolved")
                if a.get("target") and a.get("endpoint"):
                    lands = "%s (%s)" % (a["target"], a["endpoint"])
                guard = a.get("guard")
                rows.append((a.get("label"), code(a.get("command")), lands, a.get("inputs"),
                             v.t("yes") if a.get("destructive") else v.t("no"),
                             v.t("yes") if a.get("confirmation") else v.t("no"),
                             "%s %s" % (guard.get("kind"), ", ".join(guard.get("roles") or []))
                             if isinstance(guard, dict) else "-"))
            out.append(table([v.t("label"), v.t("command"), v.t("lands"), v.t("sends"),
                              v.t("destructive"), v.t("confirmation"), v.t("guard")], rows))
        else:
            out.append(v.t("none"))
        messages = s.get("messages") or []
        if messages:
            out += ["", "**%s**" % v.t("messages"), ""]
            out += ["- [%s] %s (%s)" % (m.get("kind"), m.get("text"), code(m.get("source")))
                    for m in messages]
        access = s.get("access") or {}
        guards = access.get("guards") or []
        view_only = bool(guards) and all(g.get("kind") == "view" for g in guards)
        out += ["", "**%s**: %s — %s%s%s" % (
            v.t("access"), access.get("authentication"), ", ".join(access.get("roles") or []),
            "; " + ", ".join("%s @ %s" % (g.get("kind"), code(g.get("source"))) for g in guards)
            if guards else "", " (%s)" % v.t("view_only") if view_only else "")]

    out += ["", "## %s" % v.h("code_map"), ""]
    rows = [(s["id"], code(h.get("ref")), h.get("services"), h.get("entities"))
            for s in screens for h in s.get("handlers") or []]
    out.append(table([v.t("id"), v.t("handler"), v.t("services"), v.t("entities")], rows)
               if rows else v.t("none"))

    out += ["", "## %s" % v.h("view_logic"), ""]
    rows = [(s["id"], e.get("kind"), e.get("description"), e.get("should_live_in"),
             code(e.get("source"))) for s in screens for e in s.get("embedded_logic") or []]
    out.append(table([v.t("id"), v.t("kind"), v.t("description"), v.t("should_live"),
                      v.t("source")], rows) if rows else v.t("none"))

    out += ["", "## %s" % v.h("unresolved"), ""]
    out.append(table([v.t("ref"), v.t("reason"), v.t("oq")],
                     [(code(u.get("ref")), u.get("reason"), u.get("oq")) for u in unresolved])
               if unresolved else v.t("none"))
    oqs = inv.get("open_questions") or []
    if oqs:
        out += ["", table([v.t("oq"), v.t("question"), v.t("status")],
                          [(q, store.get(q, {}).get("question"), store.get(q, {}).get("status"))
                           for q in oqs])]
    return "\n".join(out)


# ----------------------------------------------------------------------------- features
def features_view(v, inv, metrics):
    screens = {s["id"]: s for s in inv["screens"]}
    features = inv.get("features") or []
    out = ["## %s" % v.h("feature_list"), ""]
    out.append(table([v.t("id"), v.t("name"), v.t("command"), v.t("screens"), v.t("actors"),
                      v.t("entities")],
                     [(f["id"], f.get("name"), code(f.get("command")), f.get("screens"),
                       f.get("actors"), f.get("entities")) for f in features]))
    out += ["", "## %s" % v.h("tasks"), ""]
    out.append(table([v.t("name"), v.t("goal"), v.t("path"), v.t("steps"), v.t("inputs"),
                      v.t("required_inputs")],
                     [(t.get("name"), t.get("goal"), " → ".join(t.get("screens") or []),
                       metrics["tasks"].get(t.get("name"), {}).get("steps"),
                       metrics["tasks"].get(t.get("name"), {}).get("inputs"),
                       metrics["tasks"].get(t.get("name"), {}).get("required_inputs"))
                      for t in inv.get("tasks") or []]))

    def view_only(feature):
        guards = [g for sid in feature.get("screens") or [] for g in
                  ((screens.get(sid) or {}).get("access") or {}).get("guards") or []]
        return bool(guards) and all(g.get("kind") == "view" for g in guards)

    actors = sorted({a for f in features for a in f.get("actors") or []})
    out += ["", "## %s" % v.h("actor_feature"), ""]
    rows = []
    for actor in actors:
        row = [actor]
        for f in features:
            mark = "✓" if actor in (f.get("actors") or []) else ""
            if mark and view_only(f):
                mark = "✓ (%s)" % v.t("view_only")
            row.append(mark)
        rows.append(row)
    out.append(table([v.t("actors")] + [f["id"] for f in features], rows) if features
               else v.t("none"))

    out += ["", "## %s" % v.h("feature_entity"), ""]
    rows = [(f["id"], f.get("name"), entity, ops) for f in features
            for entity, ops in sorted((f.get("entity_operations") or {}).items())]
    out.append(table([v.t("id"), v.t("feature"), v.t("entities"), "CRUD"], rows)
               if rows else v.t("none"))

    out += ["", "## %s" % v.h("criteria"), ""]
    rows = []
    for f in features:
        for aid in f.get("actions") or []:
            sid = aid.split(".")[0]
            fields = {x.get("name"): x for x in (screens.get(sid) or {}).get("inputs") or []}
            action = next((a for a in (screens.get(sid) or {}).get("actions") or []
                           if a.get("id") == aid), {})
            for name in action.get("inputs") or []:
                field = fields.get(name) or {}
                server = {r.get("rule") for r in field.get("validation") or []
                          if r.get("where") in ("server", "both")}
                for r in field.get("validation") or []:
                    flag = " — %s" % v.t("client_only") \
                        if r.get("where") == "client" and r.get("rule") not in server else ""
                    rows.append((f["id"], field.get("label") or name, "%s%s" % (
                        r.get("rule"), "=%s" % r["value"] if r.get("value") not in (None, "") else ""),
                        "%s%s" % (r.get("where"), flag)))
    out.append(table([v.t("feature"), v.t("inputs"), v.t("rule"), v.t("where")], rows)
               if rows else v.t("none"))
    return "\n".join(out)


# --------------------------------------------------------------------------- components
def components_view(v, inv):
    components = inv.get("components") or []
    names = {c["id"]: c.get("name") for c in components}
    out = ["## %s" % v.h("inventory"), ""]
    out.append(table([v.t("id"), v.t("name"), v.t("kind"), v.t("level"), v.t("variants_col"),
                      v.t("states"), v.t("used_by"), v.t("source")],
                     [(c["id"], c.get("name"), c.get("kind"), c.get("level"), c.get("variants"),
                       c.get("states"), c.get("used_by"), code(c.get("source")))
                      for c in components]) if components else v.t("none"))
    dups = [c for c in components if c.get("duplicates")]
    out += ["", "## %s" % v.h("duplicates"), ""]
    out.append(table([v.t("id"), v.t("name"), v.t("kind"), v.t("rebuilds"), v.t("source")],
                     [(c["id"], c.get("name"), c.get("kind"),
                       ", ".join("%s %s" % (d, names.get(d, "")) for d in c["duplicates"]),
                       code(c.get("source"))) for c in dups]) if dups else v.t("none"))
    unused = [c for c in components if c.get("unused")]
    out += ["", "## %s" % v.h("unused"), ""]
    out.append("\n".join("- %s %s (%s)" % (c["id"], c.get("name"), code(c.get("source")))
                         for c in unused) if unused else v.t("none"))
    return "\n".join(out)


# ------------------------------------------------------------------------ design system
def design_view(v, inv, tokens, project):
    leaves = dict(iter_tokens(tokens))
    raw = {p: t for p, t in leaves.items() if not is_alias(t)}

    def rows_for(predicate):
        rows = []
        for path, token in sorted(raw.items()):
            if predicate(path, token):
                ext = token_extension(token)
                sources = ext.get("sources") or []
                rows.append((code(path), code(token.get("$value")), ext.get("usage_count"),
                             ext.get("cluster"), ", ".join(sources[:3]) +
                             (" …+%d" % (len(sources) - 3) if len(sources) > 3 else "")))
        return rows

    headers = [v.t("token"), v.t("value"), v.t("uses"), v.t("cluster"), v.t("source")]
    out = []
    for key, predicate in (
            ("palette", lambda p, t: t.get("$type") == "color"),
            ("typography", lambda p, t: p.startswith("font.")),
            ("dimensions", lambda p, t: t.get("$type") != "color" and not p.startswith("font."))):
        rows = rows_for(predicate)
        out += ["## %s" % v.h(key), "", table(headers, rows) if rows else v.t("none"), ""]

    clusters = {}
    for path, token in raw.items():
        name = token_extension(token).get("cluster")
        if name:
            clusters.setdefault((token.get("$type"), name), []).append(
                (token_extension(token).get("usage_count") or 0, token.get("$value"), path))
    rows = []
    for (kind, name), members in sorted(clusters.items()):
        if len(members) > 1:
            members.sort(key=lambda m: (-m[0], str(m[1])))
            rows.append((name, kind, ", ".join("%s×%d" % (m[1], m[0]) for m in members),
                         v.t("consolidate") % members[0][1]))
    out += ["## %s" % v.h("fragmentation"), "",
            table([v.t("cluster"), v.t("type"), v.t("members"), v.t("proposal")], rows)
            if rows else v.t("none"), ""]

    rows = []
    for path, token in sorted(leaves.items()):
        if is_alias(token):
            target = token["$value"][1:-1]
            rows.append((code(path), code(target), code((leaves.get(target) or {}).get("$value")),
                         token.get("$description")))
    out += ["## %s" % v.h("semantic"), "",
            table([v.t("token"), v.t("alias"), v.t("value"), v.t("description")], rows)
            if rows else v.t("none"), ""]

    comps = [c for c in inv.get("components") or [] if c.get("variants")]
    out += ["## %s" % v.h("variants"), "",
            table([v.t("id"), v.t("name"), v.t("variants_col"), v.t("states")],
                  [(c["id"], c.get("name"), c.get("variants"), c.get("states")) for c in comps])
            if comps else v.t("none"), ""]
    out += ["## %s" % v.h("importing"), "", "```",
            "/product:design-system --import=reports/before/%s/ui-design-tokens.json --name=<name>"
            % project, "```", "", v.t("import_note")]
    return "\n".join(out)


def render(project_dir, inventory, tokens, lang):
    """{file name: Markdown} for the four views."""
    v = View(lang)
    metrics = compute(inventory, tokens)
    project = inventory.get("project")
    generated = inventory.get("generated_at") or datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    base = "reports/before/%s" % project
    inputs = ["%s/ui-inventory.json" % base, "%s/ui-design-tokens.json" % base]
    store = read_store(project_dir)
    bodies = {
        "ui-screen-catalog.md": (v.t("title_catalog"), screen_catalog(v, inventory, metrics, store)),
        "ui-features.md": (v.t("title_features"), features_view(v, inventory, metrics)),
        "ui-components.md": (v.t("title_components"), components_view(v, inventory)),
        "ui-design-system-extract.md": (v.t("title_design"),
                                        design_view(v, inventory, tokens, project)),
    }
    return {name: frontmatter("%s — %s" % (title, project), generated, inputs) + "\n" + body.rstrip()
            + "\n" for name, (title, body) in bodies.items()}


def resolve_lang(project_dir, lang):
    if lang in LANGS:
        return lang
    try:
        with open(os.path.join(project_dir, "work", "pipeline-progress.json"), encoding="utf-8") as h:
            value = (json.load(h).get("options") or {}).get("output_language")
        return value if value in LANGS else "en"
    except (OSError, ValueError, AttributeError):
        return "en"


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    options = dict(a[2:].split("=", 1) for a in argv[1:] if a.startswith("--") and "=" in a)
    project_dir = args[0] if args else "."
    inventory, tokens, errors = load(project_dir, options.get("project"))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    lang = resolve_lang(project_dir, options.get("lang"))
    target = os.path.join(project_dir, "reports", "before", inventory["project"])
    for name, text in render(project_dir, inventory, tokens, lang).items():
        with open(os.path.join(target, name), "w", encoding="utf-8") as handle:
            handle.write(text)
        print("wrote %s" % os.path.relpath(os.path.join(target, name), project_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
