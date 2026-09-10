#!/usr/bin/env python3
"""Build the consolidated HTML report for a nexus-architect project.

This is the engine behind `/architect:report` and `/product:report`. It reads the
Markdown a pipeline run already wrote under `<project>/reports/`, plus the pipeline
progress registry, the Open Questions store in `work/context.md` and (architect) the
review synthesis JSON, and emits one self-contained HTML file: Mermaid inlined where a
local copy of the library is available, no network request needed to read it.

Nothing here is authored by a model at run time. The report is a deterministic
rendering of files on disk, so re-running it after a phase re-ran is cheap and the
result is diffable. In particular a Mermaid fence always becomes
`<pre class="mermaid">` holding the escaped source and nothing else — never a
`<pre><code>` pair, which Mermaid's `startOnLoad` (it reads `innerHTML`) cannot parse.

Usage
-----
    python3 tools/build-report.py [PROJECT_DIR] [--output PATH] [--mermaid-js PATH]
                                  [--layout architect|product] [--lang en|ja]

`PROJECT_DIR` defaults to the current directory and must contain `reports/`. All other
paths are resolved relative to it. Output language comes from `--lang`, else from
`options.output_language` in `work/pipeline-progress.json` (`en` default, `ja`
supported): every UI string — section headings, table headers, summary labels — goes
through the one bilingual table below. Document content is rendered as written.

Layouts
-------
The layout is detected from the report tree (`--layout` overrides): a project holding
any of `reports/00_core`, `01_ux`, `02_spec`, `03_domain` is a **product** project,
anything else is an **architect** project. Each is skipped when its directory is absent
or holds nothing renderable. The `<h2 id>`s are the canonical section identifiers of
`skills/report/SKILL.md` / `skills/product/report/SKILL.md` § Input Sources.

architect — output `reports/00_summary/full-report.html`

    id               source
    ---------------- --------------------------------------------------------------
    summary          work/pipeline-progress.json + reports/review/review-synthesis.json
                     + work/context.md § Open Questions
    investigation    reports/before/*/           (one subgroup per project directory)
    analysis         reports/01_analysis/
    evaluation       reports/02_evaluation/
    design           reports/03_design/ and its adr/ (index first, then ADR id order),
                     aggregates/, state-machines/ and api-specifications/ subdirectories
    stories          reports/04_stories/
    implementation   reports/06_implementation/
    test-specs       reports/07_test-specs/ and bdd-scenarios/*.feature as Gherkin
    review           reports/review/ plus the per-perspective table built from
                     reports/review/individual/*.json

product — output `reports/report/full-report.html`

    id               source
    ---------------- --------------------------------------------------------------
    summary          "Key Assumptions & Validation Status": the validate-assumptions
                     gate in work/pipeline-progress.json, the open ASM- rows of
                     reports/00_core/assumptions.md and validation-plan.md, every
                     TBD / TBD-assumption placeholder per document, and the Open
                     Questions of work/context.md grouped by status with owners
    core             reports/00_core/
    ux               reports/01_ux/ and domain-stories/
    spec             reports/02_spec/, examples/ (index first) and ui-mocks/
    domain           reports/03_domain/ (figures/, slides/ listed by name only)
    quality          reports/04_quality/
    adaptation       reports/05_adaptation/
    other            any other reports/<dir>/ — one subgroup per directory
    review           reports/report/review.md

Documents inside a product section follow the pipeline order of
`skills/product/common/skill-dependencies.yaml` (`phases.*.outputs`); anything the
manifest does not declare comes after, in name order. Non-Markdown assets (HTML mocks,
images, slides) are listed by file name, never embedded.

Manifest JSON (`aggregate-manifest.json`, `state-machine-manifest.json`,
`api-style-decisions.json`, …) is the machine-readable model, not report content: it is
never rendered. OpenAPI/AsyncAPI YAML is listed by file name and `info.title` only.

Exit codes: 0 on success, 1 when `PROJECT_DIR` has no `reports/` or `markdown` is not
installed.
"""
import argparse
import datetime
import glob
import html
import json
import os
import re
import sys

try:
    import markdown
except ImportError:  # pragma: no cover - environment guard
    sys.stderr.write(
        "build-report: the 'markdown' package is required.\n"
        "Install the repository dependencies: pip install -r requirements.txt\n"
    )
    raise SystemExit(1)

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    sys.stderr.write(
        "build-report: the 'pyyaml' package is required.\n"
        "Install the repository dependencies: pip install -r requirements.txt\n"
    )
    raise SystemExit(1)

MD_EXTENSIONS = ["extra", "sane_lists"]

FENCE_PATTERN = re.compile(
    r"^(?P<fence>```|~~~)(?P<lang>[^\n]*)\n(?P<body>.*?)\n(?P=fence)[ \t]*$",
    re.M | re.S,
)

CDN_URL = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"

# --------------------------------------------------------------------------- i18n
# One table for every user-visible string. Index 0 is English (the default), index 1 is
# Japanese. Document content never passes through here — only the report's own chrome.
LANGS = ("en", "ja")

