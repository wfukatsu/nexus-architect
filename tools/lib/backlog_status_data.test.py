#!/usr/bin/env python3
"""Executable check of the backlog-status derivation contract.

backlog_status_data.py encodes the backlog family's state rules (deliver-backlog /
export-backlog / backlog-checklists contracts); this asserts them as behaviour:

- delivery status precedence: tracker sync cache > impl.status > todo, and the node's
  `labels` array is NEVER read as state (it is the creation seed);
- stage derivation: M = pr.merged or done; R = M or pr.url; I = R or status review/done;
- tree building: positional numeric order, F-nodes after positional siblings, orphans
  kept under a synthetic bucket;
- parent roll-up: own impl.status wins, else child aggregation;
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
