#!/usr/bin/env python3
"""Collect the public upstream of the k8s-tf OKF bundle and record what moved. No model involved.

Usage:
  tools/refresh-okf-k8s-tf.py [--apply-redirects] [--check] [--offline] [--no-pages]
                              [--now=ISO8601] [--github-output=PATH]

  (default)          fetch every public page the bundle cites and every release feed in
                     knowledge/okf-k8s-tf-upstream/sources.yaml; hold the page text locally under
                     knowledge/okf-k8s-tf-upstream/pages/ (git-ignored); rewrite state.json and
                     REPORT.md when anything moved, including the list of documents awaiting
                     re-verification
  --apply-redirects  also rewrite the frontmatter `resource` of every cited page that redirected
                     to its final URL, and note it in the bundle's log.md — the one bundle edit
                     that needs no judgement
  --check            fetch and report, write nothing (exit 3 when the recorded state is out of date)
  --offline          fetch nothing: recompute the pending list from the recorded state and the
                     bundle as it is now — run after re-verifying documents, so the ones just
                     re-verified leave the list
  --no-pages         do not write the local page text
  --now              timestamp to record (CI passes the run time; default: now, UTC)
  --github-output    append `changed=true|false` and `pending=<n>` for a workflow step

Revising a document's prose is not done here: that is judgement, and belongs to the
/architect:revise-knowledge skill, which reads the pending list this writes.

Exit: 0 ok, 1 too many sources unreachable (over half the pages — the network, not the docs),
      2 usage, 3 --check found the recorded state out of date.
"""

import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
import okf_upstream as up  # noqa: E402

ROOT = os.path.dirname(HERE)
BUNDLE = os.environ.get("NEXUS_OKF_K8S_TF") or os.path.join(ROOT, "knowledge", "okf-k8s-tf")
UPSTREAM = os.environ.get("NEXUS_OKF_K8S_TF_UPSTREAM") or os.path.join(ROOT, "knowledge", "okf-k8s-tf-upstream")


def main(argv):
    check = no_pages = redirects = offline = False
    now = gh_out = None
    for a in argv:
        if a == "--check":
            check = True
        elif a == "--no-pages":
            no_pages = True
        elif a == "--offline":
            offline = True
        elif a == "--apply-redirects":
            redirects = True
        elif a.startswith("--now="):
            now = a.split("=", 1)[1]
        elif a.startswith("--github-output="):
            gh_out = a.split("=", 1)[1]
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            print("unknown argument: %s" % a, file=sys.stderr)
            return 2
    if check and redirects:
        print("--check writes nothing; it cannot --apply-redirects", file=sys.stderr)
        return 2
    if offline and (check or redirects):
        print("--offline recomputes the pending list only; it takes no other mode", file=sys.stderr)
        return 2
    now = now or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    today = now[:10]

    state_path = os.path.join(UPSTREAM, "state.json")
    if offline:
        return recompute(state_path, today)
    feeds = up.load_feeds(os.path.join(UPSTREAM, "sources.yaml"))
    cited = up.page_sources(BUNDLE)
    pages_dir = None if (check or no_pages) else os.path.join(UPSTREAM, "pages")

    print("okf-upstream: checking %d pages and %d release feeds ..." % (len(cited), len(feeds)))
    pages, releases, errors = up.collect(BUNDLE, feeds, up.HttpFetcher(), now, pages_dir)
    unreachable = sum(e["kind"] == "page" for e in errors)
    for e in errors:
        print("    %s %s: %s" % (e["kind"], e["target"], e["error"]), file=sys.stderr)
    if unreachable * 2 > len(cited):
        print("okf-upstream: over half the pages unreachable — not recording", file=sys.stderr)
        return 1

    prev = up.load_state(state_path)
    state = up.merge(prev, pages, releases, errors, now, cited=set(cited))
    delta = up.diff(prev, state)
    applied = up.apply_redirects(BUNDLE, state) if redirects else []
    state["pending"] = up.pending_documents(BUNDLE, state, today)
    changed = not up.content_equal(prev, state)

    for key in ("changed", "moved", "added", "removed", "bumped"):
        if delta[key]:
            print("  %-8s %d" % (key, len(delta[key])))
    for rel, old, new in applied:
        print("  redirect %s: %s -> %s" % (rel, old, new))
    print("  errors   %d" % len(errors))
    print("okf-upstream: %s; %d document(s) awaiting re-verification"
          % ("state moved" if changed else "no change", len(state["pending"])))

    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write("changed=%s\npending=%d\n" % ("true" if changed else "false", len(state["pending"])))
    if check:
        return 3 if changed else 0
    # A quiet week writes nothing, so it produces no pull request. `pending` is part of the state,
    # so a document crossing its stale_after, or being re-verified, is a change like any other.
    if changed:
        up.log_redirects(BUNDLE, applied, today)
        os.makedirs(UPSTREAM, exist_ok=True)
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        with open(os.path.join(UPSTREAM, "REPORT.md"), "w", encoding="utf-8") as fh:
            fh.write(up.render_report(state, delta, errors, up.private_sources(BUNDLE), applied))
        print("okf-upstream: wrote state.json and REPORT.md")
    return 0


def recompute(state_path, today):
    prev = up.load_state(state_path)
    if not prev.get("pages"):
        print("okf-upstream: no recorded state to recompute from — run without --offline", file=sys.stderr)
        return 1
    state = json.loads(json.dumps(prev))
    state["pending"] = up.pending_documents(BUNDLE, state, today)
    delta = up.diff(state, state)
    print("okf-upstream: %d document(s) awaiting re-verification (offline recompute)" % len(state["pending"]))
    if state != prev:
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        with open(os.path.join(UPSTREAM, "REPORT.md"), "w", encoding="utf-8") as fh:
            fh.write(up.render_report(state, delta, [], up.private_sources(BUNDLE)))
        print("okf-upstream: wrote state.json and REPORT.md")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