UI = {
    "report_title": ("System Architecture Consolidated Report", "システムアーキテクチャ統合レポート"),
    "toc": ("Contents", "目次"),
    "pipeline_meta": ("nexus-architect / architect pipeline", "nexus-architect / architect パイプライン"),
    "target": ("Target", "対象"),
    "documents": ("Documents", "収録文書"),
    "generated": ("Generated", "生成"),
    "count_unit": ("", " 件"),
    # Section headings
    "sec_summary": ("Executive Summary — Quality Gate Verdict", "エグゼクティブサマリ — 品質ゲート判定"),
    "sec_investigation": ("Investigation", "調査（Investigation）"),
    "sec_analysis": ("Analysis", "分析（Analysis）"),
    "sec_evaluation": ("Evaluation", "評価（Evaluation）"),
    "sec_design": ("Design", "設計（Design）"),
    "sec_stories": ("Domain Stories", "ドメインストーリー（Domain Stories）"),
    "sec_implementation": ("Implementation", "実装設計（Implementation）"),
    "sec_test_specs": ("Test Specifications", "テスト仕様（Test Specifications）"),
    "sec_review": ("Review", "レビュー（Review）"),
    # Subgroup titles
    "sub_adr": ("Architecture Decision Records", "アーキテクチャ決定記録（ADR）"),
    "sub_aggregates": ("Aggregates", "集約（Aggregates）"),
    "sub_state_machines": ("State Machines", "状態遷移モデル（State Machines）"),
    "sub_api_specs": ("API Specifications", "API 仕様（API Specifications）"),
    "sub_bdd": ("BDD Scenarios (Gherkin .feature)", "BDD シナリオ（Gherkin .feature）"),
    # API specification table
    "api_table_caption": (
        "OpenAPI / AsyncAPI specification files",
        "OpenAPI / AsyncAPI 仕様ファイル一覧",
    ),
    "api_table_note": (
        "(the YAML body is not embedded here; only the file name and its <code>info.title</code>)",
        "（YAML 本文はここには埋め込まず、ファイル名と <code>info.title</code> のみ一覧する）",
    ),
    "col_file": ("File", "ファイル"),
    "col_info_title": ("info.title", "info.title"),
    "no_info_title": ("(no info.title)", "(info.title なし)"),
    "parse_error": ("(parse error: %s)", "(解析エラー: %s)"),
    # Review section
    "review_table_caption": (
        "Individual review perspectives (reports/review/individual/*.json)",
        "個別レビュー観点（reports/review/individual/*.json）",
    ),
    "col_perspective": ("Perspective", "観点"),
    "col_score": ("Score", "スコア"),
    "col_run_at": ("Run at", "実行時刻"),
    "col_findings": ("Findings", "指摘件数"),
    # Executive summary
    "verdict_label": ("Quality gate verdict", "品質ゲート判定"),
    "verdict_score": ("Aggregate score", "総合スコア"),
    "verdict_generated": ("verdict generated", "判定生成"),
    "summary_lede": (
        "This report consolidates %(docs)s design artifacts of %(project)s "
        "(%(pipeline)s, <code>workflow_type: %(workflow)s</code>, "
        "<code>scalardb_enabled: %(scalardb)s</code>).",
        "本レポートは %(project)s（%(pipeline)s、<code>workflow_type: %(workflow)s</code>・"
        "<code>scalardb_enabled: %(scalardb)s</code>）の設計成果物 %(docs)s 件を集約したものである。",
    ),
    "review_not_run": (
        "The review has not been run yet: <code>reports/review/review-synthesis.json</code> "
        "does not exist, so this report carries no quality gate verdict. "
        "Run <code>/architect:review-synthesizer</code> and rebuild.",
        "レビューは未実行です: <code>reports/review/review-synthesis.json</code> が存在しないため、"
        "本レポートには品質ゲート判定が含まれません。"
        "<code>/architect:review-synthesizer</code> を実行してから再生成してください。",
    ),
    "h_perspective_scores": ("Scores by perspective", "観点別スコア"),
    "h_gate_conditions": ("Quality gate conditions", "品質ゲート判定条件"),
    "col_verdict": ("Verdict", "判定"),
    "col_met": ("Met", "充足"),
    "col_violations": ("Why not met", "不充足の理由"),
    "h_findings_by_priority": ("Findings by priority", "指摘件数（優先度別）"),
    "findings_note": (
        "%(total)s in total (%(after_dedup)s after de-duplication, %(reported)s reported, "
        "of which %(active)s still open and %(resolved)s resolved by document revision). "
        "By severity: critical %(critical)s / major %(major)s / minor %(minor)s / info %(info)s.",
        "総数 %(total)s 件（重複排除後 %(after_dedup)s 件、報告対象 %(reported)s 件、"
        "うち未解消 %(active)s 件・文書修正により解消済み %(resolved)s 件）。"
        "重大度内訳: 致命 %(critical)s／重大 %(major)s／軽微 %(minor)s／情報 %(info)s。",
    ),
    "h_open_questions": ("Open Questions", "未決事項（Open Questions）サマリ"),
    "col_status": ("Status", "状態"),
    "col_count": ("Count", "件数"),
    "oq_note": (
        "%(total)s unique OQ- IDs across the <code>work/context.md</code> § Open Questions store. "
        "See the <code>TBD (OQ-###)</code> references in each document, and "
        "<code>work/context.md</code> itself.",
        "work/context.md § Open Questions ストア全体で %(total)s 件（一意の OQ- ID）。"
        "詳細は各文書の <code>TBD (OQ-###)</code> 参照箇所、および <code>work/context.md</code> を参照。",
    ),
    "oq_unasked": ("unasked", "未提示 (unasked)"),
    "oq_deferred": ("deferred", "先送り (deferred)"),
    "oq_answered": ("answered", "answered (回答済み)"),
    "oq_external": ("external", "外部確認待ち (external)"),
    # Product layout — chrome
    "report_title_product": ("Product Direction Consolidated Report",
                             "プロダクト方向性統合レポート"),
    "pipeline_meta_product": ("nexus-architect / product pipeline",
                              "nexus-architect / product パイプライン"),
    "profile": ("Profile", "プロファイル"),
    "sec_summary_product": ("Key Assumptions & Validation Status",
                            "主要な仮説と検証状況（Key Assumptions & Validation Status）"),
    "sec_core": ("Product Core", "プロダクトコア（Product Core）"),
    "sec_ux": ("UX Foundation", "UX 基盤（UX Foundation）"),
    "sec_spec": ("Specification", "仕様（Specification）"),
    "sec_domain": ("Domain & Architecture", "ドメインとアーキテクチャ（Domain & Architecture）"),
    "sec_quality": ("Quality & NFR", "品質と非機能要件（Quality & NFR）"),
    "sec_adaptation": ("Adaptation", "変更適応（Adaptation）"),
    "sec_other": ("Other Documents", "その他の文書（Other Documents）"),
    "sub_domain_stories": ("Domain Stories", "ドメインストーリー（Domain Stories）"),
    "sub_examples": ("Example Maps", "Example Map（実例マッピング）"),
    "sub_ui_mocks": ("UI Mocks", "UI モック（UI Mocks）"),
    "asset_table_caption": ("Files in %s (listed, not embedded)",
                            "%s のファイル一覧（本文には埋め込まない）"),
    # Product layout — Key Assumptions & Validation Status
    "gate_label": ("Validation gate verdict", "検証ゲート判定"),
    "gate_evaluated": ("evaluated", "判定日時"),
    "gate_not_run": (
        "The validation gate has not been evaluated: <code>gates.validate-assumptions</code> "
        "is absent from <code>work/pipeline-progress.json</code>, so this report carries no "
        "Go/No-Go verdict. Run <code>/product:validate-assumptions</code> and rebuild.",
        "検証ゲートは未評価です: <code>work/pipeline-progress.json</code> に "
        "<code>gates.validate-assumptions</code> が無いため、本レポートには Go/No-Go 判定が"
        "含まれません。<code>/product:validate-assumptions</code> を実行してから再生成してください。",
    ),
    "summary_lede_product": (
        "This report consolidates %(docs)s product artifacts of %(project)s "
        "(%(pipeline)s, <code>profile: %(profile)s</code>).",
        "本レポートは %(project)s（%(pipeline)s、<code>profile: %(profile)s</code>）の"
        "プロダクト成果物 %(docs)s 件を集約したものである。",
    ),
    "h_open_assumptions": ("Open assumptions", "未検証の仮説（Open assumptions）"),
    "open_assumptions_note": (
        "%(count)s assumption(s) still open per "
        "<code>gates.validate-assumptions.open_assumptions</code>; the rows below are taken "
        "verbatim from the source documents.",
        "<code>gates.validate-assumptions.open_assumptions</code> に基づく未検証の仮説 "
        "%(count)s 件。以下の行は元文書の表からそのまま再掲している。",
    ),
    "asm_source_note": ("From <code>%s</code>", "<code>%s</code> より"),
    "asm_missing": ("(no row for this ID in %s)", "（%s に該当行なし）"),
    "assumptions_missing": (
        "<code>reports/00_core/assumptions.md</code> does not exist — the assumptions have "
        "not been validated yet.",
        "<code>reports/00_core/assumptions.md</code> が存在しないため、仮説はまだ検証されていない。",
    ),
    "h_tbd": ("TBD placeholders by document", "文書別 TBD 一覧"),
    "col_document": ("Document", "文書"),
    "col_tbd": ("TBD", "TBD"),
    "col_tbd_assumption": ("TBD-assumption", "TBD-assumption"),
    "col_oq_refs": ("Linked OQ", "紐付く OQ"),
    "tbd_note": (
        "%(tbd)s <code>TBD</code> and %(asm)s <code>TBD-assumption</code> placeholders across "
        "%(docs)s document(s).",
        "<code>TBD</code> %(tbd)s 件・<code>TBD-assumption</code> %(asm)s 件（%(docs)s 文書）。",
    ),
    "tbd_none": ("No TBD placeholders remain in the rendered documents.",
                 "収録文書に TBD は残っていない。"),
    "h_oq_by_status": ("Open Questions by status", "未決事項（Open Questions）— 状態別"),
    "col_id": ("ID", "ID"),
    "col_question": ("Question", "質問"),
    "col_owner": ("Owner", "担当"),
    "col_impact": ("Impact", "影響"),
    "oq_answered_count": (
        "%(count)s answered — kept in the store as decision records, not repeated here.",
        "回答済み %(count)s 件（決定記録としてストアに保持、ここでは再掲しない）。",
    ),
    "oq_store_missing": (
        "<code>work/context.md</code> does not exist; no Open Questions could be read.",
        "<code>work/context.md</code> が存在しないため、Open Questions を読み取れなかった。",
    ),
    # Mermaid
    "mermaid_cdn_note": (
        "The Mermaid library could not be bundled locally, so this report falls back to "
        "loading it from a CDN. Displaying the diagrams requires a network connection.",
        "Mermaid ライブラリをローカルに同梱できなかったため CDN 読み込みにフォールバックしています。"
        "図の表示にはネットワーク接続が必要です。",
    ),
}

OQ_STATUS_KEYS = {
    "unasked": "oq_unasked",
    "deferred": "oq_deferred",
    "answered": "oq_answered",
    "external": "oq_external",
}

