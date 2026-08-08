#!/usr/bin/env python3
"""Contract asserted by the curses shell and the two view modules it drives.

The shell (status_tui.App) had no tests at all, and every defect the TUI review turned up
lived in exactly that layer: the `c` key opening a browser instead of copying, the action
menu losing `Esc close`, the help panel printing its glyph legend once per tab and running
off the bottom of an 80x24 terminal, an empty filtered tree reporting "this pipeline never
ran", and Esc quitting on a stray escape sequence.

None of that needs a terminal. App touches `stdscr` only while drawing, so the key
handling, the action dispatch and the panel assembly are all exercised here against a
`stdscr` of None; the drawing itself stays covered by the PTY smoke test in
nexus-status.test.sh. Run with no arguments.
"""

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
os.environ.setdefault("NX_PLUGIN_ROOT", ROOT)

FAILURES = []


def check(label, ok, detail=""):
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           "" if ok else "  <- %s" % detail))
    if not ok:
        FAILURES.append(label)


# --------------------------------------------------------------------------- fixture
def make_project(tmp):
    """A product project mid-pipeline with a failed phase the manifest does not know,
    plus a two-Epic backlog whose first Issue is done (so its default action is an open)."""
    proj = os.path.join(tmp, "proj")
    os.makedirs(os.path.join(proj, "work"))
    os.makedirs(os.path.join(proj, "reports", "00_core"))
    os.makedirs(os.path.join(proj, "reports", "backlog"))
    with open(os.path.join(proj, "work", "pipeline-progress.json"), "w") as fh:
        fh.write("""{ "project_name": "fx", "options": { "output_language": "en" },
          "phases": { "define-vision": { "status": "completed" },
                      "define-scope": { "status": "in_progress" },
                      "hand-written-phase": { "status": "failed" } } }""")
    for name in ("vision-mission-value", "pr-faq", "constraints"):
        with open(os.path.join(proj, "reports", "00_core", "%s.md" % name), "w") as fh:
            fh.write("x\n")
    with open(os.path.join(proj, "reports", "backlog",
                           "backlog-manifest.json"), "w") as fh:
        fh.write("""{ "platform": "github", "project": "o/r", "nodes": [
          { "local_id": "E1", "level": "epic", "title": "Epic one" },
          { "local_id": "I1.1", "level": "issue", "parent_local_id": "E1", "title": "A",
            "impl": { "status": "done" },
            "remote": { "iid": 1, "url": "https://example.invalid/1" } },
          { "local_id": "E2", "level": "epic", "title": "Epic two" } ] }""")
    return proj


TMP = tempfile.mkdtemp(prefix="nx-tui-")
PROJ = make_project(TMP)
os.environ["NX_PROJECT_DIR"] = PROJ
os.environ["NX_LANG"] = "en"

import backlog_status_data as B      # noqa: E402
import backlog_status_view as BV     # noqa: E402
import pipeline_status_data as P     # noqa: E402
import pipeline_status_view as PV    # noqa: E402
import status_tui as S               # noqa: E402


def build_views():
    product = PV.PipelineView(PROJ, "en", plugin="product")
    architect = PV.PipelineView(PROJ, "en", plugin="architect")
    codegen = PV.CodegenView(PROJ, "en", sources=lambda: ["product"])
    backlog = BV.BacklogView(os.path.join(PROJ, "reports", "backlog",
                                          "backlog-manifest.json"), "en")
    return [product, architect, codegen, backlog]


def build_app(views=None):
    """An App with no screen. Nothing below draws, and the clipboard is stubbed out."""
    views = views or build_views()
    app = S.App(None, views, 0)
    app.clip_tool = ["stub"]
    return app


# ------------------------------------------------------------- the open/copy contract
print("action dispatch: what `c` promises vs what the menu promises")

COPIED, OPENED = [], []
S.copy_clipboard = lambda tool, text: (COPIED.append(text), True)[1]
S.open_target = lambda target: (OPENED.append(target), True)[1]

emitted = set()
for state, phase in [(v.state, p) for v in build_views()
                     if isinstance(v, PV.PipelineView)
                     for p in v.state["phases"].values()]:
    emitted.update(label for label, _ in P.actions_for(state, phase))
bl = build_views()[3]
for node in bl.by_id.values():
    emitted.update(label for label, _ in
                   B.actions_for(node, bl.states[node["local_id"]], 0))
check("every open-type label the data modules emit is known to the shell",
      set(S.OPEN_LABELS) <= emitted,
      "shell knows %r, data emits %r" % (S.OPEN_LABELS, sorted(emitted)))

app = build_app()
backlog = app.views[3]
app.view_idx = 3
done_issue = backlog.by_id["I1.1"]
label, command = backlog.default_action(done_issue)
check("a done Issue's default action is an open", label in S.OPEN_LABELS, label)

COPIED[:], OPENED[:] = [], []
app.perform(done_issue, label, command, allow_open=False)
check("`c` copies the URL instead of launching a browser",
      COPIED == [command] and OPENED == [], "copied=%r opened=%r" % (COPIED, OPENED))

