"""Collect the public upstream of the k8s-tf OKF bundle and report what moved.

The bundle at knowledge/okf-k8s-tf/ was written from two kinds of source:

* **Official documentation** — every document's frontmatter `sources` lists the public pages its
  design guidance (設計指針) rests on: kubernetes.io, developer.hashicorp.com, docs.gitlab.com …
* **Two private repositories** — the observed-implementation tier (対象実装) is a snapshot of
  them. They are not public, and this repository is, so they are never fetched here.

This module watches the first kind from the internet, plus the release feeds of every technology
the bundle names a version for, and reports the difference against the last recorded state:

    knowledge/okf-k8s-tf-upstream/
      sources.yaml   hand-edited: the release feeds to watch and the version the bundle states
      state.json     committed: per page a content hash, per feed the latest release
      REPORT.md      committed: what changed on the last run, and which bundle documents it touches
      pages/         git-ignored: the extracted text of every page, the locally held copy

Page text is held locally but never committed: it is third-party documentation under a mix of
licences, and this repository is public. The committed state is enough to say *what* changed; the
text is what the reviser — `/architect:revise-knowledge`, a Claude skill run on demand — reads to
say *how*.

Everything here is deterministic and needs no model: collecting, diffing, the list of documents
awaiting re-verification, and the one bundle edit that takes no judgement (a cited page that
redirected gets its `resource` rewritten to the final URL, `apply_redirects`). That is what the
weekly workflow runs. Revising a document's prose is judgement, and belongs to the skill.

Network access goes through the `Fetcher` protocol so the suite can run offline.
"""

import datetime
import hashlib
import html
import http.client
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

import yaml

SCHEMA_VERSION = 1
USER_AGENT = "nexus-architect-okf-refresh (+https://github.com/wfukatsu/nexus-architect)"

# Sources that are never fetched: the private repositories the observed tier was read from.
PRIVATE_PREFIXES = ("https://gitlab.com/scalar-labs/",)

# Anything inside these is chrome, not content, and changes without the documentation changing.
SKIP_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "aside", "svg", "button",
             "form", "template", "iframe", "select"}
BLOCK_TAGS = {"p", "div", "section", "li", "tr", "table", "ul", "ol", "dl", "dt", "dd", "pre",
              "blockquote", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "article", "main",
              "td", "th", "figure", "figcaption", "details", "summary"}
HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


# ------------------------------------------------------------------------------ extraction

