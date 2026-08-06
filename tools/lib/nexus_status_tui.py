"""Live dashboard for a nexus-architect project — pipeline and backlog in one screen.

Builds the two views and hands them to the curses shell in status_tui.py: the pipeline
tab (product / architect phase progress) and the backlog tab (Epic -> Sub-Epic -> Issue
delivery). Tab switches between them; each keeps its own selection, folds and filter.

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

    manifest = os.path.join(PROJ, "reports", "backlog", "backlog-manifest.json")
    views = [PV.PipelineView(PROJ, LANG), BV.BacklogView(manifest, LANG)]
    initial = 1 if VIEW == "backlog" else 0
    if not views[initial].available:
        initial = next((i for i, v in enumerate(views) if v.available), initial)
    app = S.App(stdscr, views, initial)
    views[1].sync_at_start(app)
    app.run()


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "")
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