CSS = """
:root{--bg:#fbfbfa;--fg:#1c1b19;--muted:#6b6862;--line:#e2ded6;--card:#fff;--accent:#8a4b2a;
--fail:#b3261e;--ok:#2e7d4f;--warn:#b7791f;--code:#f3f1ec;--sidebar:#f5f3ee;}
@media(prefers-color-scheme:dark){:root{--bg:#161513;--fg:#e9e6df;--muted:#a29d94;--line:#333029;
--card:#1e1d1a;--accent:#e0925f;--fail:#f2705f;--ok:#6fcf97;--warn:#e0b25f;--code:#232220;--sidebar:#1b1a17;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font-family:-apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Noto Sans JP",Meiryo,sans-serif;
line-height:1.8;font-size:15px;-webkit-text-size-adjust:100%}
#layout{display:flex;align-items:flex-start}
#sidebar{position:sticky;top:0;height:100vh;overflow-y:auto;width:310px;flex:0 0 310px;
background:var(--sidebar);border-right:1px solid var(--line);padding:22px 16px 60px;font-size:13px}
#sidebar h2{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 12px}
#sidebar ul{list-style:none;margin:0;padding:0}
#sidebar ul ul{margin:4px 0 12px 10px;border-left:1px solid var(--line);padding-left:10px}
#sidebar a{color:var(--fg);text-decoration:none;display:block;padding:3px 6px;border-radius:5px;line-height:1.45}
#sidebar a:hover{background:var(--line)}
#sidebar .nav-sec>a{font-weight:700;margin-top:10px}
main{flex:1;min-width:0;max-width:1080px;margin:0 auto;padding:36px 44px 120px}
header.rep{border-bottom:3px solid var(--accent);padding-bottom:18px;margin-bottom:34px}
header.rep h1{font-size:29px;margin:0 0 8px;letter-spacing:-.01em}
header.rep .meta{color:var(--muted);font-size:13px}
header.rep .meta code{background:none;padding:0}
h2{font-size:23px;margin:56px 0 18px;padding-bottom:8px;border-bottom:2px solid var(--line);scroll-margin-top:16px}
.doc h3.doc-title{font-size:22px;margin:40px 0 14px;scroll-margin-top:16px;display:flex;flex-wrap:wrap;
align-items:baseline;gap:10px;border-left:4px solid var(--accent);padding-left:12px}
.doc h3.doc-title .src{font-size:11px;color:var(--muted);font-weight:400;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.doc h4{font-size:18px;margin:34px 0 10px}
.doc h4{font-size:16px;margin:26px 0 8px}
.doc h5{font-size:14.5px;margin:20px 0 6px}
.doc h6{font-size:13.5px;margin:18px 0 6px;color:var(--muted)}
article.doc{border-top:1px solid var(--line);padding-top:6px;margin-top:34px}
.subgroup{margin-top:10px}
.subgroup-title{font-size:14px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);
border-top:1px dashed var(--line);padding-top:22px;margin:34px 0 0}
p{margin:.7em 0}
a{color:var(--accent)}
code{background:var(--code);padding:.1em .35em;border-radius:4px;font-size:.88em;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
pre{background:var(--code);border:1px solid var(--line);border-radius:8px;padding:14px 16px;overflow-x:auto}
pre code{background:none;padding:0;font-size:12.5px;line-height:1.6}
table{border-collapse:collapse;width:100%;margin:16px 0;font-size:13.5px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:7px 11px;text-align:left;vertical-align:top}
th{background:var(--code);font-weight:700}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
blockquote{margin:14px 0;padding:2px 16px;border-left:3px solid var(--line);color:var(--muted)}
hr{border:0;border-top:1px solid var(--line);margin:28px 0}
ul,ol{padding-left:1.5em}
li{margin:.25em 0}
.mermaid-wrap{margin:20px 0;padding:14px;background:var(--card);border:1px solid var(--line);
border-radius:10px;overflow-x:auto;text-align:center}
pre.mermaid{background:none;border:0;padding:0;text-align:center}
pre.mermaid svg{max-width:100%;height:auto}
.verdict-section{border-top:0;margin-top:0}
.verdict-banner{display:flex;flex-wrap:wrap;align-items:baseline;gap:18px;background:var(--card);
border:2px solid var(--fail);border-radius:12px;padding:20px 24px;margin:18px 0 22px}
.verdict-banner.ok{border-color:var(--ok)}
.verdict-banner.warn{border-color:var(--warn)}
.verdict-label{font-size:12px;letter-spacing:.1em;color:var(--muted);text-transform:uppercase}
.verdict-value{font-size:42px;font-weight:800;color:var(--fail);letter-spacing:.02em;line-height:1}
.verdict-banner.ok .verdict-value{color:var(--ok)}
.verdict-banner.warn .verdict-value{color:var(--warn)}
.verdict-score{font-size:16px;color:var(--muted)}
.lede{font-size:15.5px}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:16px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.stat-num{font-size:27px;font-weight:800;font-variant-numeric:tabular-nums}
.stat-cap{font-size:12px;color:var(--muted)}
.stat.p0{border-color:var(--fail)}.stat.p0 .stat-num{color:var(--fail)}
.stat.p1 .stat-num{color:var(--warn)}
.callout{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);
border-radius:8px;padding:14px 18px;margin:18px 0}
.note{font-size:13px;color:var(--muted)}
@media(max-width:900px){#sidebar{display:none}main{padding:22px 16px 80px}}
@media print{#sidebar{display:none}main{max-width:none;padding:0}
a{color:inherit;text-decoration:none}article.doc{break-inside:avoid-page}
h2{break-after:avoid}.mermaid-wrap{break-inside:avoid}}
""".strip()


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_frontmatter(text):
    """Split a leading `---` YAML block from the body. Malformed frontmatter is body."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm_text = text[3:end].strip("\n")
            body = text[end + 4:].lstrip("\n")
            try:
                meta = yaml.safe_load(fm_text) or {}
            except Exception:
                meta = {}
            if not isinstance(meta, dict):
                meta = {}
            return meta, body
    return {}, text


def norm_stem(path_only):
    return os.path.splitext(os.path.basename(path_only))[0]


def rewrite_links(text):
    """Turn inter-report links into in-page anchors: `foo/bar.md#x` -> `#bar`."""
    def repl_md(m):
        path = m.group(1)
        if path.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)
        return "](#%s)" % norm_stem(path.split("#")[0])

    text = re.sub(r"\]\(([^)\s]+\.md(?:#[^)\s]*)?)\)", repl_md, text)

    def repl_html(m):
        path = m.group(1)
        if path.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)
        return 'href="#%s"' % norm_stem(path.split("#")[0])

    return re.sub(r'href="([^"]+\.md(?:#[^"]*)?)"', repl_html, text)


def rewrite_images(text, doc_dir, out_dir):
    """Re-base relative image paths from the document's directory onto the output file's
    directory, so `![…](figures/x.png)` in reports/03_domain/ still resolves when the report
    lives in reports/report/. Absolute paths, URLs and data URIs are left alone."""
    def rebase(src):
        if src.startswith(("http://", "https://", "data:", "/", "#")):
            return src
        target = os.path.normpath(os.path.join(doc_dir, src))
        return os.path.relpath(target, out_dir).replace(os.sep, "/")

    text = re.sub(r"(!\[[^\]]*\]\()([^)\s]+)(\))",
                  lambda m: m.group(1) + rebase(m.group(2)) + m.group(3), text)
    return re.sub(r'(<img\b[^>]*\bsrc=")([^"]+)(")',
                  lambda m: m.group(1) + rebase(m.group(2)) + m.group(3), text)


def extract_fences(text):
    """Lift fenced blocks out before Markdown conversion so their bodies stay verbatim."""
    fences = []

    def repl(m):
        idx = len(fences)
        fences.append((m.group("lang").strip(), m.group("body")))
        return "\n\nZQFENCEZQ%dZQENDZQ\n\n" % idx

    return FENCE_PATTERN.sub(repl, text), fences


def shift_headings(text, delta=1, max_level=6):
    """The document's own `title` becomes the article h1, so its body headings move down."""
    def repl(m):
        level = min(len(m.group(1)) + delta, max_level)
        return "#" * level + m.group(2)

    return re.sub(r"^(#{1,6})(\s+.*)$", repl, text, flags=re.M)


