#!/usr/bin/env python3
"""Contract test for tools/lib/ui_views.py — the four views are projections, not prose.

The views `/architect:analyze-ui` publishes are rendered from the inventory, so this suite pins what
a rendering must be: every view passes both output hooks and has no `#` heading; the canonical
section names are present in either language; the figures a metric covers come from the metrics;
the facts a reader looks for (an input's validation and where it runs, a view-only guard, a dead end,
a client-only rule, a fragmented cluster) are on the page; and the same inventory renders to the same
bytes.

Run: python3 tools/lib/ui_views.test.py
Exit 0 = all checks pass, 1 = at least one failed (the repo-wide convention).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import ui_fixture  # noqa: E402
from ui_views import VIEWS, render  # noqa: E402

TOOL = os.path.join(HERE, "ui_views.py")
HOOKS = os.path.join(REPO, "hooks")
PASSED = 0
FAILED = 0


def check(label, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print("  [ok] %s" % label)
    else:
        FAILED += 1
        print("  [FAIL] %s%s" % (label, (" — %s" % detail) if detail else ""))


SECTIONS = {
    "ui-screen-catalog.md": ["Summary", "Screen Transition Diagram", "Screen List", "Screen Details",
                             "Screen-to-Code Map", "Business Logic in the View Layer",
                             "Unresolved Items and Open Questions"],
    "ui-features.md": ["Feature List", "Tasks", "Actor × Feature", "Feature × Entity",
                       "Validation Rules as Acceptance-Criteria Candidates"],
    "ui-components.md": ["Component Inventory", "Hand-Built Duplicates", "Unused Components"],
    "ui-design-system-extract.md": ["Palette", "Typography", "Spacing, Radius, Borders and Shadow",
                                    "Fragmentation", "Semantic Token Candidates",
                                    "Component Variants", "Importing into a Design System"],
}

tmp = tempfile.mkdtemp(prefix="ui-views-test-")
try:
    root = os.path.join(tmp, "project")
    inv = ui_fixture.inventory()
    inv["generated_at"] = "2026-09-11T00:00:00Z"
    inv["open_questions"] = ["OQ-001"]
    ui_fixture.write_project(root, inv)
    os.makedirs(os.path.join(root, "work"), exist_ok=True)
    with open(os.path.join(root, "work", "context.md"), "w", encoding="utf-8") as handle:
        handle.write("## Open Questions\n\n| ID | Question | Status | Answer | Options offered | "
                     "Owner | Impact | Asked at |\n|---|---|---|---|---|---|---|---|\n"
                     "| OQ-001 | Who can reach the help page? | unasked | | | product owner | "
                     "UIS-005 | |\n")

    for lang in ("en", "ja"):
        print("rendering in %s" % lang)
        proc = subprocess.run([sys.executable, TOOL, root, "--lang=%s" % lang],
                              capture_output=True, text=True)
        check("exit 0", proc.returncode == 0, proc.stderr)
        base = os.path.join(root, "reports", "before", "shop")
        for name in VIEWS:
            path = os.path.join(base, name)
            text = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
            check("%s is written" % name, bool(text))
            for hook in ("validate-frontmatter.sh", "validate-mermaid.sh"):
                run = subprocess.run(["bash", os.path.join(HOOKS, hook), path],
                                     capture_output=True, text=True)
                check("%s passes %s" % (name, hook), run.returncode == 0,
                      (run.stdout + run.stderr)[-400:])
            body = re.sub(r"```.*?```", "", text.split("\n---\n", 1)[-1], flags=re.S)
            check("%s has no # heading" % name, not re.search(r"^# ", body, re.M))
            headings = re.findall(r"^## (.+)$", body, re.M)
            missing = [s for s in SECTIONS[name] if not any(s in h for h in headings)]
            check("%s carries its canonical sections" % name, not missing, missing)
            if lang == "ja":
                check("%s headings are Japanese with the English name" % name,
                      all("（" in h for h in headings), headings)

    en = render(root, inv, ui_fixture.tokens(), "en")
    catalog, features = en["ui-screen-catalog.md"], en["ui-features.md"]
    components, design = en["ui-components.md"], en["ui-design-system-extract.md"]

    print("the facts a reader looks for")
    check("an input's validation shows where it runs", "min=1 @client" in catalog
          and "min=1 @server" in catalog)
    check("a redundant input is noted", "redundant: the logged-in user's e-mail" in catalog)
    check("where an action lands and what it sends",
          "UIS-004 (POST /order)" in catalog and "quantity, email, csrf" in catalog)
    check("the dead end and the orphan are styled in the diagram",
          "class UIS004 deadend" in catalog and "class UIS005 orphan" in catalog)
    check("global chrome actions are not diagram edges", "UIS003 -->|LogOut|" not in catalog)
    check("an unresolved question is shown from the store",
          "OQ-001 | Who can reach the help page? | unasked" in catalog)
    check("view-layer logic is listed with where it should live",
          "Line total | domain | `js/cart.js:12-18`" in catalog)
    check("task steps come from the metrics", "| Buy | Order what is in the cart | UIS-002 → "
          "UIS-003 → UIS-004 | 3 | 2 | 2 |" in features, features)
    check("a client-only rule is flagged",
          "client only — the server accepts what it forbids" in features)
    check("entity operations are shown", "| UIF-003 | Place an order | Cart | RD |" in features)
    check("a hand-built duplicate names what it rebuilds", "UIC-002 Button" in components)
    check("a fragmented cluster gets a consolidation proposal",
          "Consolidate to #0066cc (most used)" in design)
    check("a semantic candidate shows its alias and value",
          "`semantic.color.primary` | `color.hex-0066cc` | `#0066cc`" in design)
    check("the import command names the project's token file",
          "--import=reports/before/shop/ui-design-tokens.json" in design)

    guarded = ui_fixture.inventory()
    guarded["screens"][2]["access"]["guards"] = [{"kind": "view", "source": "web/cart.jsp:2"}]
    views = render(root, guarded, ui_fixture.tokens(), "en")
    check("a screen guarded only in the view is marked", "(view-only)" in views["ui-screen-catalog.md"])
    check("so are the features behind it", "✓ (view-only)" in views["ui-features.md"])

    print("rendering is deterministic")
    again = render(root, inv, ui_fixture.tokens(), "en")
    check("the same inventory renders to the same bytes", again == en)

    print("refusal")
    bad = ui_fixture.inventory()
    bad["screens"][1]["actions"][0]["target"] = "UIS-099"
    broken = os.path.join(tmp, "broken")
    ui_fixture.write_project(broken, bad)
    proc = subprocess.run([sys.executable, TOOL, broken], capture_output=True, text=True)
    check("an inventory that is not well-formed is refused",
          proc.returncode == 1 and "UIS-099" in proc.stderr, proc.stderr)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d checks, %d failed" % (PASSED + FAILED, FAILED))
sys.exit(1 if FAILED else 0)
