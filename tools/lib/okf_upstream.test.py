#!/usr/bin/env python3
"""Contract test for `okf_upstream.py` — the collector behind the weekly k8s-tf bundle refresh.

Offline: the network is a fake fetcher. What it pins down:

1. What is watched — every public page the bundle cites, never a private scalar-labs repository,
   and every release feed in sources.yaml well-formed, naming documents that exist and stating a
   version those documents actually state.
2. What counts as a change — the extracted text ignores page chrome, so a reflowed nav bar is not
   a documentation change, while an edited paragraph is.
3. What the state keeps — an unreachable source keeps its previous entry, `changed_at` moves only
   with the content, and a week with nothing new is byte-identical apart from `checked_at`.
4. What the report says — the baseline run is not a flood of false alarms, a changed page names
   the bundle documents that cite it, and the private sources are listed as skipped on purpose.

Exit 1 on any failure.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import okf_upstream as U  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUNDLE = os.path.join(ROOT, "knowledge", "okf-k8s-tf")
UPSTREAM = os.path.join(ROOT, "knowledge", "okf-k8s-tf-upstream")

checks = failures = 0


def check(label, condition, detail=""):
    global checks, failures
    checks += 1
    if condition:
        print("  ok    %s" % label)
    else:
        failures += 1
        print("  FAIL  %s%s" % (label, (" — %s" % detail) if detail else ""))


def page(body, nav="<a>Home</a>", title="Doc"):
    return ("<html><head><title>%s</title><script>var t=1</script></head><body>"
            "<header><nav>%s</nav></header><main><h1>Title</h1>"
            "<p>First   paragraph\n spans lines.</p><ul><li>one</li><li>two</li></ul>%s"
            "<pre>code  kept\n    indented</pre></main><footer>© 2026</footer></body></html>"
            % (title, nav, body))


class FakeFetcher:
    def __init__(self, pages=None, api=None, fail=()):
        self.pages, self.api, self.fail = pages or {}, api or {}, set(fail)

    def get(self, url, api=False):
        if url in self.fail:
            raise urllib.error.URLError("unreachable")
        if api:
            return U.Response(200, json.dumps(self.api[url]), url)
        body = self.pages.get(url, page("<p>default</p>"))
        final = url
        if isinstance(body, tuple):
            body, final = body
        return U.Response(200, body, final)


# ------------------------------------------------------------------------------ watched set

print("What is watched")

cited = U.page_sources(BUNDLE)
private = U.private_sources(BUNDLE)
check("the bundle cites public pages", len(cited) >= 40, len(cited))
check("no private scalar-labs source is ever fetched",
      not [u for u in cited if u.startswith("https://gitlab.com/scalar-labs/")])
check("the private sources are known, so the report can list them", len(private) == 2, sorted(private))
check("every watched page is https", all(u.startswith("https://") for u in cited))
check("every watched page names the bundle documents citing it",
      all(meta["cited_by"] for meta in cited.values()))

feeds = U.load_feeds(os.path.join(UPSTREAM, "sources.yaml"))
check("sources.yaml declares release feeds", len(feeds) >= 20, len(feeds))
names = [f["name"] for f in feeds]
check("feed names are unique", len(names) == len(set(names)))
docs = U.bundle_documents(BUNDLE)
unknown = sorted({(f["name"], d) for f in feeds for d in f.get("cited_by") or [] if d not in docs})
check("every feed cites only documents that exist", not unknown, unknown)
misstated = []
for f in feeds:
    stated = str(f.get("bundle_states") or "")
    for d in f.get("cited_by") or []:
        if stated and d in docs:
            with open(os.path.join(BUNDLE, d), encoding="utf-8") as fh:
                if stated not in fh.read():
                    misstated.append((f["name"], stated, d))
check("every stated version appears in the documents it is cited by", not misstated, misstated)
try:
    tmp = tempfile.mkdtemp()
    bad = os.path.join(tmp, "s.yaml")
    with open(bad, "w") as fh:
        fh.write("releases:\n  - name: X\n    github: a/b\n    endoflife: c\n")
    try:
        U.load_feeds(bad)
        check("a feed naming two kinds is refused", False)
    except ValueError:
        check("a feed naming two kinds is refused", True)
finally:
    shutil.rmtree(tmp)

# ------------------------------------------------------------------------------ extraction

print("What counts as a change")

title, text = U.extract(page("<p>body</p>"))
check("the title is read", title == "Doc", title)
check("headings survive as Markdown", "# Title" in text, text)
check("script, nav, header and footer are dropped",
      "var t" not in text and "Home" not in text and "©" not in text, text)
check("whitespace outside <pre> is collapsed", "First paragraph spans lines." in text, text)
check("<pre> keeps its indentation", "    indented" in text, text)
check("list items are marked", "- one" in text and "- two" in text, text)
check("a changed nav is not a changed page",
      U.digest(U.extract(page("<p>b</p>", nav="<a>New nav</a>"))[1]) == U.digest(U.extract(page("<p>b</p>"))[1]))
check("a changed paragraph is a changed page",
      U.digest(U.extract(page("<p>b</p>"))[1]) != U.digest(U.extract(page("<p>c</p>"))[1]))
check("an <article> is the root when there is no <main>",
      U.extract("<body><nav>x</nav><article><p>in</p></article><p>out</p></body>")[1].strip() == "in")
check("the outline is the heading lines", U.outline("# A\ntext\n## B\n#### deep\n") == ["# A", "## B"])

print("Versions")

check("a patch behind", U.drift("1.14.8", "1.14.9") == "patch")
check("a minor behind", U.drift("1.14.8", "1.16.0") == "minor")
check("a major behind", U.drift("5.94.1", "6.0.0") == "major")
check("a stated line is current for any patch on it", U.drift("1.35", "1.35.4") == "")
check("a stated major is current for any minor on it", U.drift("27", "27.5.1") == "")
check("ahead is not behind", U.drift("2.0.0", "1.9.9") == "")

gh = {"kind": "github", "github": "o/r", "name": "R"}
api = {"https://api.github.com/repos/o/r/releases?per_page=30": [
    {"tag_name": "v2.0.0-rc.1", "prerelease": True, "published_at": "2026-09-20T00:00:00Z"},
    {"tag_name": "v1.9.0-beta", "prerelease": False, "published_at": "2026-09-19T00:00:00Z"},
    {"tag_name": "helm-chart-9.9.9", "prerelease": False, "published_at": "2026-09-18T00:00:00Z"},
    {"tag_name": "v1.8.2", "prerelease": False, "published_at": "2026-09-01T00:00:00Z"}]}
got = U.resolve_feed(gh, FakeFetcher(api=api))
check("without tag_prefix a monorepo's other tags win — which is why the option exists",
      got["latest"] == "helm-chart-9.9.9", got)
got = U.resolve_feed(dict(gh, tag_prefix="v"), FakeFetcher(api=api))
check("prereleases and -beta tags are skipped", got["latest"] == "1.8.2" and got["released"] == "2026-09-01", got)
eol = {"kind": "endoflife", "endoflife": "k", "name": "K", "bundle_states": "1.35"}
got = U.resolve_feed(eol, FakeFetcher(api={"https://endoflife.date/api/k.json": [
    {"cycle": "1.37", "latest": "1.37.1", "latestReleaseDate": "2026-09-23"},
    {"cycle": "1.35", "latest": "1.35.9", "eol": "2027-02-28"}]}))
check("endoflife reports the newest release and the stated cycle's EOL",
      got["latest"] == "1.37.1" and got["eol"] == "2027-02-28", got)

# ------------------------------------------------------------------------------ state

print("What the state keeps")

tmp = tempfile.mkdtemp()
try:
    b = os.path.join(tmp, "bundle")
    os.makedirs(os.path.join(b, "foundation"))
    with open(os.path.join(b, "foundation", "x.md"), "w") as fh:
        fh.write('---\ntitle: X\nstale_after: 2026-01-01\nsources:\n'
                 '  - { id: a, resource: "https://a.example/doc", title: A }\n'
                 '  - { id: b, resource: "https://b.example/doc", title: B }\n'
                 '  - { id: p, resource: "https://gitlab.com/scalar-labs/private", title: P }\n---\n# x\n')
    feed = [{"name": "Tool", "kind": "terraform-provider", "terraform-provider": "n/t",
             "bundle_states": "1.0.0", "cited_by": ["foundation/x.md"]}]
    reg = {"https://registry.terraform.io/v1/providers/n/t": {"version": "1.0.0", "published_at": "2026-01-01"}}
    pages_dir = os.path.join(tmp, "pages")

    p1, r1, e1 = U.collect(b, feed, FakeFetcher(api=reg), "T1", pages_dir)
    check("the private source is not fetched", set(p1) == {"https://a.example/doc", "https://b.example/doc"}, sorted(p1))
    check("page text is held locally", len(os.listdir(pages_dir)) == 2, os.listdir(pages_dir))
    s1 = U.merge(U.load_state(os.path.join(tmp, "none.json")), p1, r1, e1, "T1")
    d1 = U.diff({"pages": {}, "releases": {}}, s1)
    check("the first state is a baseline, not 2 new pages to re-verify",
          d1["baseline"] and not d1["added"] and not U.affected_documents(s1, d1))

    p2, r2, e2 = U.collect(b, feed, FakeFetcher(api=reg), "T2")
    s2 = U.merge(s1, p2, r2, e2, "T2")
    check("an unchanged week differs only in checked_at", U.content_equal(s1, s2) and s1["checked_at"] != s2["checked_at"])
    check("changed_at stays put when nothing moved", s2["pages"]["https://a.example/doc"]["changed_at"] == "T1")

    moved = FakeFetcher(pages={"https://a.example/doc": page("<p>edited</p>"),
                               "https://b.example/doc": (page("<p>default</p>"), "https://b.example/new")},
                        api={"https://registry.terraform.io/v1/providers/n/t": {"version": "2.1.0", "published_at": "2026-09-01"}})
    p3, r3, e3 = U.collect(b, feed, moved, "T3")
    s3 = U.merge(s2, p3, r3, e3, "T3")
    d3 = U.diff(s2, s3)
    check("an edited page is reported changed", d3["changed"] == ["https://a.example/doc"], d3)
    check("a redirect is reported moved", d3["moved"] == ["https://b.example/doc"], d3)
    check("a new release is reported bumped, with its drift", d3["bumped"] == ["Tool"] and s3["releases"]["Tool"]["drift"] == "major", s3["releases"])
    check("changed_at moves with the content", s3["pages"]["https://a.example/doc"]["changed_at"] == "T3")
    aff = U.affected_documents(s3, d3)
    check("the citing document is listed for re-verification", list(aff) == ["foundation/x.md"], aff)

    p4, r4, e4 = U.collect(b, feed, FakeFetcher(api=reg, fail={"https://a.example/doc"}), "T4")
    s4 = U.merge(s3, p4, r4, e4, "T4")
    check("an unreachable page is reported, not raised", [e["target"] for e in e4] == ["https://a.example/doc"], e4)
    check("an unreachable page keeps its previous entry", s4["pages"]["https://a.example/doc"] == s3["pages"]["https://a.example/doc"])

    s5 = U.merge(s3, p4, r4, [], "T5", cited={"https://b.example/doc"})
    check("a page the bundle no longer cites is dropped", list(s5["pages"]) == ["https://b.example/doc"], list(s5["pages"]))

    print("What the report says")
    rep = U.render_report(s3, d3, e4, U.private_sources(b), U.stale_documents(b, "2026-09-28"))
    check("the report starts with frontmatter", rep.startswith("---\n") and "schema_version: 1" in rep)
    check("the report names the document to re-verify", "| `foundation/x.md` |" in rep, rep)
    check("the report lists the redirect target", "https://b.example/new" in rep)
    check("the report marks the bumped release", "**2.1.0**" in rep)
    check("the report lists what could not be checked", "## Could not be checked this run" in rep)
    check("the report lists the private source as skipped by design",
          "https://gitlab.com/scalar-labs/private — private" in rep)
    check("the report lists documents past stale_after", "`foundation/x.md` — 2026-01-01" in rep)
finally:
    shutil.rmtree(tmp)

# ------------------------------------------------------------------------------ committed state

print("The committed state agrees with the bundle")

state = U.load_state(os.path.join(UPSTREAM, "state.json"))
check("state.json is recorded", bool(state.get("pages")))
missing = sorted(set(cited) - set(state.get("pages", {})))
check("every cited public page has a recorded state", not missing, missing)
extra = sorted(set(state.get("pages", {})) - set(cited))
check("the state records no page the bundle does not cite", not extra, extra)
check("state.json holds no page text", all("text" not in (e or {}) for e in state.get("pages", {}).values()))
check("every feed has a recorded state", set(names) <= set(state.get("releases", {})),
      sorted(set(names) - set(state.get("releases", {}))))

ignored = subprocess.run(["git", "-C", ROOT, "check-ignore", "-q",
                          "knowledge/okf-k8s-tf-upstream/pages/x.md"]).returncode == 0
check("the local page text is git-ignored", ignored)

print("\n%d checks, %d failed" % (checks, failures))
sys.exit(1 if failures else 0)
