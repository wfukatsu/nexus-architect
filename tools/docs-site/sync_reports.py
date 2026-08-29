#!/usr/bin/env python3
"""Stage a nexus-architect project's reports/ tree as a Blume documentation site.

Blume (https://useblume.dev) turns a folder of Markdown/MDX into a docs site, but it reads a
docs/ folder of its own and renders Mermaid only inside .mdx pages. This script is the bridge:

    reports/**/*.md            -> docs/**/*.mdx   (frontmatter adapted, MDX-unsafe text escaped,
                                                   links rewritten to site routes)
    reports/**/*.json          -> docs/**/*.mdx   (rendered as a code page)
    reports/**/openapi/*.yaml  -> specs/openapi/  (Blume's OpenAPI reference, /api)
    reports/**/asyncapi/*.yaml -> specs/asyncapi/ (Blume's AsyncAPI reference, /events)
    reports/00_summary/*.html  -> public/         (served as-is)
    work/pipeline-progress.json -> docs/index.mdx (the landing page: phases, status, outputs)

Numeric phase prefixes are stripped from path segments (01_analysis -> /analysis), so every
route is predictable and cross-report links can be rewritten to it. Nothing in reports/ is
modified; docs/, public/ and specs/ are wiped and rebuilt on every run.

Usage:
    sync_reports.py [PROJECT_DIR] [--watch[=SEC]]

PROJECT_DIR defaults to the current directory; it must contain reports/. Exit 0 when the
site was staged, 1 when the project has no reports/ or a report could not be converted.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "docs"
PUBLIC = HERE / "public"
SPECS = HERE / "specs"

# Sidebar order and label of the top-level report directories. Anything else reports/
# grows later still appears, after these, under its humanized name.
GROUPS = [
    ("00_summary", "Summary"),
    ("00_requirements", "00 Requirements"),
    ("before", "Before (as-is)"),
    ("01_analysis", "01 Analysis"),
    ("02_evaluation", "02 Evaluation"),
    ("03_design", "03 Design"),
    ("04_stories", "04 Domain Stories"),
    ("05_adaptation", "05 Adaptation"),
    ("08_infrastructure", "08 Infrastructure"),
    ("review", "Review"),
    ("backlog", "Backlog"),
]

# Labels for the nested directories the pipeline writes (defaults would be "Adr").
SUBGROUPS = {
    "adr": "ADR",
    "aggregates": "Aggregates",
    "state-machines": "State Machines",
    "api-specifications": "API Specifications",
    "examples": "Example Maps",
    "individual": "Individual Reviews",
}

STATUS_MARK = {
    "completed": "✅",
    "in_progress": "🔄",
    "pending": "⬜",
    "failed": "❌",
    "skipped": "⏭️",
}

# ----------------------------------------------------------------------------- paths


def slug_segment(segment: str) -> str:
    """01_analysis -> analysis; adr-001-foo.md keeps its name (no leading digits+_)."""
    return re.sub(r"^\d+_", "", segment)


def route_for(rel: Path) -> str:
    """Site route of a report path relative to reports/ (extension dropped)."""
    parts = [slug_segment(p) for p in rel.with_suffix("").parts]
    if parts and parts[-1] == "index":
        parts = parts[:-1]
    return "/" + "/".join(parts)


def docs_path_for(rel: Path) -> Path:
    parts = [slug_segment(p) for p in rel.parts]
    return DOCS.joinpath(*parts).with_suffix(".mdx")


# ------------------------------------------------------------------ frontmatter


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (raw frontmatter block without fences, body)."""
    if not text.startswith("---"):
        return "", text
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", text, re.S)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def scalar(fm: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}:[ \t]*(.+?)[ \t]*$", fm, re.M)
    if not m:
        return None
    v = m.group(1).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v


def list_items(fm: str, key: str) -> list[str]:
    """Values of a YAML list key, in either block (- x) or flow ([x, y]) form."""
    m = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", fm, re.M)
    if not m:
        return []
    inline = m.group(1).strip()
    if inline.startswith("["):
        inner = inline.strip("[]").strip()
        return [x.strip().strip("\"'") for x in inner.split(",") if x.strip()]
    items = []
    for line in fm[m.end():].splitlines():
        if re.match(r"^\s+-\s*", line):
            items.append(re.sub(r"^\s+-\s*", "", line).strip().strip("\"'"))
        elif line.strip() and not line.startswith(" "):
            break
    return items


# ------------------------------------------------------------------- MDX escaping

FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})")


