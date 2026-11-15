#!/usr/bin/env python3
"""Contract test for tools/lib/report_review.py — the five report dimensions, measured.

Usage: python3 tools/lib/report_review.test.py     (exit 1 on failure)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import report_review as R  # noqa: E402

FAILURES = 0


def check(name, cond, detail=""):
    global FAILURES
    print("  [%s] %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond or not detail else " -- %r" % (detail,)))
    if not cond:
        FAILURES += 1


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


PROGRESS = {
    "options": {"output_language": "en"},
    "phases": {
        "investigate": {"status": "completed", "outputs": ["reports/before/app/codebase-structure.md"]},
        "evaluate-mmi": {"status": "completed", "outputs": ["reports/02_evaluation/mmi-overview.md"]},
        "evaluate-ddd": {"status": "completed",
                         "outputs": ["reports/02_evaluation/ddd-tactical-architecture-evaluation.md"]},
        "design-aggregate": {"status": "completed", "outputs": ["reports/03_design/aggregates/aggregate-order.md"]},
        "create-domain-story": {"status": "completed", "outputs": ["reports/04_stories/domain-story-ordering.md"]},
        "review-risk": {"status": "completed", "outputs": ["reports/review/individual/review-risk.json"]},
        "review-synthesizer": {"status": "completed",
                               "outputs": ["reports/review/review-synthesis.md", "reports/review/review-synthesis.json"]},
        "report": {"status": "completed", "outputs": ["reports/00_summary/full-report.html"]},
        "analyze-ui": {"status": "skipped", "outputs": ["reports/01_analysis/ui-inventory.md"]},
    },
}
SYNTHESIS = {"verdict": "FAIL", "aggregate_score": 2.81,
             "perspective_scores": {"consistency": 3.7, "risk": 2.15},
             "findings": [{"id": "SYN-001", "priority": "P0"}, {"id": "SYN-002", "priority": "P1"},
                          {"id": "SYN-003", "priority": "P3"}]}

ARTICLE = '<article class="doc" id="%s"><h3 class="doc-title">%s<span class="src">x.md</span></h3>%s</article>'
TABLE = '<table><thead><tr><th>%s</th><th>Rule</th></tr></thead><tbody><tr><td>a</td><td>b</td></tr></tbody></table>'
MERMAID = '<div class="mermaid-wrap"><pre class="mermaid">%s</pre></div>'


def page(nav, body, title="app — System Architecture Consolidated Report", h1="<h1>app</h1>"):
    return ('<!doctype html><html><head><title>%s</title><style>.x{}</style></head><body>'
            '<nav id="sidebar"><h2>Contents</h2><ul>%s</ul></nav><main>%s%s</main>'
            '<script>mermaid.initialize({})</script></body></html>' % (title, nav, h1, body))


def good_html():
    nav = "".join('<li><a href="#%s">%s</a></li>' % (i, i) for i in (
        "summary", "codebase-structure", "mmi-overview", "ddd-tactical-architecture-evaluation",
        "aggregate-order", "domain-story-ordering", "review-synthesis"))
    summary = ('<section id="summary" class="doc verdict-section"><h2>Executive Summary</h2>'
               '<p>The review verdict is FAIL with an aggregate score of 2.81; consistency scored 3.7 and risk 2.15.</p>'
               '<p>System MMI 47.0% and DDD score 45.2% (weak alignment). Findings SYN-001 and SYN-002 are P1 or above.</p>'
               '</section>')
    body = summary + "".join([
        ARTICLE % ("codebase-structure", "Codebase", "<p>Twelve packages, one God service. The decision is TBD (OQ-001).</p>"
                   + MERMAID % 'flowchart LR\n  A["Order"] --> B["Stock"]\n  B --> C'),
        ARTICLE % ("mmi-overview", "MMI", "<p>Scores per module.</p>" + TABLE % "Module"),
        ARTICLE % ("ddd-tactical-architecture-evaluation", "DDD", "<p>Tactical design is weak.</p>"),
        ARTICLE % ("aggregate-order", "Order", "<p>The order aggregate.</p>" + TABLE % "Invariant"
                   + MERMAID % 'classDiagram\n  class Order {\n    +OrderId id\n  }\n  Order --> OrderLine'),
        ARTICLE % ("domain-story-ordering", "Ordering", "<p>A customer orders.</p>"
                   + MERMAID % 'sequenceDiagram\n  participant C as Customer\n  C-&gt;&gt;S: place order'),
        ARTICLE % ("review-synthesis", "Review", "<p>Nine critical findings.</p>" + TABLE % "ID"),
    ])
    return page(nav, body)


def main():
    root = tempfile.mkdtemp(prefix="nx-rr-")
    try:
        proj = os.path.join(root, "p")
        write(proj, "work/pipeline-progress.json", json.dumps(PROGRESS))
        write(proj, "reports/review/review-synthesis.json", json.dumps(SYNTHESIS))
        write(proj, "reports/02_evaluation/mmi-overview.md", "# MMI\n\n| Metric | Value |\n|---|---|\n| System Average MMI | 47.0% (6 packages) |\n")
        write(proj, "reports/02_evaluation/ddd-tactical-architecture-evaluation.md", "# DDD\n\n## Overall DDD Score: 45.2% (Weak alignment)\n")
        write(proj, "reports/03_design/aggregates/aggregate-order.md", "# Order\n")
        write(proj, "reports/04_stories/domain-story-ordering.md", "# Ordering\n")
        write(proj, "reports/04_stories/domain-story-catalog.md", "# Catalog of stories\n")

        print("no report yet")
        r = R.Review(proj).run()
        check("a project without the consolidated report is not measured", r["measured"] is False and "full-report" in r["reason"], r)

        print("a sound report")
        write(proj, "reports/00_summary/full-report.html", good_html())
        r = R.Review(proj).run()
        d = r["dimensions"]
        check("every dimension scores 5 and the verdict is PASS 5.0",
              all(d[k]["score"] == 5 for k in d) and r["verdict"] == "PASS" and r["weighted_score"] == 5.0 and r["findings"] == [],
              {k: (d[k]["score"], d[k]["findings"]) for k in d})
        c = d["completeness"]
        check("phases with Markdown under reports/ are covered; JSON-only perspectives and the report itself are set aside; a skipped phase is not asked for",
              c["phases_covered"] == ["create-domain-story", "design-aggregate", "evaluate-ddd", "evaluate-mmi", "investigate", "review-synthesizer"]
              and c["phases_without_markdown_output"] == ["report", "review-risk"] and c["phases_uncovered"] == [], c)
        check("the key metrics are found next to their labels",
              c["metrics_present"] == {"mmi_score": True, "ddd_score": True, "review_verdict": True,
                                       "aggregate_score": True, "mermaid_diagram": True}, c["metrics_present"])
        check("the story catalog is not demanded as a section; the modelled story and aggregate are checked for diagram and table",
              c["subsections_missing"] == [], c["subsections_missing"])
        s = d["score_accuracy"]
        check("perspective scores, aggregate, verdict and P0/P1 ids all found",
              all(x["status"] == "exact" for x in s["checked"]) and s["verdict"]["found"] and s["p0_p1_ids"] == 2 and s["p0_p1_missing"] == [], s)
        check("class diagram braces across lines and ER cardinalities are not unbalanced brackets",
              d["mermaid_syntax"]["blocks"] == 3 and d["mermaid_syntax"]["problems"] == [], d["mermaid_syntax"])
        check("a TBD carrying its OQ- id is not a placeholder", d["structure"]["bare_tbd"] == 0 and d["structure"]["placeholders"] == {})
        check("the weights are the skill's", R.WEIGHTS == {"completeness": 0.30, "score_accuracy": 0.35, "mermaid_syntax": 0.15, "language": 0.10, "structure": 0.10})

        print("a report with every kind of defect")
        bad = good_html()
        bad = bad.replace('<li><a href="#ddd-tactical-architecture-evaluation">ddd-tactical-architecture-evaluation</a></li>',
                          '<li><a href="#ddd-evaluation">ddd</a></li>')  # broken anchor
        bad = bad.replace(ARTICLE % ("ddd-tactical-architecture-evaluation", "DDD", "<p>Tactical design is weak.</p>"), "")  # phase uncovered
        bad = bad.replace("consistency scored 3.7", "consistency scored 3.4").replace("and SYN-002 are", "is")  # rounding, P1 missing
        bad = bad.replace(TABLE % "Invariant", "<p>no table</p>")  # aggregate without its invariant table
        bad = bad.replace(MERMAID % 'flowchart LR\n  A["Order"] --> B["Stock"]\n  B --> C',
                          MERMAID % 'flowchart LR\n  A["Order"] -> B[Stock\n  B --> C' + MERMAID % '<code>graph LR\n A --> B</code>')
        bad = bad.replace("<p>Scores per module.</p>", "<p>モジュールごとのスコアは次の表のとおりです。</p>")  # wrong language
        bad = bad.replace("<p>Nine critical findings.</p>", "<p>Nine critical findings; retention is TBD and the TODO list follows.</p>")
        bad = bad.replace(TABLE % "ID", "<table><tr><td>no</td><td>header</td></tr></table>")
        write(proj, "reports/00_summary/full-report.html", bad)
        r = R.Review(proj).run()
        d = r["dimensions"]
        check("one phase without a section and a missing table: completeness 3",
              d["completeness"]["score"] == 3 and d["completeness"]["phases_uncovered"] == ["evaluate-ddd"]
              and d["completeness"]["subsections_missing"] == [{"document": "aggregate-order", "missing": "table"}], d["completeness"])
        check("a rounded score and a missing P1 id: score accuracy 2",
              d["score_accuracy"]["score"] == 2 and d["score_accuracy"]["p0_p1_missing"] == ["SYN-002"]
              and [x["status"] for x in d["score_accuracy"]["checked"]] == ["rounding", "exact", "exact"], d["score_accuracy"])
        m = d["mermaid_syntax"]
        check("a <code> block is major, a single-dash arrow and an unclosed bracket are minor: mermaid 2",
              m["score"] == 2 and [p["severity"] for p in m["problems"]] == ["minor", "major"]
              and any("single-dash" in i for i in m["problems"][0]["issues"]) and any("unbalanced []" in i for i in m["problems"][0]["issues"]), m)
        check("one Japanese paragraph under en: language 4",
              d["language"]["score"] == 4 and d["language"]["paragraphs_wrong"] == 1 and d["language"]["headings_wrong"] == [], d["language"])
        st = d["structure"]
        check("a broken anchor is major (2); the unlinked document, the headless table, TODO and the bare TBD are counted",
              st["score"] == 2 and st["broken_anchors"] == ["ddd-evaluation"] and st["tables_without_header"] == [2]
              and st["placeholders"] == {"TODO": 1} and st["bare_tbd"] == 1, st)
        check("weighted 0.3*3+0.35*2+0.15*2+0.1*4+0.1*2 = 2.5, FAIL", r["weighted_score"] == 2.5 and r["verdict"] == "FAIL", (r["weighted_score"], r["verdict"]))
        ids = [f["id"] for f in r["findings"]]
        check("finding ids follow the RPT-<dimension><nn> scheme in dimension order",
              ids[:2] == ["RPT-101", "RPT-102"] and "RPT-201" in ids and "RPT-301" in ids and "RPT-401" in ids and "RPT-501" in ids
              and ids == sorted(ids), ids)
        check("every finding carries severity, location, title, description and recommendation",
              all(all(f.get(k) for k in ("severity", "location", "title", "description", "recommendation")) for f in r["findings"]))

        print("a wrong verdict is critical")
        write(proj, "reports/00_summary/full-report.html", good_html().replace("verdict is FAIL", "verdict is PASS"))
        r = R.Review(proj).run()
        check("the synthesis says FAIL, the page says PASS: critical, score 1, verdict FAIL",
              r["dimensions"]["score_accuracy"]["score"] == 1 and r["by_severity"]["critical"] == 1 and r["verdict"] == "FAIL", r["dimensions"]["score_accuracy"])

        print("Japanese output language")
        prog = dict(PROGRESS); prog["options"] = {"output_language": "ja"}
        write(proj, "work/pipeline-progress.json", json.dumps(prog))
        write(proj, "reports/00_summary/full-report.html", good_html())
        r = R.Review(proj).run()
        check("under ja every English paragraph is wrong; headings of ids are too short to judge",
              r["dimensions"]["language"]["paragraphs_wrong"] == r["dimensions"]["language"]["paragraphs"] > 0
              and r["dimensions"]["language"]["score"] == 1, r["dimensions"]["language"])

        print("command line")
        out = os.path.join(root, "rr.json")
        p = subprocess.run([sys.executable, os.path.join(HERE, "report_review.py"), proj, "out=" + out], capture_output=True, text=True)
        check("prints the JSON and writes out=", p.returncode == 0 and json.loads(p.stdout)["measured"] and json.load(open(out))["verdict"] == json.loads(p.stdout)["verdict"], p.stderr)
        empty = os.path.join(root, "empty"); os.makedirs(empty)
        check("a project without the report exits 1", subprocess.run([sys.executable, os.path.join(HERE, "report_review.py"), empty], capture_output=True).returncode == 1)
        check("a bad argument or a missing project exits 2",
              subprocess.run([sys.executable, os.path.join(HERE, "report_review.py"), proj, "--x"], capture_output=True).returncode == 2
              and subprocess.run([sys.executable, os.path.join(HERE, "report_review.py")], capture_output=True).returncode == 2)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
