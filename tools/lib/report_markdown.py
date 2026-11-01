"""The Markdown twin of the consolidated report (`full-report.md` beside `full-report.html`).

`tools/build-report.py` builds the HTML. The Markdown is built from the same run so the two
cannot drift: the same documents in the same order, the same section and article anchors, the
same executive summary. Two sources feed it:

- **Documents** — each one's own Markdown, transformed exactly as the HTML path transforms it
  before conversion (inter-report links to in-page anchors, image paths re-based onto the
  report's directory, headings moved down two levels under the article title), with every
  fenced block restored verbatim. A Mermaid fence therefore stays a ```mermaid fence, which
  GitHub, GitLab and most editors render.
- **The report's own chrome** — the executive summary, section and subgroup headings, the
  callout tables. Those exist only as the HTML the builder writes, from a fixed set of tags,
  so `HtmlToMarkdown` converts that subset: headings, paragraphs, pipe tables, lists, inline
  code / bold / emphasis / links, the verdict banner and the priority grid. An `<article>`
  whose id has a Markdown document is replaced by that document instead of being converted.

Anchors are `<a id="…"></a>` lines, so `#stem` links keep resolving in any renderer that
keeps raw HTML anchors (GitHub prefixes them and still follows the link).
"""

import html
import re
from html.parser import HTMLParser

INLINE_MARKS = {"strong": "**", "b": "**", "em": "*", "i": "*"}
BLOCKS = {"p", "div", "section", "header", "main", "blockquote", "article", "nav"}
SKIP_CONTENT = {"style", "script", "head", "title"}
COLLECT_CLASSES = ("verdict-banner", "stat-grid")
HARD_BREAK = "\x00BR\x00"     # survives whitespace folding; becomes "  \n" on output


def fence(lang, body):
    """A fence that cannot be closed early by the body it holds."""
    marker = "```"
    while marker in body:
        marker += "`"
    return "%s%s\n%s\n%s" % (marker, lang or "", body, marker)


def restore_fences(text, fences):
    for idx, (lang, body) in enumerate(fences):
        token = "ZQFENCEZQ%dZQENDZQ" % idx
        text = text.replace(token, fence(lang, body))
    return text


def anchor(ident):
    return '<a id="%s"></a>' % html.escape(ident, quote=True)


def article(stem, title, relpath, body_md):
    """One document as the report shows it: anchor, title, source path, body."""
    return "%s\n\n### %s\n\n`%s`\n\n%s" % (anchor(stem), title.strip(), relpath, body_md.strip())


def feature(stem, heading, relpath, text):
    return "%s\n\n### %s\n\n`%s`\n\n%s" % (anchor(stem), heading.strip(), relpath,
                                           fence("gherkin", text.rstrip("\n")))