def render_fence(lang, body):
    """Mermaid bodies are escaped exactly once inside `<pre class="mermaid">`; the browser
    unescapes them before Mermaid parses, which is what keeps `<br/>` labels working."""
    lang = (lang or "").strip()
    if lang.lower() == "mermaid":
        return '<div class="mermaid-wrap"><pre class="mermaid">%s</pre></div>' % html.escape(body)
    cls = ' class="language-%s"' % html.escape(lang) if lang else ""
    return "<pre><code%s>%s\n</code></pre>" % (cls, html.escape(body))


def substitute_fences(html_text, fences):
    for idx, (lang, body) in enumerate(fences):
        token = "ZQFENCEZQ%dZQENDZQ" % idx
        rendered = render_fence(lang, body)
        html_text = html_text.replace("<p>%s</p>" % token, rendered)
        html_text = html_text.replace(token, rendered)
    return html_text


# ------------------------------------------------------------- pipe-table helpers
def split_cells(line):
    """`| a | **b** | c |` -> ['a', '**b**', 'c']; an escaped pipe stays in its cell."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


def is_separator_row(cells):
    return bool(cells) and all(set(c) <= set("-: ") for c in cells)


def id_table(text, prefix):
    """(header cells, {id: cells}) of the first pipe table whose first column holds
    `<prefix>-###` ids. The header is returned as written so the summary can reuse the
    document's own column names in the document's own language."""
    header, rows = None, {}
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            if rows:
                break
            header = None
            continue
        cells = split_cells(line)
        if header is None:
            header = cells
            continue
        if is_separator_row(cells):
            continue
        if cells and re.fullmatch(prefix + r"-\d{3}", cells[0]):
            rows[cells[0]] = cells
    return (header or []), rows


# `TBD`, `TBD-assumption`, optionally followed by `(OQ-###)` in ASCII or full-width
# parentheses — the Japanese documents write `TBD（OQ-012）`.
TBD_PATTERN = re.compile(r"\bTBD(-assumption)?\b(?:\s*[（(]\s*(OQ-\d{3})\s*[)）])?")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCT_MANIFEST = os.path.join(REPO_ROOT, "skills", "product", "common",
                                "skill-dependencies.yaml")


def load_manifest_ranks(path=PRODUCT_MANIFEST):
    """{declared output path: rank} in manifest order — which is pipeline order, the
    manifest being what `/product:start` reads to sequence the phases. `{}` when the
    manifest cannot be read, so ordering degrades to name order rather than failing."""
    try:
        data = yaml.safe_load(read(path)) or {}
    except Exception:
        return {}
    ranks = {}
    for i, spec in enumerate((data.get("phases") or {}).values()):
        for j, out in enumerate((spec or {}).get("outputs") or []):
            ranks.setdefault(str(out), (i, j))
    return ranks


class ReportBuilder:
    layout = "architect"
    title_key = "report_title"
    pipeline_key = "pipeline_meta"
    summary_key = "sec_summary"
    default_output = ("reports", "00_summary", "full-report.html")
    section_ids = ("investigation", "analysis", "evaluation", "design", "stories",
                   "implementation", "test-specs", "review")

    def __init__(self, project_dir, lang="en", mermaid_js=None, output_dir=None):
        self.project_dir = project_dir
        self.lang_index = LANGS.index(lang) if lang in LANGS else 0
        self.lang = LANGS[self.lang_index]
        self.mermaid_js_override = mermaid_js
        # Where the HTML will live — relative image paths are re-based onto it.
        self.output_dir = output_dir or os.path.join(project_dir, *self.default_output[:-1])
        self.article_count = 0
        self.mermaid_count = 0
        # Section anchors are reserved so a document named summary.md or review.md
        # cannot collide with the <section>/<h2> that carries the same id.
        self.ids_seen = {"summary", *self.section_ids}
        self.articles = []

    # ------------------------------------------------------------------ helpers
    def t(self, key):
        return UI[key][self.lang_index]

    def path(self, *parts):
        return os.path.join(self.project_dir, *parts)

    def register_id(self, stem):
        if stem in self.ids_seen:
            n = 2
            candidate = "%s-%d" % (stem, n)
            while candidate in self.ids_seen:
                n += 1
                candidate = "%s-%d" % (stem, n)
            stem = candidate
        self.ids_seen.add(stem)
        return stem

    # ------------------------------------------------------------- article render
    def render_markdown_file(self, path):
        raw = read(path)
        meta, body = parse_frontmatter(raw)
        title = str(meta.get("title", os.path.basename(path))).strip()
        body_protected, fences = extract_fences(body)
        body_protected = rewrite_links(body_protected)
        body_protected = rewrite_images(body_protected, os.path.dirname(path), self.output_dir)
        body_protected = shift_headings(body_protected, delta=2)
        body_html = markdown.markdown(
            body_protected, extensions=MD_EXTENSIONS, output_format="html5")
        body_html = substitute_fences(body_html, fences)

        stem = self.register_id(norm_stem(path))
        relpath = os.path.relpath(path, self.project_dir).replace(os.sep, "/")
        mermaid_count = sum(1 for lang, _ in fences if lang.strip().lower() == "mermaid")
        self.mermaid_count += mermaid_count
        self.article_count += 1

        # TBD placeholders are counted on the body (frontmatter excluded) and indexed per
        # article; the product summary lists them, the architect summary ignores them.
        hits = TBD_PATTERN.findall(body)
        tbd_asm = sum(1 for kind, _ in hits if kind)
        self.articles.append({
            "id": stem, "title": title, "relpath": relpath,
            "tbd": len(hits) - tbd_asm, "tbd_assumption": tbd_asm,
            "oq_refs": sorted({oq for _, oq in hits if oq}),
        })

        article = (
            '<article class="doc" id="%s"><h3 class="doc-title">%s'
            '<span class="src">%s</span></h3>%s</article>'
            % (html.escape(stem, quote=True), html.escape(title),
               html.escape(relpath), body_html)
        )
        return {"id": stem, "title": title, "html": article}

    def inline_md(self, cell):
        """Bold, code and links inside a table cell, through the same converter as the body."""
        out = markdown.markdown(rewrite_links(cell), extensions=MD_EXTENSIONS,
                                output_format="html5").strip()
        return re.sub(r"^<p>|</p>$", "", out)

    def render_feature_file(self, path):
        text = read(path)
        m = re.search(r"^\s*Feature:\s*(.+)$", text, re.M)
        stem = norm_stem(path)
        heading = m.group(1).strip() if m else stem
        relpath = os.path.relpath(path, self.project_dir)
        art_id = self.register_id("feature-%s" % stem)
        self.article_count += 1
        article = (
            '<article class="doc" id="%s"><h3 class="doc-title">%s'
            '<span class="src">%s</span></h3>'
            '<pre><code class="language-gherkin">%s\n</code></pre></article>'
            % (html.escape(art_id, quote=True), html.escape(heading),
               html.escape(relpath), html.escape(text))
        )
        return {"id": art_id, "title": heading, "html": article}

    def subgroup(self, title, articles_html):
        return '<div class="subgroup"><h3 class="subgroup-title">%s</h3>%s</div>' % (
            html.escape(title), "".join(articles_html))

    def render_dir(self, directory, toc):
        """Every top-level `.md` in `directory`, name order. Returns article HTML."""
        if not os.path.isdir(directory):
            return []
        out = []
        for fname in sorted(f for f in os.listdir(directory) if f.endswith(".md")):
            doc = self.render_markdown_file(os.path.join(directory, fname))
            out.append(doc["html"])
            toc.append((doc["id"], doc["title"]))
        return out

    @staticmethod
    def section(section_id, heading, articles):
        return '<section class="phase"><h2 id="%s">%s</h2>%s</section>' % (
            section_id, heading, "".join(articles))

    # --------------------------------------------------------------- sections
    def simple_section(self, section_id, heading_key, directory):
        toc = []
        articles = self.render_dir(self.path(directory), toc)
        if not articles:
            return None, []
        return self.section(section_id, self.t(heading_key), articles), toc

    def investigation_section(self):
        """`reports/before/<project>/` — one subgroup per project directory found."""
        base = self.path("reports", "before")
        if not os.path.isdir(base):
            return None, []
        toc = []
        # Loose Markdown directly under reports/before/ still belongs to the section.
        articles = self.render_dir(base, toc)
        for project_dir in sorted(p for p in glob.glob(os.path.join(base, "*"))
                                  if os.path.isdir(p)):
            sub = self.render_dir(project_dir, toc)
            if sub:
                articles.append(self.subgroup(os.path.basename(project_dir), sub))
        if not articles:
            return None, []
        return self.section("investigation", self.t("sec_investigation"), articles), toc

    def yaml_info_title(self, path):
        try:
            data = yaml.safe_load(read(path))
            info = (data or {}).get("info") or {}
            return info.get("title", self.t("no_info_title"))
        except Exception as exc:
            return self.t("parse_error") % exc

    def design_section(self):
        base = self.path("reports", "03_design")
        if not os.path.isdir(base):
            return None, []
        toc = []
        articles = self.render_dir(base, toc)

        # ADR: index.md first, then adr-NNN in id order.
        adr_dir = os.path.join(base, "adr")
        if os.path.isdir(adr_dir):
            def adr_key(f):
                if f == "index.md":
                    return (0, 0, f)
                m = re.match(r"adr-(\d+)", f)
                return (1, int(m.group(1)) if m else 9999, f)

            sub = []
            for fname in sorted((f for f in os.listdir(adr_dir) if f.endswith(".md")),
                                key=adr_key):
                doc = self.render_markdown_file(os.path.join(adr_dir, fname))
                sub.append(doc["html"])
                toc.append((doc["id"], doc["title"]))
            if sub:
                articles.append(self.subgroup(self.t("sub_adr"), sub))

        for subdir, key in (("aggregates", "sub_aggregates"),
                            ("state-machines", "sub_state_machines")):
            sub = self.render_dir(os.path.join(base, subdir), toc)
            if sub:
                articles.append(self.subgroup(self.t(key), sub))

        api_sub = self.api_specifications(base, toc)
        if api_sub:
            articles.append(api_sub)

        if not articles:
            return None, []
        return self.section("design", self.t("sec_design"), articles), toc

    def api_specifications(self, design_base, toc):
        api_dir = os.path.join(design_base, "api-specifications")
        if not os.path.isdir(api_dir):
            return None
        md_paths, yaml_paths = [], []
        for root, _dirs, files in os.walk(api_dir):
            for fname in files:
                if fname.endswith(".md"):
                    md_paths.append(os.path.join(root, fname))
                elif fname.endswith((".yaml", ".yml")):
                    yaml_paths.append(os.path.join(root, fname))
        md_paths.sort()
        yaml_paths.sort()

        sub = []
        if yaml_paths:
            rows = "".join(
                "<tr><td><code>%s</code></td><td>%s</td></tr>"
                % (html.escape(os.path.relpath(p, design_base)),
                   html.escape(str(self.yaml_info_title(p))))
                for p in yaml_paths)
            sub.append(
                '<div class="callout"><p><strong>%s</strong>%s</p>'
                '<table class="score-table"><thead><tr><th>%s</th><th>%s</th></tr></thead>'
                "<tbody>%s</tbody></table></div>"
                % (html.escape(self.t("api_table_caption")), self.t("api_table_note"),
                   html.escape(self.t("col_file")), html.escape(self.t("col_info_title")), rows))
        for p in md_paths:
            doc = self.render_markdown_file(p)
            sub.append(doc["html"])
            toc.append((doc["id"], doc["title"]))
        if not sub:
            return None
        return self.subgroup(self.t("sub_api_specs"), sub)

    def test_specs_section(self):
        base = self.path("reports", "07_test-specs")
        if not os.path.isdir(base):
            return None, []
        toc = []
        articles = self.render_dir(base, toc)

        bdd_dir = os.path.join(base, "bdd-scenarios")
        if os.path.isdir(bdd_dir):
            sub = self.render_dir(bdd_dir, toc)
            for fname in sorted(f for f in os.listdir(bdd_dir) if f.endswith(".feature")):
                doc = self.render_feature_file(os.path.join(bdd_dir, fname))
                sub.append(doc["html"])
                toc.append((doc["id"], doc["title"]))
            if sub:
                articles.append(self.subgroup(self.t("sub_bdd"), sub))

        if not articles:
            return None, []
        return self.section("test-specs", self.t("sec_test_specs"), articles), toc

    def review_section(self):
        base = self.path("reports", "review")
        if not os.path.isdir(base):
            return None, []
        toc = []
        doc_htmls = []
        for fname in ("review-synthesis.md", "report-quality-review.md"):
            p = os.path.join(base, fname)
            if os.path.exists(p):
                doc = self.render_markdown_file(p)
                doc_htmls.append(doc["html"])
                toc.append((doc["id"], doc["title"]))

        rows = []
        for f in sorted(glob.glob(os.path.join(base, "individual", "*.json"))):
            try:
                data = json.loads(read(f))
            except Exception:
                continue
            total = sum(len(dim.get("findings", [])) for dim in data.get("dimensions", []))
            rows.append({
                "name": data.get("perspective", os.path.basename(f)),
                "score": data.get("weighted_score"),
                "timestamp": data.get("timestamp", ""),
                "count": total,
            })
        rows.sort(key=lambda r: r["name"])

        articles = []
        if rows:
            rows_html = "".join(
                '<tr><td><code>%s</code></td><td class="num">%s</td><td>%s</td>'
                '<td class="num">%s</td></tr>'
                % (html.escape(str(r["name"])),
                   "%.2f" % r["score"] if isinstance(r["score"], (int, float))
                   else html.escape(str(r["score"])),
                   html.escape(str(r["timestamp"])), r["count"])
                for r in rows)
            articles.append(
                '<div class="callout"><p><strong>%s</strong></p>'
                '<table class="score-table"><thead><tr><th>%s</th><th>%s</th><th>%s</th>'
                "<th>%s</th></tr></thead><tbody>%s</tbody></table></div>"
                % (html.escape(self.t("review_table_caption")),
                   html.escape(self.t("col_perspective")), html.escape(self.t("col_score")),
                   html.escape(self.t("col_run_at")), html.escape(self.t("col_findings")),
                   rows_html))
        articles += doc_htmls
        if not articles:
            return None, []
        return self.section("review", self.t("sec_review"), articles), toc

    # ---------------------------------------------------------- executive summary
    def open_question_rows(self):
        """Latest row per OQ- id from the one store, work/context.md § Open Questions,
        header-driven so both the 4-column and the 8-column table shapes parse
        (rules/open-questions.md §6). Any `| ID | …` line starts a new table. `None`
        when the store does not exist."""
        path = self.path("work", "context.md")
        if not os.path.exists(path):
            return None
        header, latest = None, {}
        for line in read(path).splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = split_cells(line)
            if cells and cells[0].lower() == "id":
                header = [c.lower() for c in cells]
                continue
            if not header or not cells or not re.fullmatch(r"OQ-\d{3}", cells[0]):
                continue
            row = dict(zip(header, cells))
            row["status_raw"] = row.get("status", "")
            m = re.match(r"[a-z-]+", row["status_raw"].lower())
            row["status"] = m.group(0) if m else row["status_raw"]
            latest[cells[0]] = row
        return list(latest.values())

    def open_questions(self):
        """Count per status — the shape the executive summary table renders."""
        counts = {}
        for row in self.open_question_rows() or []:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        return counts

    def summary_section(self, progress, synthesis, oq_counts):
        options = progress.get("options", {}) or {}
        lede = self.t("summary_lede") % {
            "docs": self.article_count,
            "project": "<code>%s</code>" % html.escape(str(progress.get("project_name", ""))),
            "pipeline": html.escape(self.t("pipeline_meta")),
            "workflow": html.escape(str(options.get("workflow_type", ""))),
            "scalardb": str(options.get("scalardb_enabled")).lower(),
        }

        if synthesis is None:
            return (
                '<section id="summary" class="doc verdict-section">'
                "<h2>%s</h2>"
                '<div class="verdict-banner warn"><div class="verdict-label">%s</div>'
                '<div class="verdict-value">—</div></div>'
                '<p class="lede">%s</p><p class="note">%s</p></section>'
                % (html.escape(self.t("sec_summary")), html.escape(self.t("verdict_label")),
                   lede, self.t("review_not_run")))

        verdict = synthesis.get("verdict", "?")
        agg = synthesis.get("aggregate_score")
        generated_at = synthesis.get("generated_at", "")
        gate = synthesis.get("gate_evaluation", {}) or {}
        fsum = synthesis.get("findings_summary", {}) or {}
        by_priority = fsum.get("by_priority", {}) or {}
        by_severity = fsum.get("by_severity", {}) or {}

        verdict_class = ("fail" if verdict == "FAIL"
                         else "warn" if verdict == "CONDITIONAL_PASS" else "ok")
        agg_text = "%.2f" % agg if isinstance(agg, (int, float)) else html.escape(str(agg))

        score_rows = "".join(
            '<tr><td><code>%s</code></td><td class="num">%s</td></tr>'
            % (html.escape(str(k)), "%.2f" % v if isinstance(v, (int, float))
               else html.escape(str(v)))
            for k, v in sorted((synthesis.get("perspective_scores", {}) or {}).items(),
                               key=lambda kv: -kv[1] if isinstance(kv[1], (int, float)) else 0))

        stat_grid = "".join(
            '<div class="stat%s"><div class="stat-num">%s</div><div class="stat-cap">%s</div></div>'
            % (cls, by_priority.get(p, 0), p)
            for p, cls in (("P0", " p0"), ("P1", " p1"), ("P2", ""), ("P3", "")))

        oq_rows = "".join(
            '<tr><td>%s</td><td class="num">%d</td></tr>'
            % (html.escape(self.t(OQ_STATUS_KEYS[s]) if s in OQ_STATUS_KEYS else s), c)
            for s, c in sorted(oq_counts.items(), key=lambda kv: -kv[1]))

        gate_pass = gate.get("PASS", {}) or {}
        gate_cond = gate.get("CONDITIONAL_PASS", {}) or {}

        findings_note = self.t("findings_note") % {
            "total": fsum.get("total", "?"), "after_dedup": fsum.get("after_dedup", "?"),
            "reported": fsum.get("reported", "?"), "active": fsum.get("active", "?"),
            "resolved": fsum.get("resolved_by_revision", "?"),
            "critical": by_severity.get("critical", "?"), "major": by_severity.get("major", "?"),
            "minor": by_severity.get("minor", "?"), "info": by_severity.get("info", "?"),
        }
        oq_note = self.t("oq_note") % {"total": sum(oq_counts.values())}

        return f"""
