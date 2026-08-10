#!/usr/bin/env python3
"""Executable check of the backlog-status derivation contract.

backlog_status_data.py encodes the backlog family's state rules (deliver-backlog /
export-backlog / backlog-checklists contracts); this asserts them as behaviour:

- delivery status precedence: tracker sync cache > impl.status > todo, and the node's
  `labels` array is NEVER read as state (it is the creation seed);
- stage derivation: M = pr.merged or done; R = M or pr.url; I = R or status review/done;
- tree building: positional numeric order, F-nodes after positional siblings, orphans
  kept under a synthetic bucket;
- parent roll-up: own impl.status wins, else child aggregation, and a parent's own
  tracker label is drift rather than an override;
- tracker sync: the manifest header is inferred from the nodes' URLs, GitLab Epics are
  fetched from the group as well as Issues from the project, and a group Epic iid never
  collides with a project Issue iid;
- summary counts.

    python3 tools/lib/backlog_status_data.test.py                 # embedded fixture
    python3 tools/lib/backlog_status_data.test.py manifest.json   # a real manifest

Exit status 0 = all checks pass, 1 = at least one failed.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backlog_status_data as B  # noqa: E402


def node(lid, level, parent, labels=None, impl=None, pr=None, origin=None, iid=None):
    n = {"local_id": lid, "level": level, "title": "t-" + lid, "body": "…",
         "labels": labels or [], "parent_local_id": parent, "source_reports": [],
         "traceability": [], "remote": {"iid": iid, "url": "https://x/%s" % iid}
         if iid else None}
    if impl:
        n["impl"] = impl
    if pr:
        n["pr"] = pr
    if origin:
        n["origin"] = origin
    return n


FIXTURE = {
    "platform": "gitlab", "project": "g/p", "group": "g",
    "nodes": [
        node("E1", "epic", None, iid=1),
        node("SE1.1", "sub-epic", "E1", iid=2),
        node("SE1.2", "sub-epic", "E1", iid=3, impl={"status": "done"}),
        # labels claim todo but impl.status says done — labels must be ignored
        node("I1.1.1", "issue", "SE1.1", labels=["status::todo"], iid=11,
             impl={"status": "done"}, pr={"url": "https://x/mr/1", "merged": True}),
        node("I1.1.2", "issue", "SE1.1", iid=12, impl={"status": "review"},
             pr={"url": "https://x/mr/2"}),
        node("I1.1.3", "issue", "SE1.1", iid=13, impl={"status": "blocked"}),
        node("I1.1.10", "issue", "SE1.1", iid=14),   # numeric sort: after I1.1.3
        node("I1.1.F1", "issue", "SE1.1", iid=15,    # follow-up: after positional sibs
             origin={"discovered_in": "I1.1.1", "source": "implement",
                     "reference": "r", "queued_at": "2026-08-06T00:00:00Z"}),
        node("I1.2.1", "issue", "SE1.2", iid=21, impl={"status": "done"},
             pr={"url": "https://x/mr/3", "merged": True}),
        node("I9.9.9", "issue", "SE9.9", iid=99),    # orphan: parent not in manifest
    ],
}

FAILURES = 0


def check(name, cond, detail=""):
    global FAILURES
    print("  [%s] %s%s" % ("ok" if cond else "FAIL", name,
                           (" — " + str(detail)) if (detail and not cond) else ""))
    if not cond:
        FAILURES += 1


GL = "https://gitlab.com"
GL_PROJECT = "acme/team/app"
GL_GROUP = "acme/team"


def gl_node(lid, level, parent, kind, iid):
    """A node carrying the kind of URL export-backlog records for it on GitLab."""
    url = "%s/%s/-/%s/%d" % (GL, "groups/" + GL_GROUP if kind == "epic" else GL_PROJECT,
                             "epics" if kind == "epic" else "work_items", iid)
    n = node(lid, level, parent, iid=iid)
    n["remote"] = {"iid": iid, "url": url}
    return n


# A bare node array, as the manifests written before the header existed look, with the
# GitLab shape that used to break sync: Epics numbered from 1 in the group alongside
# Issues numbered from 1 in the project.
BARE = [
    gl_node("E1", "epic", None, "epic", 1),
    gl_node("SE1.1", "sub-epic", "E1", "epic", 2),
    gl_node("I1.1.1", "issue", "SE1.1", "issue", 1),
    gl_node("I1.1.2", "issue", "SE1.1", "issue", 2),
]


def run_sync_checks():
    manifest = {"nodes": [dict(n) for n in BARE]}
    B.infer_tracker(manifest)
    check("a bare manifest infers its platform, project and group from the node URLs",
          (manifest["platform"], manifest["project"], manifest["group"])
          == ("gitlab", GL_PROJECT, GL_GROUP), manifest.get("project"))

    sources = B.tracker_sources(manifest)
    check("a GitLab manifest syncs the project's Issues and the group's Epics",
          [(s[0], s[2]) for s in sources] == [("issues", "issue"), ("epics", "epic")],
          sources)
    check("the group path is URL-encoded for the epics endpoint",
          "groups/acme%2Fteam/epics" in " ".join(sources[1][1]), sources[1][1])

    # Two sources, both numbering from 1 — the collision that used to hand Epic 1 the
    # status of Issue #1 as soon as anything was synced.
    now = None
    epics = B._entries([{"iid": 1, "web_url": BARE[0]["remote"]["url"],
                         "labels": ["status::todo"], "state": "opened"},
                        {"iid": 2, "web_url": BARE[1]["remote"]["url"],
                         "labels": ["status::todo"], "state": "opened"}],
                       "epic", "status::", "::", now)
    issues = B._entries([{"iid": 1, "web_url": BARE[2]["remote"]["url"],
                          "labels": ["status::done"], "state": "closed"},
                         {"iid": 2, "web_url": BARE[3]["remote"]["url"],
                          "labels": [], "state": "closed"}],
                        "issue", "status::", "::", now)
    cache = B._index(epics + issues)
    check("a closed item with no status label still reads as done",
          B.item_status({"labels": [], "state": "closed"}, "status::", "::") == "done")
    check("the ambiguous bare iid is dropped when two kinds share it",
          1 not in cache and 2 not in cache, sorted(str(k) for k in cache))
    by_id, children, states = B.derive_all(manifest, cache)
    check("Epic 1 keeps its own status instead of Issue #1's",
          states["I1.1.1"]["status"] == "done" and states["E1"]["tracker_status"]
          == "todo", (states["E1"], states["I1.1.1"]))
    check("a parent aggregates its children over its own stale tracker label",
          states["SE1.1"]["status"] == "done" and states["SE1.1"]["source"] == "rollup",
          states["SE1.1"])
    check("the disagreeing parent label is reported as drift",
          states["SE1.1"]["drift"] and states["SE1.1"]["rollup"], states["SE1.1"])

    # `gh issue list --limit 1000` returns a window, not the tracker; a node outside it
    # used to be indistinguishable from an unlabelled one — both rendered as todo.
    check("a node the fetch never returned is reported, not absorbed",
          len(B.unreached({"nodes": manifest["nodes"] + [
              gl_node("I1.1.9", "issue", "SE1.1", "issue", 99)]}, cache)) == 1,
          B.unreached(manifest, cache))
    check("an unlabelled open item is not mistaken for an unreached one",
          B.unreached(manifest, cache) == [], B.unreached(manifest, cache))

    check("a GitHub issue URL parses to one repository and no group",
          B.parse_remote_url("https://github.com/acme/app/issues/12")
          == ("github", "issue", "acme/app", 12))
    check("/-/issues/ and /-/work_items/ are the same item",
          B.tracker_key("%s/%s/-/issues/9" % (GL, GL_PROJECT))
          == B.tracker_key("%s/%s/-/work_items/9" % (GL, GL_PROJECT)))


def run(manifest):
    by_id, children, states = B.derive_all(manifest)

    print("delivery status precedence")
    check("labels array is ignored (impl.status=done wins over status::todo seed)",
          states["I1.1.1"]["status"] == "done", states["I1.1.1"])
    check("no impl -> todo (source=seed)",
          states["I1.1.10"]["status"] == "todo" and states["I1.1.10"]["source"] == "seed")
    check("impl.status=blocked surfaces", states["I1.1.3"]["status"] == "blocked")
    sync = {12: {"status": "done", "fetched_at": None}}
    s = B.derive_state(by_id["I1.1.2"], sync)
    check("tracker cache wins over impl.status and flags drift",
          s["status"] == "done" and s["source"] == "tracker" and s["drift"], s)

    print("stage derivation")
    check("merged pr -> [I][R][M]",
          states["I1.1.1"]["stages"] == {"implemented": True, "reviewed": True,
                                         "merged": True})
    check("pr without merge -> [I][R][.]",
          states["I1.1.2"]["stages"] == {"implemented": True, "reviewed": True,
                                         "merged": False})
    check("doing/todo without pr -> [.][.][.]",
          states["I1.1.10"]["stages"] == {"implemented": False, "reviewed": False,
                                          "merged": False})

    print("tree building")
    kids = [n["local_id"] for n in children["SE1.1"]]
    check("positional numeric order, F-node last",
          kids == ["I1.1.1", "I1.1.2", "I1.1.3", "I1.1.10", "I1.1.F1"], kids)
    check("orphan kept under the synthetic bucket",
          [n["local_id"] for n in children.get("?", [])] == ["I9.9.9"])
    check("F-node flagged as followup", states["I1.1.F1"]["followup"])

    print("tree filtering")
    ids = [n["local_id"] for n, _, _ in B.flatten_tree(children, states)]
    check("no filter shows the orphan", "I9.9.9" in ids, ids)
    ids = [n["local_id"] for n, _, _ in
           B.flatten_tree(children, states, epic_filter="E1")]
    check("epic filter excludes the orphan (no Epic owns it)",
          "I9.9.9" not in ids and "E1" in ids, ids)
    ids = [n["local_id"] for n, _, _ in
           B.flatten_tree(children, states, status_filter="blocked")]
    check("status filter applies to the orphan too", "I9.9.9" not in ids, ids)

    print("roll-up")
    check("parent's own impl.status wins (SE1.2 done from merge-issue roll-up)",
          states["SE1.2"]["status"] == "done" and states["SE1.2"]["stages"]["merged"])
    check("child aggregation: any blocked -> blocked (SE1.1)",
          states["SE1.1"]["status"] == "blocked", states["SE1.1"])
    check("epic aggregates its sub-epics", states["E1"]["status"] == "blocked")

    print("summary & counts")
    summary = B.overall_summary(manifest, states)
    check("issue totals", summary["issues_total"] == 7 and summary["issues_done"] == 2,
          summary)
    done, total = B.descendant_issue_counts(by_id["E1"], children, states)
    check("descendant counts over the epic", (done, total) == (2, 6), (done, total))

    print("tracker sync")
    run_sync_checks()

    print("actions")
    cmd = B.default_action(by_id["I1.1.2"], states["I1.1.2"])
    check("review+pr defaults to merge", cmd[1] == "/architect:merge-issue I1.1.2", cmd)
    cmd = B.default_action(by_id["I1.1.10"], states["I1.1.10"])
    check("todo defaults to implement",
          cmd[1] == "/architect:implement-backlog I1.1.10", cmd)
    acts = dict(B.actions_for(by_id["E1"], states["E1"], queue_count=2))
    check("epic offers deliver --epic",
          acts.get("deliver") == "/architect:deliver-backlog --epic=E1", acts)
    check("queue count adds the flush action",
          any(k.startswith("flush follow-ups") for k in acts))


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            manifest = json.load(f)
        if isinstance(manifest, list):
            manifest = {"platform": "", "project": "", "group": "", "nodes": manifest}
        print("checking %s" % sys.argv[1])
    else:
        manifest = FIXTURE
        print("checking embedded fixture")
    run(manifest)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
