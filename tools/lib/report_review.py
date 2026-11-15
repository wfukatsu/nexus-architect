#!/usr/bin/env python3
"""Measure the consolidated report for /architect:review-report.

    python3 tools/lib/report_review.py <project_dir> [out=<file>]

Reads reports/00_summary/full-report.html (what tools/build-report.py wrote), work/pipeline-progress.json,
reports/review/review-synthesis.json and the evaluation reports, and prints one JSON document: the
five dimensions of skills/review-report/SKILL.md, each with what was measured, the findings the
measurements imply (RPT-1xx … RPT-5xx, severity, location, recommendation), and the score the skill's
own 1–5 scale assigns to those measurements; then the weighted score and the verdict the skill's
thresholds give. The reviewing agent reads this, judges what a script cannot (whether a covered
phase is covered *well*), and writes reports/review/quality-review.md.

Why a script and not five sub-agents: every dimension is a mechanical pass over a file that is
several megabytes — the whole point of the consolidated report — which no sub-agent can read, so a
pipeline run delegated nothing twice in a row (0.66.0 and 0.68.0 references) and recorded that as a
shortfall. The pass is deterministic here, costs nothing, and the same measurements come back on a
rerun. Exit 0 when the report was measured (whatever the verdict), 1 when it does not exist.
"""
import glob
import html as htmllib
import json
import os
import re
import sys

WEIGHTS = {"completeness": 0.30, "score_accuracy": 0.35, "mermaid_syntax": 0.15,
           "language": 0.10, "structure": 0.10}
PREFIX = {"completeness": 1, "score_accuracy": 2, "mermaid_syntax": 3, "language": 4, "structure": 5}
# Phases whose outputs are not documents the report renders.
NOT_RENDERED = {"init-output", "report", "review-report"}
DIAGRAM_TYPES = ("graph", "flowchart", "sequenceDiagram", "classDiagram", "stateDiagram", "stateDiagram-v2",
                 "erDiagram", "journey", "gantt", "pie", "quadrantChart", "requirementDiagram", "gitGraph",
                 "mindmap", "timeline", "zenuml", "sankey", "xychart", "block", "C4Context", "C4Container",
                 "C4Component", "C4Dynamic", "C4Deployment", "packet", "kanban", "architecture")
PLACEHOLDERS = ("[TBD]", "TODO", "PLACEHOLDER", "〇〇", "＊＊＊")
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿]")
LATIN = re.compile(r"[A-Za-z]")


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def visible_text(fragment):
    """The text a reader sees: no scripts, styles, tags or entities."""
    fragment = re.sub(r"<script.*?</script>|<style.*?</style>", " ", fragment, flags=re.S)
    return htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment))


def stem(path):
    return os.path.splitext(os.path.basename(path.rstrip("/")))[0]


class Finding:
    def __init__(self, dim, severity, location, title, description, recommendation):
        self.dim, self.severity, self.location = dim, severity, location
        self.title, self.description, self.recommendation = title, description, recommendation

    def as_dict(self, n):
        return {"id": "RPT-%d%02d" % (PREFIX[self.dim], n), "dimension": self.dim, "severity": self.severity,
                "location": self.location, "title": self.title, "description": self.description,
                "recommendation": self.recommendation}


