#!/usr/bin/env python3
"""The doctor: is this install of the toolkit healthy, and is this project readable?

    python3 tools/lib/doctor.py [project_dir] [format=text|json]

Checks, each `ok`, `warn` or `FAIL` with one line of detail:

  repository   marketplace.json parses, the four plugins share one version, every registered
               skill directory holds a SKILL.md, hooks.json parses and names scripts that exist
               and run, hooks/claim.sh is present
  tools        bash, git, python3 present; gh, glab, claude, rtk reported when absent (warn)
  install      the four plugins in ~/.claude/plugins/installed_plugins.json, their installed
               version against the repository's — a session serves the installed copy, so a
               newer checkout is a warning worth knowing
  bundles      knowledge/okf-scalardb-scalardl/okf populated (the submodule), knowledge/okf-k8s-tf
               present with its documents' stale_after dates not past
  project      (when a directory is given, or the current one holds work/pipeline-progress.json)
               the registry parses with object options and a known profile / depth, the Open
               Questions store is headed `ID`, the audit log, learned rules and claims parse,
               phases awaiting approval are listed

Exit 0 when nothing FAILed (warnings allowed), 1 otherwise, 2 on a usage error. Nothing is
written. Wrapped by tools/doctor.sh and /architect:doctor.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

PLUGINS = ("product", "architect", "scalardb", "infra")
REQUIRED_TOOLS = ("bash", "git", "python3")
OPTIONAL_TOOLS = ("gh", "glab", "claude", "rtk")


def finding(section, status, check, detail=""):
    return {"section": section, "status": status, "check": check, "detail": detail}


def _load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ----------------------------------------------------------------------------- repository
def check_repository(root):
    out = []
    path = os.path.join(root, ".claude-plugin", "marketplace.json")
    try:
        market = _load_json(path)
    except (OSError, ValueError) as exc:
        return [finding("repository", "FAIL", "marketplace.json", str(exc))], None
    plugins = {p.get("name"): p for p in market.get("plugins", []) if isinstance(p, dict)}
    missing = [p for p in PLUGINS if p not in plugins]
    out.append(finding("repository", "FAIL" if missing else "ok", "four plugins registered",
                       "missing %s" % missing if missing else ", ".join(PLUGINS)))
    versions = {plugins[p].get("version") for p in PLUGINS if p in plugins}
    out.append(finding("repository", "ok" if len(versions) == 1 else "FAIL", "one version across the plugins",
                       ", ".join(sorted(str(v) for v in versions))))
    absent = []
    for p in PLUGINS:
        for skill in plugins.get(p, {}).get("skills", []):
            if not os.path.isfile(os.path.join(root, skill, "SKILL.md")):
                absent.append(skill)
    out.append(finding("repository", "FAIL" if absent else "ok", "every registered skill has a SKILL.md",
                       "missing %s" % absent[:5] if absent else "%d skills" % sum(
                           len(plugins[p].get("skills", [])) for p in PLUGINS if p in plugins)))
    hooks_path = os.path.join(root, "hooks", "hooks.json")
    try:
        hooks = _load_json(hooks_path)
        scripts = set(re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/(hooks/[A-Za-z0-9_./-]+)", json.dumps(hooks)))
        bad = [s for s in scripts if not os.path.isfile(os.path.join(root, s))
               or not os.access(os.path.join(root, s), os.R_OK)]
        out.append(finding("repository", "FAIL" if bad else "ok", "hooks.json names scripts that exist",
                           "missing %s" % bad if bad else ", ".join(sorted(os.path.basename(s) for s in scripts))))
    except (OSError, ValueError) as exc:
        out.append(finding("repository", "FAIL", "hooks.json", str(exc)))
    out.append(finding("repository", "ok" if os.path.isfile(os.path.join(root, "hooks", "claim.sh")) else "FAIL",
                       "hooks/claim.sh present (the once-per-tool-call guard)"))
    return out, next(iter(versions)) if len(versions) == 1 else None


# ---------------------------------------------------------------------------------- tools
def check_tools():
    out = []
    for name in REQUIRED_TOOLS:
        out.append(finding("tools", "ok" if shutil.which(name) else "FAIL", name,
                           shutil.which(name) or "not on PATH"))
    if sys.version_info < (3, 8):
        out.append(finding("tools", "FAIL", "python3 >= 3.8", sys.version.split()[0]))
    for name in OPTIONAL_TOOLS:
        out.append(finding("tools", "ok" if shutil.which(name) else "warn", name,
                           shutil.which(name) or "not on PATH (optional: %s)" % {
                               "gh": "GitHub backlog delivery", "glab": "GitLab backlog delivery",
                               "claude": "evals and the dashboard's --exec", "rtk": "condensed command output"}[name]))
    return out


# -------------------------------------------------------------------------------- install
def check_install(repo_version, home=None):
    out = []
    home = home or os.path.expanduser("~")
    path = os.path.join(home, ".claude", "plugins", "installed_plugins.json")
    if not os.path.isfile(path):
        return [finding("install", "warn", "Claude Code plugins", "no %s — not installed as plugins "
                        "(Codex and Omnigent read the repository directly)" % path)]
    try:
        data = _load_json(path)
    except (OSError, ValueError) as exc:
        return [finding("install", "warn", "installed_plugins.json", str(exc))]
    entries = data.get("plugins", data) if isinstance(data, dict) else {}
    for p in PLUGINS:
        key = "%s@nexus-architect" % p
        value = entries.get(key) if isinstance(entries, dict) else None
        if not value:
            out.append(finding("install", "warn", key, "not installed"))
            continue
        records = value if isinstance(value, list) else [value]
        versions = sorted({str(r.get("version")) for r in records if isinstance(r, dict)})
        if repo_version and versions and versions != [str(repo_version)]:
            out.append(finding("install", "warn", key, "installed %s, repository %s — a session serves the "
                               "installed copy; update the plugin (or point a run at the checkout) before "
                               "expecting the newer skills" % (", ".join(versions), repo_version)))
        else:
            out.append(finding("install", "ok", key, "installed %s" % ", ".join(versions)))
    return out


# -------------------------------------------------------------------------------- bundles
def _stale_after_dates(bundle_dir):
    dates = []
    for path in glob.glob(os.path.join(bundle_dir, "**", "*.md"), recursive=True):
        try:
            with open(path, encoding="utf-8") as fh:
                head = fh.read(4000)
        except OSError:
            continue
        m = re.search(r"^\s*stale_after:\s*[\"']?(\d{4}-\d{2}-\d{2})", head, re.M)
        if m:
            try:
                dates.append((date.fromisoformat(m.group(1)), os.path.relpath(path, bundle_dir)))
            except ValueError:
                pass
    return dates


def check_bundles(root, today=None):
    out = []
    today = today or date.today()
    scalardb = os.path.join(root, "knowledge", "okf-scalardb-scalardl", "okf")
    populated = os.path.isdir(scalardb) and any(os.scandir(scalardb))
    out.append(finding("bundles", "ok" if populated else "FAIL", "ScalarDB/ScalarDL bundle populated",
                       scalardb if populated else "empty — run tools/update-okf-bundle.sh ensure (git submodule)"))
    k8s = os.path.join(root, "knowledge", "okf-k8s-tf")
    if not os.path.isdir(k8s):
        out.append(finding("bundles", "FAIL", "Kubernetes/Terraform bundle present", k8s))
        return out
    dates = _stale_after_dates(k8s)
    past = sorted(d for d in dates if d[0] < today)
    out.append(finding("bundles", "ok", "Kubernetes/Terraform bundle present", "%d documents dated" % len(dates)))
    out.append(finding("bundles", "warn" if past else "ok", "no bundle document past its stale_after",
                       ("%d past: %s — /architect:revise-knowledge" % (len(past), ", ".join(p for _, p in past[:3])))
                       if past else ("earliest %s" % min(d for d, _ in dates) if dates else "no dates")))
    return out


# -------------------------------------------------------------------------------- project
def check_project(project):
    out = []
    reg = os.path.join(project, "work", "pipeline-progress.json")
    try:
        progress = _load_json(reg)
    except (OSError, ValueError) as exc:
        return [finding("project", "FAIL", "work/pipeline-progress.json", str(exc))]
    options = progress.get("options") if isinstance(progress, dict) else None
    out.append(finding("project", "ok" if isinstance(options, dict) else "FAIL", "options is an object",
                       ", ".join("%s=%s" % kv for kv in sorted((options or {}).items())
                                 if isinstance(kv[1], (str, bool, int)))[:200] if isinstance(options, dict) else type(options).__name__))
    try:
        import pipeline_status_data as P
        _, _, _, _, warnings = P.resolve_profile("architect", options if isinstance(options, dict) else {})
        out.append(finding("project", "warn" if warnings else "ok", "profile and depth are manifest names",
                           "; ".join(warnings) if warnings else "%s / %s" % (
                               (options or {}).get("profile", "full"), (options or {}).get("depth", "default"))))
        phases = progress.get("phases") if isinstance(progress, dict) else None
        if isinstance(phases, dict):
            unknown = [n for n, e in phases.items()
                       if isinstance(e, dict) and e.get("status") not in P.PHASE_STATUSES]
            out.append(finding("project", "warn" if unknown else "ok", "every phase status is a known value",
                               "unknown on %s" % unknown[:5] if unknown else "%d phases" % len(phases)))
            awaiting = [n for n, e in phases.items() if isinstance(e, dict) and e.get("status") == "awaiting_approval"]
            if awaiting:
                out.append(finding("project", "warn", "phases awaiting approval",
                                   "%s — /architect:start asks again; tools/lib/open_questions.py by=role says whom" % awaiting))
    except Exception as exc:  # the dashboard module is optional here
        out.append(finding("project", "warn", "pipeline_status_data", "could not load: %s" % exc))
    try:
        import open_questions as Q
        rows, exists = Q.read_store(project)
        if not exists:
            out.append(finding("project", "warn", "work/context.md", "absent — no Open Questions store yet"))
        else:
            text = open(os.path.join(project, "work", "context.md"), encoding="utf-8").read()
            headed = bool(re.search(r"^\|\s*(ID|OQ-###)\s*\|", text, re.M))
            unasked = sum(1 for r in rows if r["status_word"] == "unasked")
            out.append(finding("project", "ok" if headed or not rows else "warn", "Open Questions store headed ID",
                               "%d rows, %d unasked" % (len(rows), unasked) if headed else "table not headed ID / OQ-###"))
    except Exception as exc:
        out.append(finding("project", "warn", "open_questions", str(exc)))
    audit = os.path.join(project, "work", "audit", "events.jsonl")
    if os.path.isfile(audit):
        bad = total = 0
        with open(audit, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                total += 1
                try:
                    json.loads(line)
                except ValueError:
                    bad += 1
        out.append(finding("project", "warn" if bad else "ok", "audit log parses",
                           "%d events%s" % (total, (", %d malformed lines" % bad) if bad else "")))
    for label, rel, loader in (("learned rules", os.path.join("work", "learned-rules.json"), "learned_rules"),
                               ("claims", os.path.join("reports", "backlog", "claims.json"), "backlog_claims")):
        path = os.path.join(project, rel)
        if not os.path.isfile(path):
            continue
        try:
            module = __import__(loader)
            data = module.load(path) if loader == "learned_rules" else module.load(project)
            count = len(data.get("rules", data.get("claims", [])))
            out.append(finding("project", "ok", "%s store parses" % label, "%d entries" % count))
        except Exception as exc:
            out.append(finding("project", "FAIL", "%s store parses" % label, str(exc)))
    return out


def run(project=None, root=ROOT, home=None, today=None):
    findings = []
    repo, version = check_repository(root)
    findings += repo
    findings += check_tools()
    findings += check_install(version, home)
    findings += check_bundles(root, today)
    if project is None and os.path.isfile(os.path.join(os.getcwd(), "work", "pipeline-progress.json")):
        project = os.getcwd()
    if project is not None:
        findings += check_project(project)
    return {"root": root, "version": version, "project": os.path.abspath(project) if project else None,
            "findings": findings,
            "failures": sum(1 for f in findings if f["status"] == "FAIL"),
            "warnings": sum(1 for f in findings if f["status"] == "warn")}


def render_text(report):
    lines = ["nexus-architect doctor — %s (%s)" % (report["root"], report["version"] or "version unknown")]
    section = None
    for f in report["findings"]:
        if f["section"] != section:
            section = f["section"]
            lines.append("[%s]" % section)
        lines.append("  %-4s %s%s" % (f["status"], f["check"], (" — " + f["detail"]) if f["detail"] else ""))
    lines.append("%d failure(s), %d warning(s)" % (report["failures"], report["warnings"]))
    return "\n".join(lines)


def main(argv):
    project, fmt = None, "text"
    for arg in argv:
        if arg.startswith("format="):
            fmt = arg.split("=", 1)[1]
        elif arg.startswith("-"):
            sys.stderr.write(__doc__)
            return 2
        elif project is None:
            project = arg
        else:
            sys.stderr.write("doctor: one project directory at most\n")
            return 2
    if project is not None and not os.path.isdir(project):
        sys.stderr.write("doctor: not a directory: %s\n" % project)
        return 2
    if fmt not in ("text", "json"):
        sys.stderr.write("doctor: format must be text or json\n")
        return 2
    report = run(project)
    sys.stdout.write((json.dumps(report, ensure_ascii=False, indent=2) if fmt == "json"
                      else render_text(report)) + "\n")
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