def escape_segment(seg: str) -> str:
    """Make a run of plain Markdown safe for MDX: braces are expressions, `<` opens JSX."""
    seg = seg.replace("{", "\\{").replace("}", "\\}")
    seg = re.sub(r"<br\s*/?>", "<br />", seg, flags=re.I)
    # any other '<' followed by something that MDX would try to parse as a tag
    seg = re.sub(r"<(?!br />)(?=\S)", "&lt;", seg)
    return seg


def escape_line(line: str) -> str:
    """Escape outside inline code spans; a code span is a backtick run and its twin."""
    out, i, n = [], 0, len(line)
    while i < n:
        if line[i] == "`":
            j = i
            while j < n and line[j] == "`":
                j += 1
            ticks = line[i:j]
            close = line.find(ticks, j)
            if close == -1:
                out.append(escape_segment(line[i:]))
                break
            out.append(line[i:close + len(ticks)])
            i = close + len(ticks)
        else:
            k = line.find("`", i)
            if k == -1:
                k = n
            out.append(escape_segment(line[i:k]))
            i = k
    return "".join(out)


LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\))")


class LinkRewriter:
    def __init__(self, reports: Path, rel: Path, known_routes: dict[str, str]):
        self.reports = reports
        self.project = reports.parent
        self.rel = rel
        self.known = known_routes  # reports-relative posix path -> route

    def __call__(self, m: re.Match) -> str:
        head, target, tail = m.groups()
        if head.startswith("!"):
            return m.group(0)
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith(("#", "/")):
            return m.group(0)
        path, _, anchor = target.partition("#")
        if not path:
            return m.group(0)
        # Reports cite project files as project-root paths (`samples/…/Order.java`,
        # `work/context.md`). The site cannot serve those, so they become plain text.
        if not path.startswith("reports/") and (
                path.split("/", 1)[0] in ("work", "generated", "samples", "src")
                or (self.project / path).exists()):
            text = head[1:-2]
            return f"`{path}`" if text == path else f"{text} (`{path}`)"
        if path.startswith("reports/"):
            resolved = Path(path[len("reports/"):])
        else:
            resolved = Path(os.path.normpath((self.rel.parent / path).as_posix()))
        key = resolved.as_posix().rstrip("/")
        route = self.known.get(key)
        if route is None and key.endswith(".md"):
            route = route_for(resolved)  # a report that does not exist (yet): keep it a route
        if route is None:
            return m.group(0)
        if anchor:
            route += "#" + anchor
        return f"{head}{route}{tail}"


def convert_body(body: str, rewrite: LinkRewriter) -> str:
    out, fence = [], None
    for line in body.splitlines():
        m = FENCE_RE.match(line)
        if fence is None and m:
            fence = m.group(2)
            out.append(line)
            continue
        if fence is not None:
            out.append(line)
            if m and m.group(2)[0] == fence[0] and len(m.group(2)) >= len(fence) \
                    and line.strip() == m.group(2):
                fence = None
            continue
        line = LINK_RE.sub(rewrite, line)
        out.append(escape_line(line))
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------- page writers


def yaml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def write_page(dest: Path, title: str, description: str, body: str,
               nexus_fm: str = "", order: int | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fm = ["---", f"title: {yaml_str(title)}", f"description: {yaml_str(description)}"]
    if order is not None:
        fm += ["sidebar:", f"  order: {order}"]
    if nexus_fm.strip():
        fm.append("nexus:")
        fm += ["  " + l for l in nexus_fm.splitlines()]
    fm.append("---")
    dest.write_text("\n".join(fm) + "\n\n" + body, encoding="utf-8")


def provenance_block(fm: str, rewrite: LinkRewriter) -> str:
    """A short line under the title carrying the report's own metadata."""
    bits = []
    for key in ("id", "status", "skill", "phase", "mode", "aggregate", "domain",
                "generated_at", "decided_at"):
        v = scalar(fm, key)
        if v:
            bits.append(f"**{key}** `{v}`")
    lines = []
    if bits:
        lines.append("> " + " · ".join(bits))
    inputs = list_items(fm, "input_files") + [u for u in list_items(fm, "upstream")
                                              if u.startswith("reports/")]
    if inputs:
        links = ", ".join(LINK_RE.sub(rewrite, f"[{Path(p).name}]({p})")
                          if p.startswith("reports/") else f"`{p}`" for p in inputs)
        lines.append(f"> **inputs** {links}")
    return ("\n".join(lines) + "\n\n") if lines else ""


def convert_markdown(reports: Path, rel: Path, known: dict[str, str],
                     order: int | None) -> None:
    text = (reports / rel).read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    title = scalar(fm, "title") or rel.stem
    desc_bits = [b for b in (scalar(fm, "phase"), scalar(fm, "skill")) if b]
    if scalar(fm, "id"):
        desc_bits.insert(0, scalar(fm, "id"))
    description = " · ".join(desc_bits) or rel.as_posix()
    rewrite = LinkRewriter(reports, rel, known)
    body = provenance_block(fm, rewrite) + convert_body(body, rewrite)
    write_page(docs_path_for(rel), title, description, body, nexus_fm=fm, order=order)


def convert_code(reports: Path, rel: Path, lang: str) -> None:
    text = (reports / rel).read_text(encoding="utf-8")
    fence = "````" if "```" in text else "```"
    body = f"{fence}{lang} title={yaml_str(rel.name)}\n{text.rstrip()}\n{fence}\n"
    write_page(docs_path_for(rel), rel.name, rel.as_posix(), body)


def write_meta(dirpath: Path, title: str, order: int) -> None:
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / "meta.ts").write_text(
        'import { defineMeta } from "blume";\n\n'
        f"export default defineMeta({{ title: {json.dumps(title, ensure_ascii=False)}, "
        f"order: {order}, collapsed: true }});\n",
        encoding="utf-8",
    )