<section id="summary" class="doc verdict-section">
  <h2>{html.escape(self.t('sec_summary'))}</h2>
  <div class="verdict-banner {verdict_class}">
    <div class="verdict-label">{html.escape(self.t('verdict_label'))}</div>
    <div class="verdict-value">{html.escape(str(verdict))}</div>
    <div class="verdict-score">{html.escape(self.t('verdict_score'))} <strong>{agg_text}</strong> / 5.00
      ({html.escape(self.t('verdict_generated'))}: {html.escape(str(generated_at))})</div>
  </div>
  <p class="lede">{lede}</p>
  <p class="note">{html.escape(str(fsum.get('note', '')))}</p>

  <h3>{html.escape(self.t('h_perspective_scores'))}</h3>
  <table class="score-table"><thead><tr><th>{html.escape(self.t('col_perspective'))}</th>
  <th>{html.escape(self.t('col_score'))}</th></tr></thead><tbody>{score_rows}</tbody></table>

  <h3>{html.escape(self.t('h_gate_conditions'))}</h3>
  <table class="score-table">
    <thead><tr><th>{html.escape(self.t('col_verdict'))}</th>
    <th>{html.escape(self.t('col_met'))}</th>
    <th>{html.escape(self.t('col_violations'))}</th></tr></thead>
    <tbody>
      <tr><td>PASS</td><td>{"o" if gate_pass.get("met") else "x"}</td>
      <td>{html.escape("; ".join(gate_pass.get("violations", [])) or "-")}</td></tr>
      <tr><td>CONDITIONAL PASS</td><td>{"o" if gate_cond.get("met") else "x"}</td>
      <td>{html.escape("; ".join(gate_cond.get("violations", [])) or "-")}</td></tr>
    </tbody>
  </table>

  <h3>{html.escape(self.t('h_findings_by_priority'))}</h3>
  <div class="stat-grid">{stat_grid}</div>
  <p class="note">{findings_note}</p>

  <h3>{html.escape(self.t('h_open_questions'))}</h3>
  <table class="score-table"><thead><tr><th>{html.escape(self.t('col_status'))}</th>
  <th>{html.escape(self.t('col_count'))}</th></tr></thead><tbody>{oq_rows}</tbody></table>
  <p class="note">{oq_note}</p>
