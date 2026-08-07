"""Live dashboard for a nexus-architect project — every view in one screen.

Builds the four views and hands them to the curses shell in status_tui.py:

  Product     the product pipeline's phase progress
  Architect   the architect pipeline's phase progress
  Codegen     the code-generation phases of both plugins
  Backlog     the Epic -> Sub-Epic -> Issue delivery tree

Product and architect are separate pipelines with separate manifests, so they are
separate tabs; code generation is run by hand after either of them and emits code rather
than reports, so it is a third. Tab / Shift-Tab move between them, skipping the ones this
project has nothing behind, and each keeps its own selection, folds and filter.

Inputs are re-checked every NX_INTERVAL seconds and re-read only when they changed, so
the selection survives a refresh. Invoked by tools/nexus-status.sh.

Usage: nexus_status_tui.py <project-dir>
"""

import curses
import locale
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backlog_status_view as BV  # noqa: E402
import pipeline_status_view as PV  # noqa: E402
import status_tui as S  # noqa: E402
import token_cost_data as D  # noqa: E402

PROJ = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NX_PROJECT_DIR", ".")
env = os.environ.get
LANG = env("NX_LANG", "en")
VIEW = env("NX_VIEW", "auto")
PLUGIN = env("NX_PLUGIN", "") or None


def build_views():
    """The four tabs, in strip order, wired so codegen reuses the pipeline tabs' work.

    The codegen tab only shows a group for a plugin whose pipeline actually ran, and the
    two pipeline tabs have just derived exactly that — so it reads their verdict instead
    of deriving both manifests a second time on every 10-second poll.
    """
    product = PV.PipelineView(PROJ, LANG, plugin="product")
    architect = PV.PipelineView(PROJ, LANG, plugin="architect")

    def sources():
        found = [v.plugin for v in (product, architect) if v.state["evidence"]]
        return found or [product.state["detected_plugin"]]

    manifest = os.path.join(PROJ, "reports", "backlog", "backlog-manifest.json")
    return [product, architect, PV.CodegenView(PROJ, LANG, sources=sources),
            BV.BacklogView(manifest, LANG)]


def initial_view(views):
    """Which tab opens, from --view / --plugin, falling back to the detected pipeline."""
    names = [v.name for v in views]
    want = VIEW
    if want == "pipeline":
        want = PLUGIN or views[0].state["detected_plugin"]
    elif want == "auto":
        want = "backlog" if not views[0].state["has_progress"] else (
            PLUGIN or views[0].state["detected_plugin"])
    idx = names.index(want) if want in names else 0
    if views[idx].available:
        return idx
    return next((i for i, v in enumerate(views) if v.available), idx)


def main(stdscr):
    S.debug("start term=%s encoding=%s locale=%s ncurses=%s size=%dx%d "
            "glyphs=%s ambiguous_wide=%s view=%s",
            os.environ.get("TERM", "-"), getattr(sys.stdout, "encoding", "-"),
            locale.setlocale(locale.LC_CTYPE), curses.version,
            *stdscr.getmaxyx()[::-1], "ascii" if D.ASCII_ONLY else "unicode",
            D.AMBIGUOUS_WIDE, VIEW)
    if curses.has_colors():
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(3, curses.COLOR_WHITE, -1)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
        curses.init_pair(5, curses.COLOR_YELLOW, -1)
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)
        curses.init_pair(7, curses.COLOR_RED, -1)

    views = build_views()
    app = S.App(stdscr, views, initial_view(views))
    for view in views:
        if isinstance(view, BV.BacklogView):
            view.sync_at_start(app)
    app.run()


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "")
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