class Review:
    def __init__(self, project):
        self.project = project
        self.report = os.path.join(project, "reports", "00_summary", "full-report.html")
        self.html = read_text(self.report)
        self.text = visible_text(self.html)
        progress = read_json(os.path.join(project, "work", "pipeline-progress.json"), {}) or {}
        self.phases = progress.get("phases") or {}
        self.options = progress.get("options") or {}
        self.synthesis = read_json(os.path.join(project, "reports", "review", "review-synthesis.json"), {}) or {}
        self.articles = re.findall(r'<article class="doc" id="([^"]+)"', self.html)
        self.findings = {d: [] for d in WEIGHTS}

    def add(self, dim, severity, location, title, description, recommendation):
        self.findings[dim].append(Finding(dim, severity, location, title, description, recommendation))

    def article(self, doc_id):
        m = re.search(r'<article class="doc" id="%s">(.*?)</article>' % re.escape(doc_id), self.html, re.S)
        return m.group(1) if m else ""

    def near(self, label, value, window=120):
        """Whether `value` (a number) is printed within `window` characters of `label`."""
        found = []
        for m in re.finditer(re.escape(label), self.text, re.I):
            seg = self.text[m.start():m.end() + window]
            found.extend(float(x) for x in re.findall(r"\d+(?:\.\d+)?", seg))
        return found

    # ---------------------------------------------------------------- 1. completeness
    def completeness(self):
        completed = sorted(k for k, v in self.phases.items() if v.get("status") == "completed")
        uncovered, not_applicable, covered = [], [], []
        for phase in completed:
            if phase in NOT_RENDERED:
                not_applicable.append(phase)
                continue
            docs = [stem(o) for o in self.phases[phase].get("outputs") or [] if str(o).endswith(".md")]
            if not docs:
                not_applicable.append(phase)
                continue
            (covered if any(d in self.articles for d in docs) else uncovered).append(phase)
        for phase in uncovered:
            self.add("completeness", "major", "global", "Phase %s has no section" % phase,
                     "The phase is completed in work/pipeline-progress.json and none of its Markdown outputs "
                     "(%s) is a document of the report." % ", ".join(
                         stem(o) for o in self.phases[phase].get("outputs") or [] if str(o).endswith(".md")),
                     "Rebuild the report (tools/build-report.py) with the phase's reports present, or check "
                     "the layout the builder was given.")
        metrics = {}
        mmi = self.source_number(os.path.join("reports", "02_evaluation", "mmi-overview.md"),
                                 r"System Average MMI\s*\|\s*(\d+(?:\.\d+)?)")
        ddd = self.source_number(os.path.join("reports", "02_evaluation", "ddd-tactical-architecture-evaluation.md"),
                                 r"Overall DDD Score:\s*(\d+(?:\.\d+)?)")
        if "evaluate-mmi" in completed:
            metrics["mmi_score"] = mmi is not None and mmi in self.near("MMI", mmi)
        if "evaluate-ddd" in completed:
            metrics["ddd_score"] = ddd is not None and ddd in self.near("DDD", ddd)
        if "review-synthesizer" in completed:
            verdict = str(self.synthesis.get("verdict") or "")
            metrics["review_verdict"] = bool(verdict) and verdict in self.text
            agg = self.synthesis.get("aggregate_score")
            metrics["aggregate_score"] = agg is not None and ("%.2f" % float(agg) in self.text
                                                              or "%.1f" % float(agg) in self.text)
        metrics["mermaid_diagram"] = '<pre class="mermaid"' in self.html
        for name, present in metrics.items():
            if not present:
                self.add("completeness", "major", "summary", "Key metric missing: %s" % name,
                         "The executive summary and the sections carry no %s a reader can find." % name.replace("_", " "),
                         "Have the source report state it and rebuild.")
        subsections = self.subsections()
        minor = sum(1 for v in metrics.values() if not v) + len(subsections)
        if len(uncovered) >= 3:
            score = 1
        elif len(uncovered) == 2:
            score = 2
        elif len(uncovered) == 1 or minor > 2:
            score = 3
        elif minor:
            score = 4
        else:
            score = 5
        return {"weight": WEIGHTS["completeness"], "score": score, "phases_completed": completed,
                "phases_covered": covered, "phases_uncovered": uncovered, "phases_without_markdown_output": not_applicable,
                "metrics_present": metrics, "subsections_missing": subsections}

    def source_number(self, relpath, pattern):
        m = re.search(pattern, read_text(os.path.join(self.project, relpath)))
        return float(m.group(1)) if m else None

    def subsections(self):
        """Stories, aggregates and state machines: each modelled file is a document with its diagram
        and, for the tactical models, the table that justifies it."""
        missing = []
        checks = (
            ("reports/04_stories/domain-story-*.md", "sequence diagram", None),
            ("reports/03_design/aggregates/aggregate-*.md", "class diagram", r"invariant|不変条件"),
            ("reports/03_design/state-machines/state-machine-*.md", "state diagram", r"event|イベント"),
        )
        for pattern, diagram, table_word in checks:
            for path in sorted(glob.glob(os.path.join(self.project, pattern))):
                doc = stem(path)
                if doc.endswith(("-catalog", "-inventory", "-index")):
                    continue
                body = self.article(doc)
                if not body:
                    missing.append({"document": doc, "missing": "section"})
                    self.add("completeness", "major", doc, "%s has no section" % doc,
                             "The file exists under reports/ and the report has no document for it.",
                             "Rebuild the report with the file present.")
                    continue
                if '<pre class="mermaid"' not in body:
                    missing.append({"document": doc, "missing": diagram})
                    self.add("completeness", "minor", doc, "%s renders without its %s" % (doc, diagram),
                             "The document is present but carries no Mermaid block.",
                             "Restore the diagram in the source file and rebuild.")
                if table_word and not re.search(r"<table.*?</table>", body, re.S | re.I):
                    missing.append({"document": doc, "missing": "table"})
                    self.add("completeness", "minor", doc, "%s renders without its table" % doc,
                             "The diagram is there; the table that states what it must hold (%s) is not."
                             % table_word.split("|")[0],
                             "Restore the table in the source file and rebuild.")
                elif table_word and not re.search(table_word, visible_text(body), re.I):
                    missing.append({"document": doc, "missing": "table (%s)" % table_word.split("|")[0]})
                    self.add("completeness", "minor", doc, "%s: no table names its %s"
                             % (doc, table_word.split("|")[0]),
                             "The document has tables, none of them the one the model is justified by.",
                             "Restore the table in the source file and rebuild.")
        return missing

    # ---------------------------------------------------------------- 2. score accuracy
    def score_accuracy(self):
        checked, discrepancies, rounding = [], [], []
        scores = self.synthesis.get("perspective_scores") or {}
        for name, expected in sorted(scores.items()):
            try:
                expected = float(expected)
            except (TypeError, ValueError):
                continue
            seen = self.near(name, expected)
            status = "exact" if expected in seen else (
                "rounding" if any(abs(v - expected) <= 0.5 for v in seen) else "missing")
            checked.append({"name": name, "expected": expected, "status": status})
            (rounding if status == "rounding" else discrepancies if status == "missing" else []).append(name)
        agg = self.synthesis.get("aggregate_score")
        if agg is not None:
            agg = float(agg)
            status = "exact" if ("%.2f" % agg) in self.text or ("%.1f" % agg) in self.text else "missing"
            checked.append({"name": "aggregate_score", "expected": agg, "status": status})
            if status == "missing":
                discrepancies.append("aggregate_score")
        verdict = str(self.synthesis.get("verdict") or "")
        verdict_match = bool(verdict) and verdict in self.text
        p1 = [f.get("id") for f in self.synthesis.get("findings") or [] if f.get("priority") in ("P0", "P1")]
        p1_missing = [i for i in p1 if i and i not in self.text]
        for name in discrepancies:
            self.add("score_accuracy", "major", "summary", "Score not found: %s" % name,
                     "review-synthesis.json says %s; no number within 0.5 of it stands near that label in the "
                     "report." % next(c["expected"] for c in checked if c["name"] == name),
                     "Rebuild the report from the current synthesis, or fix the synthesis table in the summary.")
        for name in rounding:
            self.add("score_accuracy", "minor", "summary", "Score rounded: %s" % name,
                     "The report prints a value within 0.5 of the synthesis value, not the value itself.",
                     "Print the synthesis value as recorded.")
        if verdict and not verdict_match:
            self.add("score_accuracy", "critical", "summary", "Verdict differs from the synthesis",
                     "review-synthesis.json records %s; the report does not state it." % verdict,
                     "Rebuild the report; the verdict is read from the synthesis.")
        if p1_missing:
            self.add("score_accuracy", "major", "review", "%d P0/P1 finding IDs absent" % len(p1_missing),
                     "Not in the report: %s." % ", ".join(p1_missing[:12]) + (" …" if len(p1_missing) > 12 else ""),
                     "Rebuild the report with the current review-synthesis.md.")
        if (verdict and not verdict_match) or len(discrepancies) + len(p1_missing) >= 2:
            score = 1 if (verdict and not verdict_match) or len(discrepancies) + len(p1_missing) >= 3 else 2
        elif discrepancies or p1_missing:
            score = 2
        elif len(rounding) > 2:
            score = 3
        elif rounding:
            score = 4
        else:
            score = 5
        if not scores and agg is None and not verdict:
            score = 5  # nothing to check: no synthesis in this run
        return {"weight": WEIGHTS["score_accuracy"], "score": score, "checked": checked,
                "verdict": {"expected": verdict or None, "found": verdict_match},
                "p0_p1_ids": len(p1), "p0_p1_missing": p1_missing}

    # ---------------------------------------------------------------- 3. mermaid syntax
    def mermaid_syntax(self):
        blocks = re.findall(r'<pre class="mermaid"[^>]*>(.*?)</pre>', self.html, re.S)
        problems = []
        for n, raw in enumerate(blocks, 1):
            issues = []
            if "<code" in raw:
                issues.append(("major", "a <code> element inside the block: Mermaid reads innerHTML and "
                                        "the tag becomes diagram text"))
            src = htmllib.unescape(re.sub(r"<[^>]+>", "", raw))
            lines = [l for l in src.splitlines() if l.strip()]
            first = lines[0].strip() if lines else ""
            if len(lines) < 2:
                issues.append(("major", "empty or near-empty block"))
            elif not first.startswith("%%") and not any(
                    first.lower().startswith(t.lower()) for t in DIAGRAM_TYPES):
                issues.append(("major", "unknown diagram type %r" % first[:40]))
            kind = first.split()[0] if first else ""
            for line in lines[1:]:
                s = line.strip()
                if s.startswith("%%"):
                    continue
                if kind in ("graph", "flowchart") and re.search(r"(?<![-<.=])->(?![>-])", s):
                    issues.append(("minor", "single-dash arrow in %r" % s[:60]))
                if kind in ("graph", "flowchart"):
                    for node in re.findall(r"(?:^|-->|---|-\.->|==>|\s)([^\s\[\(\{\"'|>-]+)(?=[\[\(\{])", s):
                        if not node.isascii():
                            issues.append(("minor", "non-ASCII node id %r" % node[:30]))
                            break
                # Brackets balance per line only in flowcharts: class, ER and state diagrams open a
                # brace on one line and close it lines later, and ER cardinalities are `||--o{`.
                quoted = re.sub(r'"[^"]*"', "", s)
                if kind in ("graph", "flowchart"):
                    for open_, close in (("[", "]"), ("(", ")"), ("{", "}")):
                        if quoted.count(open_) != quoted.count(close):
                            issues.append(("minor", "unbalanced %s%s in %r" % (open_, close, s[:60])))
                            break
                if s.count('"') % 2:
                    issues.append(("minor", "unbalanced quote in %r" % s[:60]))
            if issues:
                problems.append({"block": n, "first_lines": lines[:3], "issues": [i[1] for i in issues],
                                 "severity": "major" if any(i[0] == "major" for i in issues) else "minor"})
                self.add("mermaid_syntax", problems[-1]["severity"], "mermaid block %d (%s)" % (n, first[:40]),
                         "Diagram %d: %s" % (n, issues[0][1][:60]), "; ".join(i[1] for i in issues),
                         "Fix the block in the source report and rebuild; hooks/validate-mermaid.sh checks it.")
        majors = sum(1 for p in problems if p["severity"] == "major")
        minors = len(problems) - majors
        score = 1 if majors >= 2 else 2 if majors == 1 else 3 if minors >= 2 else 4 if minors == 1 else 5
        return {"weight": WEIGHTS["mermaid_syntax"], "score": score, "blocks": len(blocks), "problems": problems}

    # ---------------------------------------------------------------- 4. language
    def language(self):
        lang = str(self.options.get("output_language") or "en")
        body = re.sub(r'<pre class="mermaid"[^>]*>.*?</pre>|<pre>.*?</pre>|<code>.*?</code>', " ", self.html, flags=re.S)
        headings = [(t, visible_text(h)) for t, h in re.findall(r"<(h[1-4])[^>]*>(.*?)</\1>", body, re.S)]
        paragraphs = [visible_text(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S)]

        def wrong(text):
            cjk, latin = len(CJK.findall(text)), len(LATIN.findall(text))
            if cjk + latin < 12:
                return False
            share = cjk / float(cjk + latin)
            return share > 0.3 if lang == "en" else share < 0.1

        wrong_headings = [h.strip()[:60] for _, h in headings if wrong(h)]
        wrong_paragraphs = [p.strip()[:80] for p in paragraphs if wrong(p)]
        for h in wrong_headings:
            self.add("language", "minor", h, "Heading not in %s" % lang, "Heading: %r." % h,
                     "Translate it in the source report and rebuild.")
        if wrong_paragraphs:
            self.add("language", "minor" if len(wrong_paragraphs) <= 2 else "major", "body",
                     "%d paragraph(s) not in %s" % (len(wrong_paragraphs), lang),
                     "First: %r." % wrong_paragraphs[0],
                     "Translate them in the source reports and rebuild.")
        total = max(len(paragraphs), 1)
        if len(wrong_paragraphs) > total / 2.0:
            score = 1
        elif len(wrong_headings) >= 2 or len(wrong_paragraphs) > 10:
            score = 2
        elif wrong_headings or len(wrong_paragraphs) >= 3:
            score = 3
        elif wrong_paragraphs:
            score = 4
        else:
            score = 5
        return {"weight": WEIGHTS["language"], "score": score, "output_language": lang,
                "headings": len(headings), "headings_wrong": wrong_headings,
                "paragraphs": len(paragraphs), "paragraphs_wrong": len(wrong_paragraphs)}

    # ---------------------------------------------------------------- 5. structure
    def structure(self):
        nav = re.search(r"<nav id=\"sidebar\">(.*?)</nav>", self.html, re.S)
        hrefs = re.findall(r'href="#([^"]+)"', nav.group(1)) if nav else []
        ids = set(re.findall(r'\bid="([^"]+)"', self.html))
        broken = [h for h in hrefs if h not in ids]
        sections = re.findall(r'<section[^>]*\bid="([^"]+)"', self.html)
        unlinked = [s for s in sections + self.articles if s not in hrefs]
        tables = re.findall(r"<table[^>]*>(.*?)</table>", self.html, re.S)
        headless = [i + 1 for i, t in enumerate(tables)
                    if "<thead" not in t and not re.match(r"\s*(?:<caption.*?</caption>\s*)?(?:<tbody>\s*)?<tr>\s*<th", t, re.S)]
        placeholders = {p: self.text.count(p) for p in PLACEHOLDERS if p in self.text}
        bare_tbd = re.findall(r".{0,40}\bTBD\b(?!\s*\(?OQ-).{0,40}", self.text)
        title = re.search(r"<title>(.*?)</title>", self.html, re.S)
        title = htmllib.unescape(title.group(1)).strip() if title else ""
        h1 = len(re.findall(r"<h1[\s>]", self.html))
        if not nav:
            self.add("structure", "major", "sidebar", "No sidebar navigation",
                     "The report has no <nav id=\"sidebar\">.", "Rebuild with tools/build-report.py.")
        for h in broken:
            self.add("structure", "major", "sidebar", "Broken navigation link #%s" % h,
                     "The sidebar links to an id the document does not have.", "Rebuild the report.")
        if unlinked:
            self.add("structure", "minor", "sidebar", "%d document(s) not in the sidebar" % len(unlinked),
                     ", ".join(unlinked[:8]) + (" …" if len(unlinked) > 8 else ""), "Rebuild the report.")
        if headless:
            self.add("structure", "minor", "table %s" % ", ".join(str(i) for i in headless[:6]),
                     "%d table(s) without a header row" % len(headless),
                     "A table whose first row is not <th> cells has no header.",
                     "Give the source table a header row.")
        for p, n in placeholders.items():
            self.add("structure", "minor", "body", "Placeholder text %r (%d)" % (p, n),
                     "Placeholder text is visible in the final report.",
                     "Replace it in the source report, or record the unknown as an Open Question.")
        if bare_tbd:
            self.add("structure", "minor", "body", "%d bare TBD without an OQ- id" % len(bare_tbd),
                     "First: %r. A TBD that names its question (TBD (OQ-012)) is intentional; one without "
                     "an id is a placeholder." % bare_tbd[0].strip(),
                     "Attach the OQ- id in the source report (rules/open-questions.md).")
        if not title:
            self.add("structure", "major", "head", "Empty <title>", "The page has no title.", "Rebuild the report.")
        if h1 != 1:
            self.add("structure", "minor", "hero", "%d <h1> elements" % h1,
                     "The page should have exactly one h1, in the hero.", "Rebuild the report.")
        majors = len(broken) + (0 if nav else 1) + (0 if title else 1)
        minors = len([1 for x in (unlinked, headless, bare_tbd) if x]) + len(placeholders) + (h1 != 1)
        score = 1 if majors >= 2 else 2 if majors == 1 else 3 if minors >= 2 else 4 if minors == 1 else 5
        return {"weight": WEIGHTS["structure"], "score": score, "nav_links": len(hrefs), "broken_anchors": broken,
                "unlinked_documents": unlinked, "tables": len(tables), "tables_without_header": headless,
                "placeholders": placeholders, "bare_tbd": len(bare_tbd), "bare_tbd_samples": [b.strip() for b in bare_tbd[:5]],
                "title": title, "h1_count": h1}

    # ---------------------------------------------------------------- the review
    def run(self):
        if not self.html:
            return {"measured": False, "reason": "no reports/00_summary/full-report.html", "project": self.project}
        dims = {"completeness": self.completeness(), "score_accuracy": self.score_accuracy(),
                "mermaid_syntax": self.mermaid_syntax(), "language": self.language(), "structure": self.structure()}
        findings = []
        for dim, items in self.findings.items():
            dims[dim]["findings"] = [f.as_dict(n) for n, f in enumerate(items, 1)]
            findings.extend(dims[dim]["findings"])
        weighted = round(sum(WEIGHTS[d] * dims[d]["score"] for d in WEIGHTS), 2)
        by_severity = {s: sum(1 for f in findings if f["severity"] == s) for s in ("critical", "major", "minor", "info")}
        if weighted >= 4.0 and not by_severity["critical"]:
            verdict = "PASS"
        elif weighted >= 3.0 and not by_severity["critical"]:
            verdict = "PASS_WITH_WARNINGS"
        else:
            verdict = "FAIL"
        return {"measured": True, "project": self.project, "report": os.path.relpath(self.report, self.project),
                "report_bytes": len(self.html.encode("utf-8")), "dimensions": dims,
                "weighted_score": weighted, "verdict": verdict, "findings": findings, "by_severity": by_severity}


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    project = argv[1]
    out = next((a.split("=", 1)[1] for a in argv[2:] if a.startswith("out=")), None)
    if any(not a.startswith("out=") for a in argv[2:]) or not os.path.isdir(project):
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    result = Review(project).run()
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0 if result["measured"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