</section>
""".strip()

    # --------------------------------------------------------------------- mermaid
    def mermaid_candidates(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = []
        if self.mermaid_js_override:
            out.append(self.mermaid_js_override)
        out.append(os.path.join(repo, "tools", "docs-site", "node_modules",
                                "mermaid", "dist", "mermaid.min.js"))
        out.append(os.path.expanduser("~/.cache/nexus-architect/mermaid.min.js"))
        return out

    def mermaid_block(self):
        for candidate in self.mermaid_candidates():
            if candidate and os.path.exists(candidate):
                js = read(candidate).replace("</script", "<\\/script")
                return "<script>%s</script>" % js, "", candidate
        note = '<p class="note">%s</p>' % self.t("mermaid_cdn_note")
        return '<script src="%s"></script>' % CDN_URL, note, None

    # ------------------------------------------------------------------------ toc
    def build_toc(self, sections_toc):
        parts = ['<li class="nav-sec"><a href="#summary">%s</a></li>'
                 % html.escape(self.t(self.summary_key))]
        for sid, heading, entries in sections_toc:
            if not entries:
                continue
            inner = "".join(
                '<li><a href="#%s">%s</a></li>'
                % (html.escape(eid, quote=True), html.escape(title))
                for eid, title in entries)
            parts.append('<li class="nav-sec"><a href="#%s">%s</a><ul>%s</ul></li>'
                         % (html.escape(sid, quote=True), html.escape(heading), inner))
        return "".join(parts)

    # ---------------------------------------------------------------------- build
    def load_progress(self):
        progress_path = self.path("work", "pipeline-progress.json")
        if os.path.exists(progress_path):
            try:
                return json.loads(read(progress_path))
            except Exception:
                return {}
        return {}

    def render_summary(self, progress):
        """The section that opens the report. Architect: the quality gate verdict from
        the review synthesis; product overrides this with the validation status."""
        synthesis = None
        synthesis_path = self.path("reports", "review", "review-synthesis.json")
        if os.path.exists(synthesis_path):
            try:
                synthesis = json.loads(read(synthesis_path))
            except Exception:
                synthesis = None
        return self.summary_section(progress, synthesis, self.open_questions())

    def header_meta(self, progress, target_path, now):
        options = progress.get("options", {}) or {}
        return (
            f"{html.escape(self.t('pipeline_meta'))}\n"
            f"    (<code>workflow_type: {html.escape(str(options.get('workflow_type', '')))}</code>,\n"
            f"    <code>scalardb_enabled: {str(options.get('scalardb_enabled')).lower()}</code>,\n"
            f"    <code>output_language: {html.escape(self.lang)}</code>)<br>\n"
            f"    {html.escape(self.t('target'))}: <code>{html.escape(target_path)}</code> /\n"
            f"    {html.escape(self.t('documents'))}: {self.article_count}{self.t('count_unit')} /\n"
            f"    {html.escape(self.t('generated'))}: {now}"
        )

    def add_sections(self, add):
        add(self.investigation_section(), "investigation", "sec_investigation")
        add(self.simple_section("analysis", "sec_analysis", "reports/01_analysis"),
            "analysis", "sec_analysis")
        add(self.simple_section("evaluation", "sec_evaluation", "reports/02_evaluation"),
            "evaluation", "sec_evaluation")
        add(self.design_section(), "design", "sec_design")
        add(self.simple_section("stories", "sec_stories", "reports/04_stories"),
            "stories", "sec_stories")
        add(self.simple_section("implementation", "sec_implementation",
                                "reports/06_implementation"),
            "implementation", "sec_implementation")
        add(self.test_specs_section(), "test-specs", "sec_test_specs")
        add(self.review_section(), "review", "sec_review")

    def build(self):
        progress = self.load_progress()

        sections_toc = []
        body_sections = []

        def add(result, sid, heading_key):
            section_html, toc = result
            if section_html:
                body_sections.append(section_html)
                sections_toc.append((sid, self.t(heading_key), toc))

        self.add_sections(add)

        summary_html = self.render_summary(progress)
        toc_html = self.build_toc(sections_toc)
        mermaid_script, mermaid_note, mermaid_src = self.mermaid_block()

        now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        project_name = str(progress.get("project_name", "") or os.path.basename(
            os.path.abspath(self.project_dir)))
        target_path = str(progress.get("target_path", ""))
        doc_title = "%s — %s" % (project_name, self.t(self.title_key))
        meta_html = self.header_meta(progress, target_path, now)

        html_doc = f"""<!DOCTYPE html>