class HtmlToMarkdown(HTMLParser):
    """Converts the builder's own HTML subset. Not a general converter, on purpose: every
    tag it meets was written by tools/build-report.py, or by the Markdown converter for a
    summary cell or an ELI5 excerpt."""

    def __init__(self, articles):
        super().__init__(convert_charrefs=True)
        self.articles = articles
        self.blocks, self.buf = [], []
        self.anchors = []
        self.skip_article = 0
        self.skip_content = 0
        self.heading = None
        self.links = []
        self.codes = []
        self.lists = []
        self.li_prefix = None
        self.table = None
        self.cell = None
        self.pre = None
        self.collect = None

    # ----------------------------------------------------------------- output
    def emit(self, block):
        if self.anchors:
            self.blocks.append("\n".join(anchor(a) for a in self.anchors))
            self.anchors = []
        self.blocks.append(block)

    def text(self):
        out = re.sub(r"[ \t]+", " ", "".join(self.buf)).strip()
        self.buf = []
        return re.sub(r" ?%s ?" % re.escape(HARD_BREAK), "  \n", out).strip()

    def flush(self):
        text = self.text()
        if not text:
            return
        if self.li_prefix is not None:
            text = self.li_prefix + text
            self.li_prefix = None
        self.emit(text)

    # ----------------------------------------------------------------- parser
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if self.skip_article:
            if tag == "article":
                self.skip_article += 1
            return
        if tag in SKIP_CONTENT:
            self.skip_content += 1
            return
        if self.skip_content:
            return
        ident = attrs.get("id")
        if tag == "article" and ident in self.articles:
            self.flush()
            if ident in self.anchors:
                self.anchors.remove(ident)
            self.emit(self.articles[ident])
            self.skip_article = 1
            return
        if ident:
            self.anchors.append(ident)
        if self.pre is not None:
            if tag == "code":
                lang = next((c[len("language-"):] for c in classes if c.startswith("language-")), "")
                self.pre["lang"] = self.pre["lang"] or lang
            return
        if self.collect is not None and tag == "div":
            self.collect["depth"] += 1
            return
        if tag == "div" and any(c in classes for c in COLLECT_CLASSES):
            self.flush()
            self.collect = {"kind": next(c for c in classes if c in COLLECT_CLASSES),
                            "parts": [], "depth": 0}
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading = int(tag[1])
        elif tag in BLOCKS and self.cell is None:
            self.flush()
        elif tag in ("ul", "ol"):
            self.flush()
            self.lists.append([tag, 0])
        elif tag == "li":
            self.flush()
            kind = self.lists[-1] if self.lists else ["ul", 0]
            kind[1] += 1
            indent = "  " * (len(self.lists) - 1)
            self.li_prefix = indent + ("%d. " % kind[1] if kind[0] == "ol" else "- ")
        elif tag == "table":
            self.flush()
            self.table = {"rows": [], "row": None}
        elif tag == "tr" and self.table is not None:
            self.table["row"] = []
        elif tag in ("td", "th") and self.table is not None:
            self.cell, self.buf = self.buf, []
        elif tag == "pre":
            self.flush()
            self.pre = {"lang": "mermaid" if "mermaid" in classes else "", "text": []}
        elif tag == "br":
            self.buf.append("<br>" if self.cell is not None else HARD_BREAK)
        elif tag == "code":
            self.codes.append(len(self.buf))
            self.buf.append("`")
        elif tag in INLINE_MARKS:
            self.buf.append(INLINE_MARKS[tag])
        elif tag == "a":
            self.links.append((len(self.buf), attrs.get("href")))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.skip_article:
            if tag == "article":
                self.skip_article -= 1
            return
        if tag in SKIP_CONTENT:
            self.skip_content = max(0, self.skip_content - 1)
            return
        if self.skip_content:
            return
        if self.pre is not None:
            if tag == "pre":
                body = "".join(self.pre["text"]).rstrip("\n")
                self.emit(fence(self.pre["lang"], body))
                self.pre = None
            return
        if self.collect is not None and tag == "div":
            if self.collect["depth"] > 1:
                self.buf.append(" ")
                self.collect["depth"] -= 1
            elif self.collect["depth"] == 1:
                part = self.text()
                if part:
                    self.collect["parts"].append(part)
                self.collect["depth"] -= 1
            else:
                parts = self.collect["parts"]
                line = " · ".join(parts)
                if line:
                    self.emit("> " + line if self.collect["kind"] == "verdict-banner" else line)
                self.collect = None
            return
        if re.fullmatch(r"h[1-6]", tag) and self.heading:
            text = self.text()
            if text:
                self.emit("#" * self.heading + " " + text)
            self.heading = None
        elif tag in ("td", "th") and self.table is not None and self.cell is not None:
            value = self.text().replace("|", "\\|")
            self.buf, self.cell = self.cell, None
            if self.table["row"] is not None:
                self.table["row"].append(value)
        elif tag == "tr" and self.table is not None:
            if self.table["row"] is not None:
                self.table["rows"].append(self.table["row"])
            self.table["row"] = None
        elif tag == "table" and self.table is not None:
            rows = [r for r in self.table["rows"] if r]
            self.table = None
            if rows:
                width = max(len(r) for r in rows)
                rows = [r + [""] * (width - len(r)) for r in rows]
                lines = ["| %s |" % " | ".join(rows[0]), "|%s" % (" --- |" * width)]
                lines += ["| %s |" % " | ".join(r) for r in rows[1:]]
                self.emit("\n".join(lines))
        elif tag == "li":
            self.flush()
        elif tag in ("ul", "ol"):
            self.flush()
            if self.lists:
                self.lists.pop()
        elif tag in BLOCKS and self.cell is None:
            self.flush()
        elif tag == "code":
            start = self.codes.pop() if self.codes else None
            if start is not None and not "".join(self.buf[start + 1:]).strip():
                del self.buf[start:]          # an empty <code></code> is no code span
            else:
                self.buf.append("`")
        elif tag in INLINE_MARKS:
            self.buf.append(INLINE_MARKS[tag])
        elif tag == "a" and self.links:
            start, href = self.links.pop()
            label = "".join(self.buf[start:]).strip()
            del self.buf[start:]
            self.buf.append("[%s](%s)" % (label, href) if href else label)

    def handle_data(self, data):
        if self.skip_article or self.skip_content:
            return
        if self.pre is not None:
            self.pre["text"].append(data)
            return
        self.buf.append(re.sub(r"\s+", " ", data))

    def close(self):
        super().close()
        self.flush()
        if self.anchors:
            self.blocks.append("\n".join(anchor(a) for a in self.anchors))
            self.anchors = []
        return self.blocks


def convert(fragment, articles=None):
    """The Markdown of one HTML fragment the builder wrote."""
    parser = HtmlToMarkdown(articles or {})
    parser.feed(fragment)
    return "\n\n".join(parser.close())


def document(frontmatter, meta_html, toc_heading, toc, summary_html, sections_html, articles):
    """The whole `full-report.md`. The frontmatter title is the report's H1 (output
    conventions: the body starts at `##`)."""
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.append("%s: %s" % (key, value if isinstance(value, int) else '"%s"' % str(value)
                                 .replace("\\", "\\\\").replace('"', '\\"')))
    lines.append("---")
    parts = ["\n".join(lines), convert("<p>%s</p>" % meta_html)]
    toc_lines = ["## %s" % toc_heading]
    for sid, heading, entries in toc:
        toc_lines.append("- [%s](#%s)" % (heading, sid))
        toc_lines += ["  - [%s](#%s)" % (title, eid) for eid, title in entries]
    parts.append("\n".join(toc_lines))
    parts.append(convert(summary_html, articles))
    parts += [convert(section, articles) for section in sections_html]
    text = "\n\n".join(p for p in parts if p.strip())
    return re.sub(r"\n{3,}", "\n\n", text).rstrip() + "\n"
