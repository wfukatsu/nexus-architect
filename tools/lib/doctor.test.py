#!/usr/bin/env python3
"""Contract test for tools/lib/doctor.py — the install and project health check.

Usage: python3 tools/lib/doctor.test.py     (exit 1 on failure)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import doctor as Dr  # noqa: E402

FAILURES = 0


def check(name, cond, detail=""):
    global FAILURES
    print("  [%s] %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond or not detail else " -- %r" % (detail,)))
    if not cond:
        FAILURES += 1


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def by_check(findings):
    return {f["check"]: f for f in findings}


def main():
    root = tempfile.mkdtemp(prefix="nx-doctor-")
    try:
        print("this repository")
        repo, version = Dr.check_repository(ROOT)
        r = by_check(repo)
        check("the repository passes its own checks", all(f["status"] == "ok" for f in repo), repo)
        check("the version is read from the marketplace", bool(version) and version[0].isdigit(), version)
        tools = by_check(Dr.check_tools())
        check("bash, git and python3 are required checks", all(tools[t]["status"] == "ok" for t in ("bash", "git", "python3")))
        check("the optional tools never FAIL", all(tools[t]["status"] in ("ok", "warn") for t in ("gh", "glab", "claude", "rtk")))

        print("a broken repository")
        fake = os.path.join(root, "repo")
        write(os.path.join(fake, ".claude-plugin", "marketplace.json"), json.dumps({"plugins": [
            {"name": "product", "version": "1.0.0", "skills": ["./skills/a"]},
            {"name": "architect", "version": "1.0.1", "skills": ["./skills/b"]},
            {"name": "scalardb", "version": "1.0.0", "skills": []},
        ]}))
        write(os.path.join(fake, "skills", "a", "SKILL.md"), "---\n---\n")
        write(os.path.join(fake, "hooks", "hooks.json"), json.dumps({"hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/missing.py"}]}]}}))
        repo, version = Dr.check_repository(fake)
        r = by_check(repo)
        check("a missing plugin, split versions, a skill without SKILL.md, a hook script that does not exist "
              "and no claim.sh are failures",
              r["four plugins registered"]["status"] == "FAIL" and r["one version across the plugins"]["status"] == "FAIL"
              and r["every registered skill has a SKILL.md"]["status"] == "FAIL"
              and r["hooks.json names scripts that exist"]["status"] == "FAIL"
              and r["hooks/claim.sh present (the once-per-tool-call guard)"]["status"] == "FAIL" and version is None, r)
        check("an unparseable marketplace is one failure, not a crash",
              Dr.check_repository(os.path.join(root, "nowhere"))[0][0]["status"] == "FAIL")

        print("installed plugins")
        home = os.path.join(root, "home")
        inst = by_check(Dr.check_install("0.60.0", home))
        check("no installed_plugins.json is a warning, not a failure",
              list(inst.values())[0]["status"] == "warn")
        write(os.path.join(home, ".claude", "plugins", "installed_plugins.json"), json.dumps({"plugins": {
            "architect@nexus-architect": [{"version": "0.59.0"}], "product@nexus-architect": [{"version": "0.60.0"}]}}))
        inst = by_check(Dr.check_install("0.60.0", home))
        check("an older installed version warns naming both versions; the matching one is ok; absent ones warn",
              inst["architect@nexus-architect"]["status"] == "warn" and "installed 0.59.0, repository 0.60.0" in inst["architect@nexus-architect"]["detail"]
              and inst["product@nexus-architect"]["status"] == "ok"
              and inst["infra@nexus-architect"]["status"] == "warn", inst)

        print("bundles")
        bundles = by_check(Dr.check_bundles(ROOT, today=date(2026, 1, 1)))
        check("this repository's bundles are populated and, as of 2026-01-01, none is stale",
              bundles["ScalarDB/ScalarDL bundle populated"]["status"] == "ok"
              and bundles["no bundle document past its stale_after"]["status"] == "ok", bundles)
        stale = by_check(Dr.check_bundles(ROOT, today=date(2099, 1, 1)))
        check("a date past every stale_after is a warning naming revise-knowledge",
              stale["no bundle document past its stale_after"]["status"] == "warn"
              and "revise-knowledge" in stale["no bundle document past its stale_after"]["detail"])
        empty = by_check(Dr.check_bundles(fake))
        check("an empty ScalarDB bundle and a missing k8s-tf bundle fail",
              empty["ScalarDB/ScalarDL bundle populated"]["status"] == "FAIL"
              and empty["Kubernetes/Terraform bundle present"]["status"] == "FAIL")

        print("a project")
        proj = os.path.join(root, "proj")
        write(os.path.join(proj, "work", "pipeline-progress.json"), json.dumps({
            "options": {"profile": "poc", "depth": "odd"},
            "phases": {"investigate": {"status": "completed"}, "analyze": {"status": "awaiting_approval"},
                       "x": {"status": "weird"}}}))
        write(os.path.join(proj, "work", "context.md"),
              "## Open Questions\n\n| ID | Question | Status | Answer | Options offered | Owner | Impact | Asked at | Role |\n"
              "|---|---|---|---|---|---|---|---|---|\n| OQ-001 | a? | unasked | | | | | | |\n")
        write(os.path.join(proj, "work", "audit", "events.jsonl"), '{"event": "PHASE_STARTED"}\n{bad\n')
        write(os.path.join(proj, "work", "learned-rules.json"), json.dumps({"schema_version": 1, "rules": [{"id": "LR-001"}]}))
        write(os.path.join(proj, "reports", "backlog", "claims.json"), "{\"claims\": 3}")
        p = by_check(Dr.check_project(proj))
        check("a bad depth warns, an unknown status warns, awaiting phases are listed, the store reads, "
              "a malformed audit line warns, the rules parse and a broken claims file fails",
              p["profile and depth are manifest names"]["status"] == "warn"
              and p["every phase status is a known value"]["status"] == "warn"
              and "analyze" in p["phases awaiting approval"]["detail"]
              and p["Open Questions store headed ID"]["detail"] == "1 rows, 1 unasked"
              and p["audit log parses"]["status"] == "warn" and "1 malformed" in p["audit log parses"]["detail"]
              and p["learned rules store parses"]["status"] == "ok"
              and p["claims store parses"]["status"] == "FAIL", p)
        check("a project without a registry is one failure",
              Dr.check_project(os.path.join(root, "none"))[0]["status"] == "FAIL")
        report = Dr.run(proj, home=home, today=date(2026, 1, 1))
        check("run counts failures and warnings and the text names every section",
              report["failures"] >= 1 and report["warnings"] >= 2
              and all(s in Dr.render_text(report) for s in ("[repository]", "[tools]", "[install]", "[bundles]", "[project]")),
              Dr.render_text(report))

        print("command line")
        r = subprocess.run([sys.executable, os.path.join(HERE, "doctor.py"), proj, "format=json"],
                           capture_output=True, text=True)
        check("json output and exit 1 on a failing project",
              r.returncode == 1 and json.loads(r.stdout)["project"] == os.path.abspath(proj), r.stderr)
        r = subprocess.run(["bash", os.path.join(ROOT, "tools", "doctor.sh"), proj], capture_output=True, text=True)
        check("the shell wrapper runs it", r.returncode == 1 and "nexus-architect doctor" in r.stdout, r.stderr)
        check("usage errors exit 2",
              subprocess.run([sys.executable, os.path.join(HERE, "doctor.py"), "--json"], capture_output=True).returncode == 2
              and subprocess.run([sys.executable, os.path.join(HERE, "doctor.py"), proj, "format=xml"], capture_output=True).returncode == 2
              and subprocess.run([sys.executable, os.path.join(HERE, "doctor.py"), os.path.join(root, "nope")], capture_output=True).returncode == 2)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("%d failure(s)" % FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