COPIED[:], OPENED[:] = [], []
app.perform(done_issue, label, command)
check("choosing `open URL` from the menu still opens it",
      OPENED == [command] and COPIED == [], "copied=%r opened=%r" % (COPIED, OPENED))

product = app.views[0]
app.view_idx = 0
finished = next(r for r, _, _ in product.rows()
                if r["kind"] == "phase" and r["phase"]["name"] == "define-vision")
label, command = product.default_action(finished)
COPIED[:], OPENED[:] = [], []
app.perform(finished, label, command, allow_open=False)
check("`c` on a completed phase copies the report path, not opens it",
      COPIED == [command] and OPENED == [], "copied=%r opened=%r" % (COPIED, OPENED))

# ------------------------------------------------------------------ the action menu
print("action menu")

check("the hint keeps `Esc close` when --exec is off",
      "Esc close" in S.menu_hint(S.SHELL_LABELS["en"], False),
      S.menu_hint(S.SHELL_LABELS["en"], False))
check("the hint says how to turn --exec on when it is off",
      S.SHELL_LABELS["en"]["exec_hint"] in S.menu_hint(S.SHELL_LABELS["en"], False))
check("the hint offers the run key when --exec is on",
      "e run via claude" in S.menu_hint(S.SHELL_LABELS["en"], True))
ja = S.menu_hint(S.SHELL_LABELS["ja"], False)
check("the localized hint keeps its close key too", "Esc 閉じる" in ja, ja)

app = build_app()
app.view_idx = 0
app.open_menu(finished)
runnable = next(i for i, (lb, _) in enumerate(app.modal["entries"])
                if lb not in S.OPEN_LABELS)
app.modal["sel"] = runnable
S.EXEC_ENABLED = False
app.handle_modal_key(ord("e"))
check("`e` without --exec keeps the menu open instead of losing your place",
      app.modal is not None)

app.open_menu(finished)
open_idx = next(i for i, (lb, _) in enumerate(app.modal["entries"])
                if lb in S.OPEN_LABELS)
app.modal["sel"] = open_idx
COPIED[:], OPENED[:] = [], []
S.EXEC_ENABLED = True
app.handle_modal_key(ord("e"))
check("`e` on an open entry opens it rather than claiming --exec is off",
      OPENED and app.modal is None, "opened=%r modal=%r" % (OPENED, app.modal))
S.EXEC_ENABLED = False

app.open_menu(finished)
app.modal["sel"] = runnable
label = app.modal["entries"][runnable][0]
RAN = []
app.run_claude = lambda cmd: RAN.append(cmd)
S.EXEC_ENABLED = True
app.handle_modal_key(ord("e"))
check("`e` with --exec hands a real command to claude",
      RAN == [dict(app.views[0].actions_for(finished))[label]] and app.modal is None,
      "ran=%r" % (RAN,))
S.EXEC_ENABLED = False

app = build_app()
app.view_idx = 0
app.open_menu(finished)
app.handle_modal_key(27)
check("Esc closes the action menu", app.modal is None)

# ------------------------------------------------------------------- the help panel
print("help panel")

views = build_views()
lines = S.help_panel_lines(views, "en")
legend = P.labels("en")["help_glyphs"]
check("the pipeline glyph legend appears once, not once per pipeline tab",
      sum(1 for t, _ in lines if t == legend) == 1,
      "%d occurrences across %d views"
      % (sum(1 for t, _ in lines if t == legend),
         sum(1 for v in views if v.available)))
check("the backlog legend is still there",
      any(t == B.labels("en")["help_glyphs"] for t, _ in lines))
check("the key legend documents Esc as close, not quit",
      any("close a menu" in t for t, _ in lines))
check("the key legend no longer offers Esc as a way to quit",
      not any("Esc" in t and "quit" in t and "close" not in t for t, _ in lines))

app = build_app(views)
app.help_open = True
app.help_top = 0
check("j scrolls the help panel", app.scroll_help(ord("j")) and app.help_top == 1)
check("k scrolls back", app.scroll_help(ord("k")) and app.help_top == 0)
check("k at the top does not scroll past it",
      app.scroll_help(ord("k")) and app.help_top == 0)
check("any other key falls through so the panel closes",
      app.scroll_help(ord("x")) is False)

# ----------------------------------------------------------- empty tree explanations
print("an empty tree says why it is empty")

views = build_views()
product, backlog = views[0], views[3]
unfiltered = product.empty_message()
product.status_filter = "skipped"
filtered = product.empty_message()
check("a filtered-empty pipeline blames the filter, not the project",
      "skipped" in filtered and filtered != unfiltered, filtered)
check("it names the key that clears the filter",
      P.labels("en")["clear_filter"] in filtered, filtered)
check("the filter is reported through the label table, not a hardcoded word",
      P.labels("en")["filter"] in filtered, filtered)
product.status_filter = None
check("with no filter it goes back to describing the project",
      product.empty_message() == unfiltered)

PV.TIER = "extension"
check("--group=extension on a pipeline with no extension tier blames --group",
      "--group=extension" in product.empty_message(), product.empty_message())
