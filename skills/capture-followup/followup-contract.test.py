#!/usr/bin/env python3
"""Executable check of the /architect:capture-followup ID & manifest contract.

SKILL.md states the follow-up contract in prose (the "Follow-up ID & Manifest
Contract" section); this asserts it as behaviour, so a later edit to the skill —
or to export-backlog's --update semantics — cannot quietly break it:

- F-index allocation: next local ID under a parent is max existing F index + 1;
  positional children never influence it.
- Namespace disjointness: an F-suffixed ID never collides with a positional ID,
  and allocation never emits an ID already present in the manifest.
- Node shape: a follow-up node carries the export-backlog fields plus a
  well-formed `origin`; positional nodes carry no `origin`.
- Parent resolution: the default parent is the Sub-Epic of the single
  `impl.status == "doing"` Issue; zero or multiple `doing` Issues mean "ask".

    python3 skills/capture-followup/followup-contract.test.py                 # embedded fixture
    python3 skills/capture-followup/followup-contract.test.py manifest.json   # a real manifest

Exit status 0 = all checks pass, 1 = at least one failed (same convention as
hooks/*.sh in CLI mode).
"""
import json
import re
import sys

FOLLOWUP_ID = re.compile(r"^I(\d+(?:\.\d+)*)\.F(\d+)$")
POSITIONAL_ID = re.compile(r"^(E\d+|SE\d+\.\d+|I\d+\.\d+\.\d+)$")
ORIGIN_SOURCES = {"implement", "review", "merge", "manual"}
NODE_FIELDS = {"local_id", "level", "title", "body", "labels", "parent_local_id",
               "source_reports", "traceability", "remote"}

FIXTURE = {
    "platform": "gitlab",
    "project": "group/project",
    "group": "group",
    "nodes": [
        {"local_id": "E1", "level": "epic", "title": "Initiative", "body": "…",
         "labels": ["type:epic", "status::todo"], "parent_local_id": None,
         "source_reports": [], "traceability": [], "remote": {"iid": 1}},
        {"local_id": "SE1.1", "level": "sub-epic", "title": "Payments", "body": "…",
         "labels": ["type:sub-epic", "status::todo", "domain:payments"],
         "parent_local_id": "E1", "source_reports": [], "traceability": [],
         "remote": {"iid": 2}},
        {"local_id": "SE1.2", "level": "sub-epic", "title": "Orders", "body": "…",
         "labels": ["type:sub-epic", "status::todo", "domain:orders"],
         "parent_local_id": "E1", "source_reports": [], "traceability": [],
         "remote": {"iid": 3}},
        {"local_id": "I1.2.1", "level": "issue", "title": "Order entity", "body": "…",
         "labels": ["type:issue", "status::todo"], "parent_local_id": "SE1.2",
         "source_reports": ["reports/02_spec/data-model.md"], "traceability": ["ENT-01"],
         "remote": {"iid": 4}, "impl": {"status": "done"}},
        {"local_id": "I1.2.2", "level": "issue", "title": "Order API", "body": "…",
         "labels": ["type:issue", "status::todo"], "parent_local_id": "SE1.2",
         "source_reports": ["reports/03_domain/api-design.md"], "traceability": ["API-02"],
         "remote": {"iid": 5}, "impl": {"status": "doing"}},
        # an existing follow-up, so allocation under SE1.2 must yield F2, not F1
        {"local_id": "I1.2.F1", "level": "issue", "title": "Extract retry policy",
         "body": "…", "labels": ["type:issue", "status::todo", "followup"],
         "parent_local_id": "SE1.2",
         "source_reports": ["reports/backlog/impl-log/I1.2.1.md"], "traceability": [],
         "origin": {"discovered_in": "I1.2.1", "source": "implement",
                    "reference": "reports/backlog/impl-log/I1.2.1.md#finding-2",
                    "queued_at": "2026-08-06T02:00:00Z"},
         "remote": {"iid": 6}},
    ],
}