<html lang="{self.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(doc_title)}</title>
<style>
{CSS}
</style>
</head>
<body>
<div id="layout">
<nav id="sidebar"><h2>{html.escape(self.t('toc'))}</h2><ul>{toc_html}</ul></nav>
<main>
<header class="rep">
  <h1>{html.escape(doc_title)}</h1>
  <div class="meta">
    {meta_html}
  </div>
  {mermaid_note}
</header>
{summary_html}
{"".join(body_sections)}
</main>
</div>
{mermaid_script}
<script>
mermaid.initialize({{startOnLoad:true, securityLevel:'loose', theme: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'default'}});
</script>
</body>
</html>
"""
        return html_doc, mermaid_src


# ------------------------------------------------------------------ product layout
PRODUCT_MARKERS = ("00_core", "01_ux", "02_spec", "03_domain")
PRODUCT_SECTIONS = (            # (section id, UI key, directory under reports/)
    ("core", "sec_core", "00_core"),
    ("ux", "sec_ux", "01_ux"),
    ("spec", "sec_spec", "02_spec"),
    ("domain", "sec_domain", "03_domain"),
    ("quality", "sec_quality", "04_quality"),
    ("adaptation", "sec_adaptation", "05_adaptation"),
)
KNOWN_PRODUCT_DIRS = {d for _, _, d in PRODUCT_SECTIONS} | {"report"}
SUBGROUP_KEYS = {"domain-stories": "sub_domain_stories", "examples": "sub_examples",
                 "ui-mocks": "sub_ui_mocks"}
# Listed by name, never embedded: UI mocks, figures, slides, exported diagrams.
ASSET_EXTS = (".html", ".png", ".jpg", ".jpeg", ".svg", ".gif", ".drawio", ".pdf")
OQ_STATUS_ORDER = ("deferred", "unasked", "external", "answered")


def detect_layout(project_dir):
    reports = os.path.join(project_dir, "reports")
    if any(os.path.isdir(os.path.join(reports, d)) for d in PRODUCT_MARKERS):
        return "product"
    return "architect"


class ProductReportBuilder(ReportBuilder):
    """The `/product:report` rendering: the same article/fence/anchor contract, a
    different section tree, and "Key Assumptions & Validation Status" up front."""
    layout = "product"
    title_key = "report_title_product"
    pipeline_key = "pipeline_meta_product"
    summary_key = "sec_summary_product"
    default_output = ("reports", "report", "full-report.html")
    section_ids = tuple(s for s, _, _ in PRODUCT_SECTIONS) + ("other", "review")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ranks = load_manifest_ranks()

    # ------------------------------------------------------------- ordering
    def manifest_key(self, path):
        """Sort key: index.md first, then the manifest (pipeline) rank of the file or of
        the declared directory holding it, then the file name."""
        rel = os.path.relpath(path, self.project_dir).replace(os.sep, "/")
        rank = self.ranks.get(rel)
        if rank is None:
            rank = self.ranks.get(os.path.dirname(rel) + "/")
        return (0 if os.path.basename(path) == "index.md" else 1,
                rank if rank is not None else (10 ** 6, 0),
                os.path.basename(path))

    def render_ordered(self, directory, toc):
        if not os.path.isdir(directory):
            return []
        paths = [os.path.join(directory, f) for f in os.listdir(directory)
                 if f.endswith(".md") and not f.startswith(".")]
        out = []
        for p in sorted(paths, key=self.manifest_key):
            doc = self.render_markdown_file(p)
            out.append(doc["html"])
            toc.append((doc["id"], doc["title"]))
        return out

    def asset_table(self, directory):
        names = sorted(f for f in os.listdir(directory)
                       if f.lower().endswith(ASSET_EXTS) and not f.startswith("."))
        if not names:
            return None
        rel = os.path.relpath(directory, self.project_dir).replace(os.sep, "/")
        rows = "".join("<tr><td><code>%s</code></td></tr>" % html.escape(n) for n in names)
        return (
            '<div class="callout"><p><strong>%s</strong></p>'
            '<table class="score-table"><thead><tr><th>%s</th></tr></thead>'
            "<tbody>%s</tbody></table></div>"
            % (html.escape(self.t("asset_table_caption") % rel),
               html.escape(self.t("col_file")), rows))

    # -------------------------------------------------------------- sections
    def product_section(self, section_id, heading_key, base):
        if not os.path.isdir(base):
            return None, []
        toc = []
        articles = self.render_ordered(base, toc)
        for name in sorted(os.listdir(base)):
            sub_dir = os.path.join(base, name)
            if name.startswith(".") or not os.path.isdir(sub_dir):
                continue
            sub = self.render_ordered(sub_dir, toc)
            assets = self.asset_table(sub_dir)
            if assets:
                sub.append(assets)
            if sub:
                title = self.t(SUBGROUP_KEYS[name]) if name in SUBGROUP_KEYS else name
                articles.append(self.subgroup(title, sub))
        if not articles:
            return None, []
        return self.section(section_id, self.t(heading_key), articles), toc

    def other_section(self):
        base = self.path("reports")
        toc = []
        articles = []
        for name in sorted(os.listdir(base)):
            d = os.path.join(base, name)
            if name.startswith(".") or name in KNOWN_PRODUCT_DIRS or not os.path.isdir(d):
                continue
            sub = self.render_dir(d, toc)
            if sub:
                articles.append(self.subgroup(name, sub))
        if not articles:
            return None, []
        return self.section("other", self.t("sec_other"), articles), toc

    def add_sections(self, add):
        for sid, key, d in PRODUCT_SECTIONS:
            add(self.product_section(sid, key, self.path("reports", d)), sid, key)
        add(self.other_section(), "other", "sec_other")
        add(self.simple_section("review", "sec_review", "reports/report"),
            "review", "sec_review")

    # --------------------------------------------------------------- summary
    def header_meta(self, progress, target_path, now):
        options = progress.get("options", {}) or {}
        return (
            f"{html.escape(self.t('pipeline_meta_product'))}\n"
            f"    (<code>profile: {html.escape(str(options.get('profile', '')))}</code>,\n"
            f"    <code>output_language: {html.escape(self.lang)}</code>)<br>\n"
            f"    {html.escape(self.t('documents'))}: {self.article_count}{self.t('count_unit')} /\n"
            f"    {html.escape(self.t('generated'))}: {now}"
        )

    def asm_table(self, relpath, open_ids):
        """The open ASM- rows of one source document, header and cells verbatim."""
        path = self.path(*relpath.split("/"))
        if not os.path.exists(path):
            return None
        header, rows = id_table(read(path), "ASM")
        if not header:
            return None
        body = []
        for asm in open_ids:
            cells = rows.get(asm)
            if cells is None:
                body.append('<tr><td><code>%s</code></td><td colspan="%d">%s</td></tr>'
                            % (html.escape(asm), max(len(header) - 1, 1),
                               html.escape(self.t("asm_missing") % relpath)))
                continue
            cells = (cells + [""] * len(header))[:len(header)]
            body.append("<tr>%s</tr>" % "".join(
                "<td>%s</td>" % self.inline_md(c) for c in cells))
        head = "".join("<th>%s</th>" % self.inline_md(h) for h in header)
        anchor = norm_stem(path)
        return (
            '<p class="note">%s</p>'
            '<table class="score-table"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
            % (self.t("asm_source_note") % ('<a href="#%s">%s</a>'
                                            % (html.escape(anchor, quote=True),
                                               html.escape(relpath))),
               head, "".join(body)))

    def tbd_table(self):
        rows = [a for a in self.articles if a["tbd"] or a["tbd_assumption"]]
        if not rows:
            return '<p class="note">%s</p>' % self.t("tbd_none")
        body = "".join(
            '<tr><td><a href="#%s">%s</a> <code>%s</code></td><td class="num">%d</td>'
            '<td class="num">%d</td><td>%s</td></tr>'
            % (html.escape(a["id"], quote=True), html.escape(a["title"]),
               html.escape(a["relpath"]), a["tbd"], a["tbd_assumption"],
               ", ".join("<code>%s</code>" % html.escape(o) for o in a["oq_refs"]) or "-")
            for a in rows)
        note = self.t("tbd_note") % {
            "tbd": sum(a["tbd"] for a in rows),
            "asm": sum(a["tbd_assumption"] for a in rows),
            "docs": len(rows),
        }
        return (
            '<table class="score-table"><thead><tr><th>%s</th><th>%s</th><th>%s</th>'
            "<th>%s</th></tr></thead><tbody>%s</tbody></table><p class=\"note\">%s</p>"
            % (html.escape(self.t("col_document")), html.escape(self.t("col_tbd")),
               html.escape(self.t("col_tbd_assumption")), html.escape(self.t("col_oq_refs")),
               body, note))

    def oq_tables(self, rows):
        if rows is None:
            return '<p class="note">%s</p>' % self.t("oq_store_missing")
        by_status = {}
        for r in rows:
            by_status.setdefault(r["status"], []).append(r)

        def status_rank(s):
            return (OQ_STATUS_ORDER.index(s) if s in OQ_STATUS_ORDER
                    else len(OQ_STATUS_ORDER), s)

        parts = []
        for status in sorted(by_status, key=status_rank):
            group = by_status[status]
            if status == "answered":
                parts.append('<p class="note">%s</p>'
                             % (self.t("oq_answered_count") % {"count": len(group)}))
                continue
            label = self.t(OQ_STATUS_KEYS[status]) if status in OQ_STATUS_KEYS else status
            body = "".join(
                "<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td></tr>"
                % (html.escape(r.get("id", "")), self.inline_md(r.get("question", "")),
                   self.inline_md(r.get("owner", "")), self.inline_md(r.get("impact", "")))
                for r in group)
            parts.append(
                "<h4>%s (%d)</h4>"
                '<table class="score-table"><thead><tr><th>%s</th><th>%s</th><th>%s</th>'
                "<th>%s</th></tr></thead><tbody>%s</tbody></table>"
                % (html.escape(label), len(group), html.escape(self.t("col_id")),
                   html.escape(self.t("col_question")), html.escape(self.t("col_owner")),
                   html.escape(self.t("col_impact")), body))

        counts = {}
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        count_rows = "".join(
            '<tr><td>%s</td><td class="num">%d</td></tr>'
            % (html.escape(self.t(OQ_STATUS_KEYS[s]) if s in OQ_STATUS_KEYS else s), c)
            for s, c in sorted(counts.items(), key=lambda kv: -kv[1]))
        parts.append(
            '<table class="score-table"><thead><tr><th>%s</th><th>%s</th></tr></thead>'
            "<tbody>%s</tbody></table><p class=\"note\">%s</p>"
            % (html.escape(self.t("col_status")), html.escape(self.t("col_count")),
               count_rows, self.t("oq_note") % {"total": len(rows)}))
        return "".join(parts)

    def render_summary(self, progress):
        options = progress.get("options", {}) or {}
        gate = ((progress.get("gates") or {}).get("validate-assumptions")) or None
        lede = self.t("summary_lede_product") % {
            "docs": self.article_count,
            "project": "<code>%s</code>" % html.escape(str(progress.get("project_name", ""))),
            "pipeline": html.escape(self.t("pipeline_meta_product")),
            "profile": html.escape(str(options.get("profile", ""))),
        }

        if gate:
            verdict = str(gate.get("verdict", "?"))
            v = verdict.lower()
            verdict_class = "ok" if v == "go" else "fail" if v == "no-go" else "warn"
            evaluated = str(gate.get("evaluated_at", ""))
            banner = (
                '<div class="verdict-banner %s"><div class="verdict-label">%s</div>'
                '<div class="verdict-value">%s</div>'
                '<div class="verdict-score">%s: %s</div></div>'
                % (verdict_class, html.escape(self.t("gate_label")),
                   html.escape(verdict.upper()), html.escape(self.t("gate_evaluated")),
                   html.escape(evaluated)))
            gate_note = ""
            open_ids = [str(a) for a in (gate.get("open_assumptions") or [])]
        else:
            banner = (
                '<div class="verdict-banner warn"><div class="verdict-label">%s</div>'
                '<div class="verdict-value">—</div></div>'
                % html.escape(self.t("gate_label")))
            gate_note = '<p class="note">%s</p>' % self.t("gate_not_run")
            open_ids = []

        assumptions_html = []
        if not os.path.exists(self.path("reports", "00_core", "assumptions.md")):
            assumptions_html.append('<p class="note">%s</p>' % self.t("assumptions_missing"))
        elif open_ids:
            assumptions_html.append('<p class="note">%s</p>' % (
                self.t("open_assumptions_note") % {"count": len(open_ids)}))
            for rel in ("reports/00_core/assumptions.md", "reports/00_core/validation-plan.md"):
                table = self.asm_table(rel, open_ids)
                if table:
                    assumptions_html.append(table)

        return (
            '<section id="summary" class="doc verdict-section"><h2>%s</h2>%s%s'
            '<p class="lede">%s</p>'
            "<h3>%s</h3>%s"
            "<h3>%s</h3>%s"
            "<h3>%s</h3>%s</section>"
            % (html.escape(self.t("sec_summary_product")), banner, gate_note, lede,
               html.escape(self.t("h_open_assumptions")), "".join(assumptions_html),
               html.escape(self.t("h_tbd")), self.tbd_table(),
               html.escape(self.t("h_oq_by_status")), self.oq_tables(self.open_question_rows())))


BUILDERS = {"architect": ReportBuilder, "product": ProductReportBuilder}


def resolve_language(project_dir):
    path = os.path.join(project_dir, "work", "pipeline-progress.json")
    if not os.path.exists(path):
        return "en"
    try:
        progress = json.loads(read(path))
    except Exception:
        return "en"
    lang = ((progress.get("options") or {}).get("output_language") or "en")
    return lang if lang in LANGS else "en"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="build-report.py",
        description="Build the consolidated HTML report for a nexus-architect project: "
                    "reports/00_summary/full-report.html (architect layout) or "
                    "reports/report/full-report.html (product layout).")
    parser.add_argument("project_dir", nargs="?", default=".",
                        help="project root holding reports/ and work/ (default: cwd)")
    parser.add_argument("--output", default=None,
                        help="output path (default: the layout's canonical path)")
    parser.add_argument("--mermaid-js", default=None,
                        help="path to mermaid.min.js to inline, tried before the defaults")
    parser.add_argument("--layout", choices=sorted(BUILDERS), default=None,
                        help="report tree layout (default: detected from reports/)")
    parser.add_argument("--lang", choices=LANGS, default=None,
                        help="UI language (default: options.output_language of the project)")
    args = parser.parse_args(argv)

    project_dir = os.path.abspath(args.project_dir)
    if not os.path.isdir(os.path.join(project_dir, "reports")):
        sys.stderr.write(
            "build-report: %s has no reports/ directory — is this a nexus-architect project?\n"
            % project_dir)
        return 1

    layout = args.layout or detect_layout(project_dir)
    builder_cls = BUILDERS[layout]
    out_path = args.output or os.path.join(project_dir, *builder_cls.default_output)
    out_path = os.path.abspath(out_path)
    builder = builder_cls(project_dir, lang=args.lang or resolve_language(project_dir),
                          mermaid_js=args.mermaid_js, output_dir=os.path.dirname(out_path))
    html_doc, mermaid_src = builder.build()

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)

    print("build-report: %d articles, %d mermaid blocks, %d bytes, mermaid=%s, layout=%s -> %s"
          % (builder.article_count, builder.mermaid_count, os.path.getsize(out_path),
             mermaid_src or "cdn", layout, out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