# ------------------------------------------------------------------ landing page


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def landing_page(project: Path, known: dict[str, str], html_reports: list[str],
                 manifest: dict) -> str:
    progress = load_json(project / "work" / "pipeline-progress.json")
    name = progress.get("project_name") or project.name
    opts = progress.get("options", {})
    lines = [f"Generated by the nexus-architect pipeline for **{name}**"
             + (f" (`{project}`)" if project else "") + ".", ""]
    if opts:
        lines.append("| option | value |")
        lines.append("|---|---|")
        for k, v in opts.items():
            lines.append(f"| `{k}` | `{json.dumps(v, ensure_ascii=False)}` |")
        lines.append("")
    if html_reports or manifest["openapi"] or manifest["asyncapi"]:
        lines.append("## Consolidated report and API references")
        lines.append("")
        for h in html_reports:
            lines.append(f"- [{h}](/{h}) — the consolidated HTML report, served as-is")
        if manifest["openapi"]:
            lines.append("- OpenAPI reference — "
                         + ", ".join(f"[{s['label']}]({s['route']})" for s in manifest["openapi"]))
        if manifest["asyncapi"]:
            lines.append("- AsyncAPI reference — "
                         + ", ".join(f"[{s['label']}]({s['route']})" for s in manifest["asyncapi"]))
        lines.append("")
    phases = progress.get("phases", {})
    if phases:
        lines.append("## Pipeline phases")
        lines.append("")
        lines.append("| phase | plugin | status | outputs |")
        lines.append("|---|---|---|---|")
        for phase, entry in phases.items():
            status = entry.get("status", "pending")
            outs = []
            for o in entry.get("outputs") or []:
                key = o[len("reports/"):] if o.startswith("reports/") else o
                key = key.rstrip("/")
                if key in known:
                    outs.append(f"[{Path(key).name}]({known[key]})")
            lines.append(f"| `{phase}` | {entry.get('plugin', '')} | "
                         f"{STATUS_MARK.get(status, '')} {status} | {', '.join(outs)} |")
        lines.append("")
    lines.append("## Report directories")
    lines.append("")
    labels = dict(GROUPS)
    tops = sorted({k.split("/")[0] for k in known if "/" in k},
                  key=lambda t: ([g for g, _ in GROUPS].index(t) if t in labels else len(GROUPS), t))
    for top in tops:
        pages = sorted((r, k) for k, r in known.items()
                       if k.startswith(top + "/") and Path(k).suffix in (".md", ".json"))
        if not pages:
            continue
        lines.append(f"- **{labels.get(top, top)}** — {len(pages)} pages, "
                     f"starting at [{Path(pages[0][1]).name}]({pages[0][0]})")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------- sync