def allocate_followup_id(nodes, parent_local_id):
    """The allocation rule SKILL.md Step 4 states: max F index under the parent + 1.

    The numeric stem comes from the parent (SE1.2 -> I1.2.F<n>, E1 -> I1.F<n>).
    """
    stem = re.sub(r"^(SE|E|I)", "", parent_local_id)
    max_f = 0
    for node in nodes:
        if node.get("parent_local_id") != parent_local_id:
            continue
        m = FOLLOWUP_ID.match(node["local_id"])
        if m and m.group(1) == stem:
            max_f = max(max_f, int(m.group(2)))
    return "I%s.F%d" % (stem, max_f + 1)


def resolve_default_parent(nodes):
    """The default-parent rule: the Sub-Epic of the single doing Issue, else None (ask)."""
    doing = [n for n in nodes
             if n.get("level") == "issue" and n.get("impl", {}).get("status") == "doing"]
    if len(doing) != 1:
        return None
    return doing[0].get("parent_local_id")


def check(name, cond, detail=""):
    global FAILURES
    status = "ok" if cond else "FAIL"
    print("  [%s] %s%s" % (status, name, (" — " + detail) if (detail and not cond) else ""))
    if not cond:
        FAILURES += 1


FAILURES = 0


def run(manifest):
    nodes = manifest["nodes"] if isinstance(manifest, dict) else manifest
    ids = [n["local_id"] for n in nodes]

    print("ID namespaces")
    for i in ids:
        check("'%s' matches exactly one namespace" % i,
              bool(FOLLOWUP_ID.match(i)) != bool(POSITIONAL_ID.match(i)),
              "an ID must be positional XOR follow-up")
    check("no duplicate local IDs", len(ids) == len(set(ids)))

    print("Allocation")
    new_id = allocate_followup_id(nodes, "SE1.2") if "SE1.2" in ids else None
    if new_id is not None:
        check("next ID under SE1.2 is I1.2.F2 (max F + 1)", new_id == "I1.2.F2", new_id)
        check("allocated ID is unused", new_id not in ids)
        check("allocated ID never collides with a positional ID",
              not POSITIONAL_ID.match(new_id))
    if "E1" in ids:
        epic_id = allocate_followup_id(nodes, "E1")
        check("Epic-direct allocation under E1 yields I1.F1", epic_id == "I1.F1", epic_id)
        check("Epic-direct ID is unused", epic_id not in ids)

    print("Node shape")
    for n in nodes:
        i = n["local_id"]
        missing = NODE_FIELDS - set(n)
        check("'%s' carries the export-backlog fields" % i, not missing, str(missing))
        if FOLLOWUP_ID.match(i):
            origin = n.get("origin")
            check("'%s' has origin" % i, isinstance(origin, dict))
            if isinstance(origin, dict):
                check("'%s' origin.source is valid" % i,
                      origin.get("source") in ORIGIN_SOURCES, str(origin.get("source")))
                check("'%s' origin has discovered_in + reference + queued_at" % i,
                      {"discovered_in", "reference", "queued_at"} <= set(origin))
            check("'%s' seeded with followup + status::todo labels" % i,
                  "followup" in n["labels"] and
                  any(l in ("status::todo", "status:todo") for l in n["labels"]))
            check("'%s' parent exists in the manifest" % i,
                  n["parent_local_id"] in ids)
        else:
            check("'%s' (positional) carries no origin" % i, "origin" not in n)

    print("Parent resolution")
    parent = resolve_default_parent(nodes)
    if any(n.get("impl", {}).get("status") == "doing" for n in nodes):
        check("single doing Issue resolves to its Sub-Epic", parent == "SE1.2", str(parent))
    two_doing = [dict(n) for n in nodes]
    for n in two_doing:
        if n["level"] == "issue" and FOLLOWUP_ID.match(n["local_id"]) is None:
            n["impl"] = {"status": "doing"}
    check("multiple doing Issues resolve to None (ask the user)",
          resolve_default_parent(two_doing) is None)
    none_doing = [{k: v for k, v in n.items() if k != "impl"} for n in nodes]
    check("zero doing Issues resolve to None (ask the user)",
          resolve_default_parent(none_doing) is None)


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            manifest = json.load(f)
        print("checking %s" % sys.argv[1])
    else:
        manifest = FIXTURE
        print("checking embedded fixture")
    run(manifest)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
