# Viewing Reports as a Local Documentation Site

`tools/docs-site.sh` serves a project's `reports/` tree as a browsable, searchable documentation
site on your machine, using [Blume](https://useblume.dev) — a Markdown-first documentation
framework on Astro. Nothing is uploaded and nothing in `reports/` is modified: the site is a
**stage** rebuilt from the reports on every run.

```bash
tools/docs-site.sh                 # sync reports/ of the current project, start the dev server
tools/docs-site.sh dev ~/proj      # the same for another project directory
tools/docs-site.sh build           # static site into tools/docs-site/dist/
tools/docs-site.sh validate        # check every internal link of the staged site
tools/docs-site.sh clean           # remove the generated stage
```

Options: `--port=N`, `--host`, `--open`, `--no-watch` (dev: do not re-sync when `reports/`
changes), `--no-install`. `PROJECT_DIR` defaults to the current directory when it has `reports/`,
otherwise to the repository root. The first run installs Blume into `tools/docs-site/node_modules`
(Node ≥ 22.12 is required; every other generated directory there is git-ignored).

## What the site contains

| Source | Becomes | Note |
|--------|---------|------|
| `reports/**/*.md` | one page per report, at `/<dir>/<name>` with the numeric phase prefix dropped (`01_analysis/system-overview.md` → `/analysis/system-overview`) | Mermaid diagrams render; the report's own frontmatter is shown under the title and kept under the `nexus` key |
| `reports/**/*.json` (manifests, review findings) | a code page at the same route | |
| `reports/**/openapi/*.yaml` | Blume's OpenAPI reference at `/api/<service>` | one page per operation, in search |
| `reports/**/asyncapi/*.yaml` | Blume's AsyncAPI reference at `/events/<name>` | |
| `reports/00_summary/full-report.html` | served as-is at `/full-report.html` | |
| `work/pipeline-progress.json` | the landing page: options, every phase with its status and links to its outputs | |

Cross-report links (`reports/03_design/context-map.md`, `../01_analysis/x.md#anchor`) are rewritten
to site routes; links to project files the site cannot serve (`samples/…/Order.java`,
`work/context.md`) become plain text. Each top-level directory is a sidebar group in pipeline
order; pages inside follow the manifest's declared-output order.

## How it works

`tools/docs-site/sync_reports.py` converts every report to **MDX** — Blume renders Mermaid only in
`.mdx` pages — and escapes what MDX would otherwise parse (`{…}` as an expression, a bare `<` as a
JSX tag), leaving fenced and inline code untouched. `tools/docs-site/blume.config.ts` declares the
`nexus` frontmatter key (Blume rejects unknown keys and its built-in `id`/`status` collide with the
ADR shape) and mounts the specs the sync copied. `blume validate` reports the links that were
already broken in the reports — typically section-number anchors such as `scalardb-schema.md#9.5`
that were never heading ids; fix those in the report, not in the site.