def sync(project: Path) -> int:
    reports = project / "reports"
    if not reports.is_dir():
        print(f"sync_reports: {project} has no reports/ directory", file=sys.stderr)
        return 1

    for d in (DOCS, PUBLIC, SPECS):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)

    files = sorted(p.relative_to(reports) for p in reports.rglob("*")
                   if p.is_file() and not p.name.startswith("."))

    manifest = {"project": load_json(project / "work" / "pipeline-progress.json")
                .get("project_name") or project.name, "openapi": [], "asyncapi": []}
    html_reports: list[str] = []
    known: dict[str, str] = {}

    # first pass: decide every route so links can be rewritten in one go
    for rel in files:
        key = rel.as_posix()
        suffix = rel.suffix.lower()
        parts = rel.parts
        if suffix in (".md", ".json"):
            known[key] = route_for(rel)
        elif suffix in (".yaml", ".yml") and "openapi" in parts:
            known[key] = f"/api/{rel.stem}"
        elif suffix in (".yaml", ".yml") and "asyncapi" in parts:
            known[key] = f"/events/{rel.stem}"
        elif suffix == ".html":
            known[key] = f"/{rel.name}"
    # directories are linkable too (`reports/03_design/adr/`): their index page when there
    # is one, otherwise the first page inside them
    for key in sorted(known):
        parent = Path(key).parent
        while parent.as_posix() not in ("", "."):
            index = parent.as_posix() + "/index.md"
            known.setdefault(parent.as_posix(), known[index] if index in known else known[key])
            parent = parent.parent

    # sidebar order within a directory: the manifest's declaration order, then name
    order_of: dict[str, int] = {}
    manifest_yaml = HERE.parent.parent / "skills" / "common" / "skill-dependencies.yaml"
    if manifest_yaml.exists():
        for i, m in enumerate(re.finditer(r"^\s+-\s+reports/(\S+)", manifest_yaml.read_text(), re.M)):
            order_of.setdefault(m.group(1), i)

    errors = 0
    for rel in files:
        key = rel.as_posix()
        suffix = rel.suffix.lower()
        try:
            if suffix == ".md":
                convert_markdown(reports, rel, known, order_of.get(key))
            elif suffix == ".json":
                convert_code(reports, rel, "json")
            elif suffix in (".yaml", ".yml") and ("openapi" in rel.parts or "asyncapi" in rel.parts):
                kind = "openapi" if "openapi" in rel.parts else "asyncapi"
                dest = SPECS / kind / rel.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(reports / rel, dest)
                manifest[kind].append({"spec": f"./specs/{kind}/{rel.name}",
                                       "label": rel.stem, "route": f"/{'api' if kind == 'openapi' else 'events'}/{rel.stem}"})
            elif suffix in (".yaml", ".yml"):
                convert_code(reports, rel, "yaml")
            elif suffix == ".html":
                shutil.copy2(reports / rel, PUBLIC / rel.name)
                html_reports.append(rel.name)
            else:
                dest = PUBLIC / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(reports / rel, dest)
        except Exception as exc:  # report and keep going: one bad page must not hide the rest
            errors += 1
            print(f"sync_reports: failed to convert {key}: {exc}", file=sys.stderr)

    # sidebar groups
    present = {rel.parts[0] for rel in files if len(rel.parts) > 1}
    for i, (key, label) in enumerate(GROUPS):
        if key in present:
            write_meta(DOCS / slug_segment(key), label, i)
    for i, top in enumerate(sorted(present - {k for k, _ in GROUPS})):
        write_meta(DOCS / slug_segment(top), top, len(GROUPS) + i)
    for rel in files:
        for depth in range(1, len(rel.parts) - 1):
            name = rel.parts[depth]
            if name in SUBGROUPS:
                target = DOCS.joinpath(*[slug_segment(p) for p in rel.parts[:depth + 1]])
                if not (target / "meta.ts").exists():
                    write_meta(target, SUBGROUPS[name], depth)

    (SPECS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    write_page(DOCS / "index.mdx", manifest["project"] + " — reports",
               "Analysis and design documents generated by nexus-architect",
               landing_page(project, known, html_reports, manifest), order=0)

    pages = sum(1 for _ in DOCS.rglob("*.mdx"))
    print(f"sync_reports: {pages} pages from {len(files)} files in {reports}"
          f" -> {DOCS}" + (f" ({errors} failed)" if errors else ""))
    return 1 if errors else 0


def newest_mtime(root: Path) -> float:
    latest = 0.0
    for p in root.rglob("*"):
        try:
            latest = max(latest, p.stat().st_mtime)
        except OSError:
            pass
    return latest


def main(argv: list[str]) -> int:
    project = Path.cwd()
    watch: float | None = None
    for a in argv:
        if a == "--watch":
            watch = 2.0
        elif a.startswith("--watch="):
            watch = float(a.split("=", 1)[1])
        elif a.startswith("-"):
            print(__doc__, file=sys.stderr)
            return 2
        else:
            project = Path(a).expanduser().resolve()
    rc = sync(project)
    if watch is None:
        return rc
    stamp = newest_mtime(project / "reports")
    print(f"sync_reports: watching {project / 'reports'} every {watch:g}s (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(watch)
            now = newest_mtime(project / "reports")
            if now != stamp:
                stamp = now
                sync(project)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