check("--group does not advertise `f`, which cannot clear it",
      P.labels("en")["clear_filter"] not in product.empty_message(),
      product.empty_message())
PV.TIER = None

check("the codegen tab ignores --group, so it must not blame it",
      "--group" not in (lambda: (setattr(PV, "TIER", "extension"),
                                 views[2].empty_message())[1])())
PV.TIER = None

backlog_unfiltered = backlog.empty_message()
BV.EPIC_FILTER = "E99"
check("an unknown --epic blames --epic instead of the manifest",
      "--epic=E99" in backlog.empty_message(), backlog.empty_message())
BV.EPIC_FILTER = None
backlog.status_filter = "blocked"
check("a filtered-empty backlog blames the filter",
      "blocked" in backlog.empty_message(), backlog.empty_message())
backlog.status_filter = None
check("with nothing set the backlog message is unchanged",
      backlog.empty_message() == backlog_unfiltered)

# ------------------------------------------------------------------ failure headline
print("a failure reaches the headline")

product = build_views()[0]
header = " ".join(t for t, _ in product.header_lines(120))
failed = [p["name"] for p in product.state["phases"].values()
          if p["display_status"] == "failed"]
check("the fixture does have a failed phase outside the counted set",
      failed == ["hand-written-phase"] and
      product.state["summary"]["by_status"]["failed"] == 0,
      "failed=%r counted=%r" % (failed, product.state["summary"]["by_status"]))
check("the header names it even though the status counts cannot",
      "hand-written-phase" in header, header)
check("the header never emits a blank line",
      all(t.strip() for t, _ in product.header_lines(120)),
      [t for t, _ in product.header_lines(120)])
check("the header stays within what the shell draws",
      len(product.header_lines(120)) <= 5, len(product.header_lines(120)))

codegen = build_views()[2]
check("a codegen tab with nothing to say emits no empty line",
      all(t.strip() for t, _ in codegen.header_lines(120)),
      [t for t, _ in codegen.header_lines(120)])

# ------------------------------------------------------------------------ ask panel
print("ask panel")

product = build_views()[0]
finished = next(r for r, _, _ in product.rows()
                if r["kind"] == "phase" and r["phase"]["name"] == "define-vision")
questions = product.ask_questions(finished)
check("a completed phase is not asked why it is 'still completed'",
      not any("still completed" in q for q in questions), questions)
running = next(r for r, _, _ in product.rows()
               if r["kind"] == "phase" and r["phase"]["name"] == "define-scope")
asked = product.ask_questions(running)
check("an unfinished phase still gets the why question",
      any("in_progress" in q for q in asked), asked)

# --------------------------------------------------------------- the poll, and Esc
print("poll and key ownership")

views = build_views()
app = build_app(views)
walks = []
for view in views:
    if isinstance(view, PV.PipelineView):
        original = view.extra_stamp
        view.extra_stamp = (lambda o=original, n=view.name:
                            (walks.append(n), o())[1])
app.stamps_now()
check("the three pipeline tabs share one filesystem walk per poll",
      len(walks) == 1, "walked for %r" % (walks,))
check("they share it because they declare the same stamp_key",
      views[0].stamp_key() == views[1].stamp_key() == views[2].stamp_key())
check("a view with nothing to share opts out with None",
      views[3].stamp_key() is None)

app = build_app()
check("q quits", app.handle_key(ord("q")) is False)
check("Q quits too", app.handle_key(ord("Q")) is False)
check("a bare Esc does NOT quit - a stray escape sequence must not kill the dashboard",
      app.handle_key(27) is True)
check("Esc says how to actually quit instead of doing nothing",
      app.notice and S.SHELL_LABELS["en"]["quit_hint"] in app.notice[0],
      app.notice)

# The sequence a terminal with application-cursor-mode off emits for the down arrow.
# ncurses cannot map it, so it arrives as three ordinary keypresses, the first of which
# is Esc — the exact way the old binding took the dashboard down.
app = build_app()
survived = all(app.handle_key(k) for k in (27, ord("["), ord("B")))
check("an unmappable arrow sequence (Esc [ B) leaves the dashboard running", survived)

for lang in ("en", "ja"):
    T = S.SHELL_LABELS[lang]
    hints = [P.labels(lang)["keys"], B.labels(lang)["keys"]]
    check("[%s] the pinned q/? legend is not duplicated inside a view's hint" % lang,
          all("q " not in h.split("|")[-1] for h in hints),
          [h.split("|")[-1] for h in hints])
    check("[%s] the pinned legend names both ways out" % lang,
          "q" in T["keys_essential"] and "?" in T["keys_essential"],
          T["keys_essential"])

app = build_app()
app.handle_key(ord("?"))
check("? opens the help panel", app.help_open)
check("a scroll key keeps it open", app.handle_key(ord("j")) and app.help_open)
check("Esc closes the help panel rather than quitting",
      app.handle_key(27) is True and not app.help_open)

print()
print("%d failure(s)" % len(FAILURES))
sys.exit(1 if FAILURES else 0)