class _Probe(HTMLParser):
    """First pass: which content root does the page have, and what is its title."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.seen = set()
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        self.seen.add(tag)
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


class _Extract(HTMLParser):
    """Second pass: the text under the content root, headings kept as Markdown `#` lines."""

    def __init__(self, root):
        super().__init__(convert_charrefs=True)
        self.root = root
        self.depth = 0          # nesting of `root` tags we are inside
        self.done = False       # only the first content root counts
        self.skip = 0           # nesting of SKIP_TAGS
        self.pre = 0
        self.out = []
        self.heading = None

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        if tag == self.root:
            self.depth += 1
        if not self.depth:
            return
        if tag in SKIP_TAGS:
            self.skip += 1
            return
        if self.skip:
            return
        if tag == "pre":
            self.pre += 1
        if tag in BLOCK_TAGS:
            self.out.append("\n")
        if tag in HEADINGS:
            self.heading = tag
            self.out.append("#" * HEADINGS[tag] + " ")
        elif tag == "li":
            self.out.append("- ")

    def handle_endtag(self, tag):
        if self.done or not self.depth:
            return
        if tag in SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag == "pre":
            self.pre = max(0, self.pre - 1)
        if tag in BLOCK_TAGS:
            self.out.append("\n")
        if tag == self.heading:
            self.heading = None
        if tag == self.root:
            self.depth -= 1
            if not self.depth:
                self.done = True

    def handle_data(self, data):
        if self.done or not self.depth or self.skip:
            return
        self.out.append(data if self.pre else re.sub(r"\s+", " ", data))


def extract(page_html):
    """Return (title, text): the page's main content as normalised, line-oriented text.

    The root is <main> when the page has one, else <article>, else <body>. Whitespace is collapsed
    outside <pre>, blank lines are squeezed, and trailing space is dropped — so the hash moves when
    the documentation moves, not when the site reflows its markup.
    """
    probe = _Probe()
    probe.feed(page_html)
    root = next((t for t in ("main", "article", "body") if t in probe.seen), None)
    if root is None:
        return probe.title.strip(), ""
    ex = _Extract(root)
    ex.feed(page_html)
    lines = [ln.rstrip() for ln in "".join(ex.out).splitlines()]
    text, blank = [], False
    for ln in lines:
        # Outside <pre> whitespace is collapsed, so at most one leading space is markup noise;
        # deeper indentation came from a <pre> block and is kept.
        ln = ln[1:] if ln.startswith(" ") and not ln.startswith("  ") else ln
        if not ln.strip():
            blank = bool(text)
            continue
        if blank:
            text.append("")
            blank = False
        text.append(ln)
    return html.unescape(re.sub(r"\s+", " ", probe.title).strip()), "\n".join(text) + "\n"


def digest(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def outline(text):
    """The heading lines of an extracted page — small enough to commit, enough to see a restructure."""
    return [ln for ln in text.splitlines() if re.match(r"#{1,3} \S", ln)]


# ------------------------------------------------------------------------------ bundle sources

def _frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        body = fh.read()
    if not body.startswith("---"):
        return {}
    parts = body.split("---", 2)
    return (yaml.safe_load(parts[1]) or {}) if len(parts) > 2 else {}


def bundle_documents(bundle):
    """Every bundle document with frontmatter, as {relative path: frontmatter}."""
    docs = {}
    for dirpath, _, files in os.walk(bundle):
        for f in sorted(files):
            if f.endswith(".md"):
                full = os.path.join(dirpath, f)
                fm = _frontmatter(full)
                if fm:
                    docs[os.path.relpath(full, bundle).replace(os.sep, "/")] = fm
    return dict(sorted(docs.items()))


def is_private(url):
    return url.startswith(PRIVATE_PREFIXES)


def page_sources(bundle):
    """The public pages the bundle cites, as {url: {"ids": [...], "cited_by": [...], "title": ...}}.

    Collected from each document's `sources` list and its top-level `resource`. Private sources
    are left out here, and listed by `private_sources` so the report can say they were skipped
    on purpose rather than forgotten.
    """
    pages = {}
    for rel, fm in bundle_documents(bundle).items():
        entries = list(fm.get("sources") or [])
        if fm.get("resource"):
            entries.append({"id": "resource", "resource": fm["resource"], "title": fm.get("title", "")})
        for s in entries:
            url = (s or {}).get("resource")
            if not url or is_private(url):
                continue
            page = pages.setdefault(url, {"ids": [], "cited_by": [], "title": s.get("title", "")})
            if s.get("id") and s["id"] not in page["ids"]:
                page["ids"].append(s["id"])
            if rel not in page["cited_by"]:
                page["cited_by"].append(rel)
    return dict(sorted(pages.items()))


def private_sources(bundle):
    seen = {}
    for rel, fm in bundle_documents(bundle).items():
        for s in fm.get("sources") or []:
            url = (s or {}).get("resource", "")
            if is_private(url):
                seen.setdefault(url, []).append(rel)
    return dict(sorted(seen.items()))


# ------------------------------------------------------------------------------ release feeds

FEED_KINDS = ("github", "gitlab", "terraform-provider", "endoflife")


def load_feeds(path):
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    feeds = data.get("releases") or []
    for f in feeds:
        kinds = [k for k in FEED_KINDS if k in f]
        if len(kinds) != 1:
            raise ValueError("feed %r must name exactly one of %s" % (f.get("name"), FEED_KINDS))
        f["kind"] = kinds[0]
    return feeds


_PRE = re.compile(r"(alpha|beta|rc|pre|dev|snapshot|nightly|canary)", re.I)


_VERSION = re.compile(r"\d+(?:\.\d+){0,3}")


def _version(tag):
    return re.sub(r"^(?:[a-z-]+/)?v?", "", tag.strip())


def _stable(tag):
    return not _PRE.search(tag)


def _highest(candidates):
    """The highest version among (version, released) pairs listed newest-published first.

    Release lists are ordered by publication, not by version: a project patching several lines
    publishes 1.18.6 after 1.19.1, and taking the first entry would make "latest" go backwards.
    On equal versions the first (most recently published) wins. A tag that is not a version once
    its prefix is stripped (`untagged-ce74…`, `helm-chart-2.11.0`) is not a candidate: its digits
    would otherwise be read as a version number and win.
    """
    best = None
    for version, released in candidates:
        if not _VERSION.fullmatch(version):
            continue
        key = tuple(_parts(version) + [0, 0, 0])[:3]
        if best is None or key > best[0]:
            best = (key, version, released)
    if best is None:
        raise LookupError("no stable release in the last 30")
    return best[1], best[2]


def resolve_feed(feed, fetcher):
    """Return {"latest": ..., "released": ..., "source": ..., ["eol": ...]} for one feed."""
    kind = feed["kind"]
    if kind == "github":
        url = "https://api.github.com/repos/%s/releases?per_page=30" % feed["github"]
        rels = json.loads(fetcher.get(url, api=True).body)
        prefix = feed.get("tag_prefix", "")
        latest, released = _highest(
            (_version(r.get("tag_name", "")[len(prefix):]), (r.get("published_at") or "")[:10])
            for r in rels
            if not (r.get("draft") or r.get("prerelease")) and _stable(r.get("tag_name", ""))
            and r.get("tag_name", "").startswith(prefix))
        return {"latest": latest, "released": released,
                "source": "https://github.com/%s/releases" % feed["github"]}
    if kind == "gitlab":
        proj = urllib.parse.quote(feed["gitlab"], safe="")
        url = "https://gitlab.com/api/v4/projects/%s/releases?per_page=30" % proj
        latest, released = _highest(
            (_version(r.get("tag_name", "")), (r.get("released_at") or "")[:10])
            for r in json.loads(fetcher.get(url, api=True).body)
            if _stable(r.get("tag_name", "")) and not r.get("upcoming_release"))
        return {"latest": latest, "released": released,
                "source": "https://gitlab.com/%s/-/releases" % feed["gitlab"]}
    if kind == "terraform-provider":
        url = "https://registry.terraform.io/v1/providers/%s" % feed["terraform-provider"]
        data = json.loads(fetcher.get(url, api=True).body)
        return {"latest": data["version"], "released": (data.get("published_at") or "")[:10],
                "source": "https://registry.terraform.io/providers/%s" % feed["terraform-provider"]}
    # endoflife: newest cycle, plus the support state of the cycle the bundle states
    url = "https://endoflife.date/api/%s.json" % feed["endoflife"]
    cycles = json.loads(fetcher.get(url, api=True).body)
    newest = cycles[0]
    out = {"latest": str(newest.get("latest") or newest["cycle"]),
           "released": str(newest.get("latestReleaseDate") or newest.get("releaseDate") or ""),
           "source": "https://endoflife.date/%s" % feed["endoflife"]}
    stated = str(feed.get("bundle_states", ""))
    for c in cycles:
        if stated and (stated == str(c["cycle"]) or stated.startswith(str(c["cycle"]) + ".")):
            out["eol"] = c.get("eol")
            break
    return out


def _parts(v):
    return [int(p) for p in re.findall(r"\d+", str(v))[:3]]


def drift(stated, latest):
    """How far the bundle's stated version is behind: 'major' | 'minor' | 'patch' | '' (current).

    A stated line such as "1.35" is compared on the components it gives, so it is current while
    any 1.35.x is latest.
    """
    s, l = _parts(stated), _parts(latest)
    if not s or not l:
        return ""
    for i, level in enumerate(("major", "minor", "patch")):
        if i >= len(s):
            return ""
        if i >= len(l) or s[i] == l[i]:
            continue
        return level if l[i] > s[i] else ""
    return ""


# ------------------------------------------------------------------------------ fetching

class Response:
    def __init__(self, status, body, final_url):
        self.status, self.body, self.final_url = status, body, final_url


class HttpFetcher:
    """urllib with a user agent, a timeout, and a GitHub token for API calls when one is set."""

    def __init__(self, timeout=30):
        self.timeout = timeout
        self.token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    def get(self, url, api=False):
        headers = {"User-Agent": USER_AGENT}
        if api and self.token and url.startswith("https://api.github.com/"):
            headers["Authorization"] = "Bearer " + self.token
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            raw = r.read()
            charset = r.headers.get_content_charset() or "utf-8"
            return Response(r.status, raw.decode(charset, errors="replace"), r.geturl())


# ------------------------------------------------------------------------------ collect & diff

def page_slug(url):
    p = urllib.parse.urlsplit(url)
    path = re.sub(r"[^A-Za-z0-9._-]+", "_", (p.netloc + p.path).strip("/"))
    return path + ".md"


def collect(bundle, feeds, fetcher, now, pages_dir=None):
    """Fetch every public page and feed. Returns (pages, releases, errors).

    Failures are returned, not raised: one unreachable site must not stop the other forty-seven
    from being checked. The caller keeps the previous entry for anything that failed.
    """
    pages, releases, errors = {}, {}, []
    for url, meta in page_sources(bundle).items():
        try:
            resp = fetcher.get(url)
            title, text = extract(resp.body)
            if not text.strip():
                raise ValueError("no content extracted")
        # HTTPException: a truncated body (IncompleteRead) is not an OSError. LookupError: a
        # charset the server names but Python does not know. Either is one page's problem.
        except (urllib.error.URLError, OSError, ValueError, LookupError, http.client.HTTPException) as e:
            errors.append({"kind": "page", "target": url, "error": str(e)[:200],
                           "title": meta["title"], "source_ids": meta["ids"], "cited_by": meta["cited_by"]})
            continue
        entry = {"title": title or meta["title"], "source_ids": meta["ids"], "cited_by": meta["cited_by"],
                 "sha256": digest(text), "chars": len(text), "outline": outline(text)}
        if resp.final_url.rstrip("/") != url.rstrip("/"):
            entry["moved_to"] = resp.final_url
        pages[url] = entry
        if pages_dir:
            os.makedirs(pages_dir, exist_ok=True)
            with open(os.path.join(pages_dir, page_slug(url)), "w", encoding="utf-8") as fh:
                fh.write("<!-- source: %s\n     fetched: %s\n     cited_by: %s -->\n\n"
                         % (resp.final_url, now, ", ".join(meta["cited_by"])))
                fh.write(text)
    for feed in feeds:
        try:
            got = resolve_feed(feed, fetcher)
        except (urllib.error.URLError, OSError, ValueError, KeyError, LookupError, IndexError,
                http.client.HTTPException) as e:
            errors.append({"kind": "release", "target": feed["name"], "error": str(e)[:200]})
            continue
        stated = str(feed.get("bundle_states", ""))
        got.update({"bundle_states": stated, "cited_by": list(feed.get("cited_by") or []),
                    "drift": drift(stated, got["latest"]) if stated else ""})
        releases[feed["name"]] = got
    return pages, releases, errors


def load_state(path):
    if not os.path.isfile(path):
        return {"schema_version": SCHEMA_VERSION, "pages": {}, "releases": {}}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def merge(prev, pages, releases, errors, now, cited=None):
    """New state: fresh entries where the fetch worked, the previous entry where it did not.

    `changed_at` moves only when the content hash (page) or latest version (feed) moves, so a week
    in which nothing changed leaves the state byte-identical apart from `checked_at`. Pages the
    bundle no longer cites (`cited` given) are dropped.
    """
    failed = {e["target"] for e in errors}
    page_errors = {e["target"]: e for e in errors if e.get("kind") == "page"}
    # On the first recorded state nothing is known about when a page last changed, so `changed_at`
    # stays null rather than claiming "today" — which would put every document up for
    # re-verification on a change nobody observed.
    first = now if (prev.get("pages") or prev.get("releases")) else None
    out = {"schema_version": SCHEMA_VERSION, "checked_at": now, "pages": {}, "releases": {}}
    for url in sorted(set(pages) | set(page_errors)):
        if cited is not None and url not in cited:
            continue
        old = prev.get("pages", {}).get(url)
        new = pages.get(url)
        if new is None:
            # Keep what was last seen, and since when the page stopped answering: one failed week
            # is the network, a page failing for a week or more is a reason to re-verify
            # (`pending_documents`). A page that never answered is recorded too — dropping it would
            # hide a source that was cited wrongly from the start.
            err = page_errors[url]
            kept = dict(old) if old else {
                "title": err.get("title", ""), "source_ids": err.get("source_ids", []),
                "cited_by": err.get("cited_by", []), "sha256": None, "chars": 0, "outline": [],
                "changed_at": None}
            kept["failing_since"] = (old or {}).get("failing_since") or now
            kept["last_error"] = err["error"]
            out["pages"][url] = kept
            continue
        same = old and old.get("sha256") == new["sha256"]
        new["changed_at"] = old.get("changed_at") if same else (now if old else first)
        out["pages"][url] = new
    for name in sorted(set(releases) | ({n for n in prev.get("releases", {}) if n in failed})):
        old = prev.get("releases", {}).get(name)
        new = releases.get(name)
        if new is None:
            out["releases"][name] = old
            continue
        same = old and old.get("latest") == new["latest"]
        new["changed_at"] = old.get("changed_at") if same else (now if old else first)
        # When the gap to the stated version last changed level ("" / patch / minor / major). A new
        # patch on an already-major gap is not news for the document; crossing into a new major is.
        # A gap seen for the first time is dated now: when it began is unknown, and dating it by
        # the latest release would hide every gap opened by an earlier release — a major that
        # shipped before the document was verified is not thereby one the document knows about.
        if old and old.get("drift", "") == new["drift"]:
            new["drift_changed_at"] = old.get("drift_changed_at")
        else:
            new["drift_changed_at"] = now if new["drift"] else None
        out["releases"][name] = new
    return out


def diff(prev, new):
    """What moved between two states, as lists the report renders."""
    pp, np_ = prev.get("pages", {}), new.get("pages", {})
    pr, nr = prev.get("releases", {}), new.get("releases", {})
    changed = [u for u in np_ if u in pp and pp[u].get("sha256") != np_[u].get("sha256")]
    added = [u for u in np_ if u not in pp]
    removed = [u for u in pp if u not in np_]
    moved = [u for u in np_ if np_[u].get("moved_to") and np_[u].get("moved_to") != pp.get(u, {}).get("moved_to")]
    bumped = [n for n in nr if n in pr and pr[n].get("latest") != nr[n].get("latest")]
    # The first recorded state is a baseline: every page is "new" to it, and reporting all of them
    # as documents to re-verify would bury the one run that matters under a false alarm.
    baseline = not pp and not pr
    return {"baseline": baseline, "changed": changed, "added": [] if baseline else added,
            "removed": removed, "moved": moved, "bumped": bumped,
            "new_feeds": [] if baseline else [n for n in nr if n not in pr]}


def content_equal(a, b):
    # checked_at and pending_as_of are dates of the run, not findings: a run that found nothing
    # new is not a change, so a quiet week writes nothing.
    strip = lambda s: {k: v for k, v in s.items() if k not in ("checked_at", "pending_as_of")}
    return strip(a) == strip(b)


def affected_documents(state, delta):
    docs = {}
    for key in ("changed", "added", "moved"):
        for url in delta[key]:
            for rel in state["pages"][url].get("cited_by", []):
                docs.setdefault(rel, []).append(url)
    for name in delta["bumped"]:
        for rel in state["releases"][name].get("cited_by", []):
            docs.setdefault(rel, []).append("release: " + name)
    return dict(sorted(docs.items()))


def _date(value):
    m = re.search(r"\d{4}-\d{2}-\d{2}", str(value or ""))
    return m.group(0) if m else ""


UNREACHABLE_AFTER_DAYS = 7   # one weekly run failing is the network; two in a row are the page


def _days_before(day, n):
    return (datetime.date.fromisoformat(day) - datetime.timedelta(days=n)).isoformat()


def pending_documents(bundle, state, today):
    """Documents awaiting re-verification, as {relative path: [reason, ...]}.

    Cumulative, not per run: a document stays listed until its `verified.at` passes the change
    that listed it — which is what `/architect:revise-knowledge` moves when it re-verifies one. So
    a week that saw nothing new still shows last week's unfinished work. A document is listed when

    * a page it cites changed after it was verified (baseline pages, `changed_at: null`, never
      count — nobody observed them change);
    * the gap between a version it states and the latest release changed level (patch / minor /
      major) after it was verified — a further patch on the same gap is not news (a feed without
      `bundle_states` is context, not a claim the document makes);
    * a page it cites redirects to a different page (`same_page` false) — typically a removed page
      sent to its section index. That is left to judgement, and stays listed until the source is
      replaced, whatever `verified.at` says;
    * a page it cites has failed to answer for UNREACHABLE_AFTER_DAYS or more (a removed page, a
      moved site). Like a redirect, it stays listed until the page answers again or the source is
      replaced;
    * the stated cycle of a version it states reached end of life after it was verified;
    * its `stale_after` has passed.
    """
    docs = bundle_documents(bundle)
    out = {}
    for rel, fm in docs.items():
        verified = _date((fm.get("verified") or {}).get("at") if isinstance(fm.get("verified"), dict) else "")
        why = []
        for url, page in state.get("pages", {}).items():
            page = page or {}
            if rel not in page.get("cited_by", []):
                continue
            changed = _date(page.get("changed_at"))
            if changed and changed > verified:
                why.append("page changed %s: %s" % (changed, url))
            if page.get("moved_to") and not same_page(url, page["moved_to"]):
                why.append("page redirected to a different page: %s -> %s" % (url, page["moved_to"]))
            failing = _date(page.get("failing_since"))
            if failing and failing <= _days_before(today, UNREACHABLE_AFTER_DAYS):
                why.append("page unreachable since %s: %s (%s)" % (failing, url, page.get("last_error", "")))
        for name, rel_ in state.get("releases", {}).items():
            r = rel_ or {}
            if rel not in r.get("cited_by", []):
                continue
            since = _date(r.get("drift_changed_at"))
            if r.get("drift") and since > verified:
                why.append("release %s %s: %s behind stated %s since %s"
                           % (name, r["latest"], r["drift"], r["bundle_states"], since))
            eol = _date(r.get("eol"))
            if eol and verified < eol <= today:
                why.append("release %s: stated %s reached end of life %s" % (name, r["bundle_states"], eol))
        stale = _date(fm.get("stale_after"))
        if stale and stale < today:
            why.append("past stale_after %s" % stale)
        if why:
            out[rel] = sorted(why)
    return out


def same_page(old, new):
    """Whether a redirect from `old` to `new` still lands on the page that was cited.

    Same path on another scheme or host, a trailing slash, or a path that extends the old one
    (`/docs/` -> `/docs/home/`, `/` -> `/en/stable/`) is the same page moved. Anything else — above
    all a path *above* the old one (`/security/overview/` -> `/security/`) — is how sites answer
    for a page they removed, and whether the claims resting on it survive is judgement.
    """
    o, n = urllib.parse.urlsplit(old), urllib.parse.urlsplit(new)
    op, np_ = o.path.rstrip("/"), n.path.rstrip("/")
    if op == np_:
        return True
    return o.netloc == n.netloc and np_.startswith(op + "/")


def apply_redirects(bundle, state):
    """Rewrite each same-page redirect's `resource` to its final URL, in the bundle frontmatter.

    The one bundle edit that needs no judgement: the site itself says where the page lives now, and
    the source keeps its `id`, so every `[id]` citation in the body still resolves. Only the
    frontmatter is touched, and only an exact quoted match. The state entry is re-keyed to the new
    URL so the next run sees no change. A redirect to a different page (`same_page`), or one some
    citing document does not carry as an exact quoted match, is left in the state as `moved_to`
    and not applied — re-keying without rewriting every citation would make the next run
    fetch the old URL again and see it as new. Returns [(document, old url, new url), ...].
    """
    applied = []
    for url in [u for u, p in state.get("pages", {}).items() if (p or {}).get("moved_to")]:
        new = state["pages"][url]["moved_to"]
        if not same_page(url, new):
            continue
        quoted = '"%s"' % url
        rewrites = []
        for rel in state["pages"][url].get("cited_by", []):
            path = os.path.join(bundle, *rel.split("/"))
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
            parts = body.split("---", 2)
            if len(parts) < 3 or quoted not in parts[1]:
                break
            rewrites.append((rel, path, parts))
        else:
            for rel, path, (_, front, rest) in rewrites:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("---" + front.replace(quoted, '"%s"' % new) + "---" + rest)
                applied.append((rel, url, new))
            entry = state["pages"].pop(url)
            entry.pop("moved_to")
        if url in state["pages"]:
            continue
        other = state["pages"].get(new)
        if other:
            other["cited_by"] = sorted(set(other.get("cited_by", [])) | set(entry.get("cited_by", [])))
            other["source_ids"] = sorted(set(other.get("source_ids", [])) | set(entry.get("source_ids", [])))
        else:
            state["pages"][new] = entry
    state["pages"] = dict(sorted(state["pages"].items()))
    return applied


def log_redirects(bundle, applied, today):
    """Append the redirect rewrites to the bundle's own log.md, in its language."""
    if not applied:
        return
    lines = ["", "## %s（自動）" % today, "",
             "- 出典ページのリダイレクトに合わせて `resource` を移転先 URL に更新（本文・出典 ID は変更なし）。"]
    lines += ["  - `%s`: %s → %s" % a for a in applied]
    with open(os.path.join(bundle, "log.md"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def render_report(state, delta, errors, private, applied=()):
    """REPORT.md — the run's findings, written for the reviewer of the weekly pull request."""
    L = ["---", 'title: "okf-k8s-tf upstream report"', "schema_version: 1",
         'generated_at: "%s"' % state["checked_at"], "generator: tools/refresh-okf-k8s-tf.py", "---", "",
         "# okf-k8s-tf upstream report", "",
         "What moved in the public sources of `knowledge/okf-k8s-tf/` since the previous recorded state.",
         "Observed-implementation statements (対象実装) are facts about a private snapshot and are",
         "**not** revised from these sources — only design guidance (設計指針), versions and freshness.", ""]
    pending = state.get("pending") or {}
    L += ["## Awaiting re-verification", ""]
    if delta.get("baseline"):
        L += ["Baseline run — the first recorded state. Page changes are reported from the next run.", ""]
    if pending:
        L += ["Cumulative: a document leaves this list when it is re-verified",
              "(`/architect:revise-knowledge`, which moves its `verified.at`).", "",
              "| Document | Why |", "|---|---|"]
        L += ["| `%s` | %s |" % (rel, "<br>".join(why)) for rel, why in pending.items()]
    else:
        L.append("None.")
    if applied:
        L += ["", "## Redirects applied", "",
              "Rewritten in the documents' frontmatter `resource` (the source `id` is unchanged):", ""]
        L += ["- `%s`: %s → %s" % a for a in applied]
    L += ["", "## Pages", "",
          "Checked %d public pages." % len(state["pages"]), ""]
    for key, label in (("changed", "Content changed"), ("moved", "Redirected, not applied"),
                       ("added", "Newly cited"), ("removed", "No longer cited")):
        # A redirect that was applied is listed once, under "Redirects applied"; its state entry
        # now lives under the new URL. Only redirects left unapplied are listed here.
        urls = [u for u in delta[key] if u in state["pages"]]
        if urls:
            L.append("### %s" % label)
            L.append("")
            for u in urls:
                e = state["pages"].get(u) or {}
                extra = " → %s" % e.get("moved_to", "") if key == "moved" else ""
                cited = ", ".join("`%s`" % c for c in e.get("cited_by", []))
                L.append("- %s%s%s" % (u, extra, (" — cited by " + cited) if cited else ""))
            L.append("")
    L += ["## Releases", "",
          "| Technology | Bundle states | Latest stable | Released | Behind | Source |",
          "|---|---|---|---|---|---|"]
    for name, r in state["releases"].items():
        if not r:
            continue
        mark = "**%s**" % r["latest"] if name in delta["bumped"] else r["latest"]
        eol = " (EOL %s)" % r["eol"] if r.get("eol") not in (None, False, "") else ""
        L.append("| %s | %s%s | %s | %s | %s | %s |" % (
            name, r.get("bundle_states") or "—", eol, mark, r.get("released", ""), r.get("drift") or "—", r["source"]))
    L += ["", "Bold = changed since the previous run. *Behind* compares the version the bundle states",
          "with the latest stable release; the stated version is an observation of the snapshot, so a",
          "gap is a question for the platform, not an error in the bundle.", ""]
    if errors:
        L += ["## Could not be checked this run", "",
              "The previous state is kept for these; they are retried next run.", ""]
        for e in errors:
            since = (state["pages"].get(e["target"]) or {}).get("failing_since") if e["kind"] == "page" else None
            L.append("- %s `%s` — %s%s" % (e["kind"], e["target"], e["error"],
                                           " (failing since %s)" % _date(since) if since else ""))
        L.append("")
    L += ["## Not fetched by design", ""]
    L += ["- %s — private; cited by %s" % (u, ", ".join("`%s`" % r for r in rels)) for u, rels in private.items()]
    return "\n".join(L) + "\n"
