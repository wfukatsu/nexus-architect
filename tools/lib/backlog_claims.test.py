#!/usr/bin/env python3
"""Contract test for tools/lib/backlog_claims.py — claims and per-Issue worktrees.

Usage: python3 tools/lib/backlog_claims.test.py     (exit 1 on failure)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backlog_claims as C  # noqa: E402
import audit_log as A  # noqa: E402

FAILURES = 0


def check(name, cond, detail=""):
    global FAILURES
    print("  [%s] %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond or not detail else " -- %r" % (detail,)))
    if not cond:
        FAILURES += 1


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)


def cli(project, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, "backlog_claims.py"), project] + list(args),
                          capture_output=True, text=True)


def main():
    root = tempfile.mkdtemp(prefix="nx-claims-")
    try:
        repo = os.path.join(root, "proj")
        os.makedirs(repo)
        subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True)
        git(repo, "config", "user.name", "Alice Dev")
        git(repo, "config", "user.email", "a@example.invalid")
        with open(os.path.join(repo, "README.md"), "w") as fh:
            fh.write("x\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "init")

        print("claims")
        rec, created = C.claim(repo, "I1.2.3", branch="feat/I1.2.3")
        check("a claim records who (git user.name), when and the branch, under reports/backlog/claims.json",
              created and rec["claimed_by"] == "Alice Dev" and rec["branch"] == "feat/I1.2.3"
              and os.path.isfile(os.path.join(repo, "reports", "backlog", "claims.json")), rec)
        rec2, created = C.claim(repo, "I1.2.3", worktree="/tmp/x")
        check("the same person again refreshes the claim instead of adding one",
              not created and rec2["worktree"] == "/tmp/x" and len(C.listing(repo)) == 1)
        try:
            C.claim(repo, "I1.2.3", by="Bob Dev")
            check("another person is refused", False)
        except C.Contested as exc:
            check("another person is refused, and told who holds it", exc.holder["claimed_by"] == "Alice Dev")
        rec3, created = C.claim(repo, "I1.2.3", by="Bob Dev", steal=True)
        all_claims = C.listing(repo, only_active=False)
        check("steal=true takes it, releasing the old claim as stolen and recording the previous holder",
              created and rec3["claimed_by"] == "Bob Dev" and rec3["stolen_from"] == "Alice Dev"
              and all_claims[0]["reason"] == "stolen" and all_claims[0]["released_by"] == "Bob Dev"
              and len(C.listing(repo)) == 1, all_claims)
        C.claim(repo, "I1.2.4", by="Alice Dev", integration="integration/E1")
        released = C.release(repo, "I1.2.4", by="Alice Dev", reason="merged")
        check("release closes the active claim with a reason", released["released_at"] and released["reason"] == "merged"
              and [c["item"] for c in C.listing(repo)] == ["I1.2.3"])
        try:
            C.release(repo, "I1.2.4")
            check("releasing an item with no active claim is refused", False)
        except KeyError:
            check("releasing an item with no active claim is refused", True)
        try:
            C.claim(repo, "../etc")
            check("an item id that is not an id is refused", False)
        except ValueError:
            check("an item id that is not an id is refused", True)
        events = [(e["event"], e["phase"], e["actor"]) for e in A.read_events(repo)]
        check("claims and releases are audit events",
              events == [("ITEM_CLAIMED", "I1.2.3", "Alice Dev"), ("ITEM_CLAIMED", "I1.2.3", "Bob Dev"),
                         ("ITEM_CLAIMED", "I1.2.4", "Alice Dev"), ("ITEM_RELEASED", "I1.2.4", "Alice Dev")], events)
        check("the text listing shows the integration branch and state",
              "I1.2.3" in C.render_text(C.listing(repo)) and "-> integration/E1" in C.render_text(C.listing(repo, False)))

        print("worktrees")
        wt = C.worktree_add(repo, "I1.2.3")
        check("a worktree is created under ../<project>-worktrees/<item> on feat/<item> from the current branch",
              os.path.realpath(wt["worktree"]) == os.path.realpath(os.path.join(root, "proj-worktrees", "I1.2.3"))
              and wt["branch"] == "feat/I1.2.3"
              and wt["base"] == "main" and os.path.isfile(os.path.join(wt["worktree"], "README.md")), wt)
        check("the claim records the worktree and branch",
              C.listing(repo)[0]["worktree"] == wt["worktree"] and C.listing(repo)[0]["branch"] == "feat/I1.2.3")
        check("git knows the worktree", wt["worktree"] in git(repo, "worktree", "list").stdout)
        with open(os.path.join(wt["worktree"], "f.txt"), "w") as fh:
            fh.write("w\n")
        git(wt["worktree"], "add", "-A")
        git(wt["worktree"], "commit", "-qm", "work")
        removed = C.worktree_remove(repo, "I1.2.3")
        check("remove deletes the worktree directory but keeps the branch and its commit",
              removed["removed"] and not os.path.exists(wt["worktree"])
              and git(repo, "show-ref", "--verify", "--quiet", "refs/heads/feat/I1.2.3").returncode == 0)
        wt2 = C.worktree_add(repo, "I1.2.3", root=os.path.join(root, "custom"))
        check("an existing branch is checked out rather than recreated, under a custom root",
              os.path.realpath(wt2["worktree"]) == os.path.realpath(os.path.join(root, "custom", "I1.2.3"))
              and os.path.isfile(os.path.join(wt2["worktree"], "f.txt")))
        wt3 = C.worktree_add(repo, "#42", root=os.path.join(root, "custom"), base="main")
        check("a #iid item gets a filesystem-safe directory and branch",
              wt3["worktree"].endswith("issue-42") and wt3["branch"] == "feat/issue-42")
        try:
            C.worktree_add(os.path.join(root, "notrepo"), "I1")
            check("a non-repository is an error", False)
        except OSError:
            check("a non-repository is an error", True)

        print("command line")
        r = cli(repo, "claim", "I2.1", "by=Carol", "branch=feat/I2.1", "integration=integration/E2")
        check("claim prints the holder", r.returncode == 0 and json.loads(r.stdout)["claimed_by"] == "Carol", r.stderr)
        r = cli(repo, "claim", "I2.1", "by=Dave")
        check("a contested claim exits 3 naming the holder", r.returncode == 3 and "held by Carol" in r.stderr, r.stderr)
        r = cli(repo, "list", "format=json")
        check("list json shows the active claims", r.returncode == 0
              and sorted(c["item"] for c in json.loads(r.stdout)) == ["I1.2.3", "I2.1"], r.stdout)
        r = cli(repo, "release", "I2.1", "by=Carol", "reason=done")
        check("release prints the reason", r.returncode == 0 and json.loads(r.stdout)["reason"] == "done")
        r = cli(repo, "worktree", "add", "I3.1", "root=" + os.path.join(root, "custom"))
        check("worktree add prints the path and branch", r.returncode == 0 and json.loads(r.stdout)["branch"] == "feat/I3.1", r.stderr)
        check("worktree remove on an item without one exits 2", cli(repo, "worktree", "remove", "I9").returncode == 2)
        check("usage errors exit 2", cli(repo, "claim").returncode == 2 and cli(repo, "fold").returncode == 2
              and cli(repo, "claim", "I1", "--by=x").returncode == 2 and cli(repo, "worktree", "grow", "I1").returncode == 2
              and subprocess.run([sys.executable, os.path.join(HERE, "backlog_claims.py")], capture_output=True).returncode == 2)
        check("a non-repository exits 1 on worktree add",
              cli(os.path.join(root), "worktree", "add", "I1").returncode == 1)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
