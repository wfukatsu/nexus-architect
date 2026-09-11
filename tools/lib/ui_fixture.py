"""The well-formed UI model the three UI suites share.

`ui_inventory.test.py`, `ui_metrics.test.py` and `ux_evaluation.test.py` each mutate a copy of
this model and expect a specific answer. Keeping one model means a change to the inventory shape
(@rules/ui-analysis.md §3) is made once and every suite sees it — three hand-copied fixtures are
how one of them quietly stops describing the shape the others test.

The scenario is a five-screen shop with one of each defect the metrics must see: a login page
with no `lang`, a cart with an unlabeled input, an image without `alt`, a low-contrast pair, a
redundant e-mail input, a client-only pattern and an unconfirmed delete, a completion page whose
only exit is logging out (dead end), a help page nothing links to (orphan), two shades of the
primary blue, a button duplicated with inline styles, and a logout labelled two ways.
"""

import copy
import os

SOURCE_FILES = {
    "web/login.jsp": 20,
    "web/menu.jsp": 20,
    "web/cart.jsp": 40,
    "web/complete.jsp": 10,
    "web/help.jsp": 10,
    "web/header.jspf": 10,
    "web/tags/button.tag": 10,
    "web/css/common.css": 30,
    "src/LoginServlet.java": 30,
    "src/CartServlet.java": 60,
    "js/cart.js": 30,
}

TOKENS_PATH = "reports/before/shop/ui-design-tokens.json"
INVENTORY_PATH = "reports/before/shop/ui-inventory.json"


def _action(aid, label, kind, target=None, endpoint=None, command=None, scope="screen",
            destructive=False, confirmation=False, source="web/menu.jsp:5"):
    return {"id": aid, "label": label, "command": command, "kind": kind, "scope": scope,
            "method": "POST" if kind == "submit" else "GET", "endpoint": endpoint,
            "target": target, "destructive": destructive, "confirmation": confirmation,
            "unresolved": None, "source": source}


def _access(roles=("customer",), guards=()):
    return {"authentication": "required" if roles else "none", "roles": list(roles),
            "guards": [dict(g) for g in guards]}


_INVENTORY = {
    "schema_version": 1,
    "project": "shop",
    "target_path": "target",
    "ui_roots": ["web"],
    "technologies": [{"name": "JSP", "evidence": "web/login.jsp"}],
    "design_tokens": TOKENS_PATH,
    "screens": [
        {
            "id": "UIS-001", "name": "Login", "route": "/login", "source": "web/login.jsp",
            "entry": True,
            "handlers": [{"ref": "LoginServlet#doPost", "source": "src/LoginServlet.java:12"}],
            "access": _access(roles=()),
            "inputs": [
                {"name": "userId", "label": "User ID", "label_association": "for",
                 "control": "text", "type": "string", "required": True,
                 "validation": [{"rule": "required", "value": None, "where": "server",
                                 "source": "src/LoginServlet.java:15"}],
                 "prefilled_from": None, "redundant_with": None, "source": "web/login.jsp:8"},
                {"name": "password", "label": "Password", "label_association": "for",
                 "control": "password", "type": "string", "required": True, "validation": [],
                 "prefilled_from": None, "redundant_with": None, "source": "web/login.jsp:10"},
            ],
            "outputs": [],
            "actions": [_action("UIS-001.A1", "Log in", "submit", target="UIS-002",
                                endpoint="POST /login", command="LogIn",
                                source="web/login.jsp:12")],
            "messages": [{"kind": "error", "text": "Invalid user ID or password",
                          "source": "web/login.jsp:6"}],
            "components": [],
            "embedded_logic": [],
            "lang": None,
            "images": [],
            "color_pairs": [],
        },
        {
            "id": "UIS-002", "name": "Menu", "route": "/menu", "source": "web/menu.jsp",
            "entry": False, "handlers": [],
            "access": _access(guards=[{"kind": "filter", "source": "src/LoginServlet.java:3"}]),
            "inputs": [], "outputs": [],
            "actions": [
                _action("UIS-002.A1", "Cart", "link", target="UIS-003", source="web/menu.jsp:5"),
                _action("UIS-002.A2", "Log out", "link", target="UIS-001", command="LogOut",
                        scope="global", source="web/header.jspf:4"),
            ],
            "messages": [], "components": ["UIC-001"], "embedded_logic": [], "lang": "en",
            "images": [], "color_pairs": [],
        },
        {
            "id": "UIS-003", "name": "Cart", "route": "/cart", "source": "web/cart.jsp",
            "entry": False,
            "handlers": [{"ref": "CartServlet#doGet", "source": "src/CartServlet.java:20"}],
            "access": _access(),
            "inputs": [
                {"name": "quantity", "label": None, "label_association": "placeholder-only",
                 "control": "number", "type": "integer", "required": True,
                 "validation": [
                     {"rule": "min", "value": 1, "where": "client", "source": "js/cart.js:4"},
                     {"rule": "min", "value": 1, "where": "server",
                      "source": "src/CartServlet.java:31"}],
                 "prefilled_from": None, "redundant_with": None, "source": "web/cart.jsp:12"},
                {"name": "email", "label": "E-mail", "label_association": "none",
                 "control": "email", "type": "string", "required": True,
                 "validation": [{"rule": "pattern", "value": ".+@.+", "where": "client",
                                 "source": "js/cart.js:9"}],
                 "prefilled_from": None, "redundant_with": "the logged-in user's e-mail",
                 "source": "web/cart.jsp:16"},
                {"name": "csrf", "label": None, "label_association": "none", "control": "hidden",
                 "type": "string", "required": True, "validation": [], "prefilled_from": "session",
                 "redundant_with": None, "source": "web/cart.jsp:18"},
            ],
            "outputs": [{"name": "lines", "label": "Cart lines", "kind": "table",
                         "fields": ["product", "price", "quantity"], "source": "web/cart.jsp:20"}],
            "actions": [
                _action("UIS-003.A1", "Sign out", "link", target="UIS-001", command="LogOut",
                        scope="global", source="web/header.jspf:4"),
                _action("UIS-003.A2", "Remove", "submit", target="UIS-003",
                        endpoint="POST /cart/remove", command="RemoveCartLine", destructive=True,
                        source="web/cart.jsp:24"),
                _action("UIS-003.A3", "Order", "submit", target="UIS-004",
                        endpoint="POST /order", command="PlaceOrder", source="web/cart.jsp:30"),
            ],
            "messages": [],
            "components": ["UIC-001", "UIC-002", "UIC-003"],
            "embedded_logic": [{"kind": "calculation", "description": "Line total",
                                "should_live_in": "domain", "source": "js/cart.js:12-18"}],
            "lang": "en",
            "images": [{"src": "/img/p1.png", "alt": None, "decorative": False,
                        "source": "web/cart.jsp:21"}],
            "color_pairs": [{"fg": "#aaaaaa", "bg": "#ffffff", "text": "normal",
                             "where": ".note", "source": "web/css/common.css:14"}],
        },
        {
            "id": "UIS-004", "name": "Order complete", "route": "/order/complete",
            "source": "web/complete.jsp", "entry": False, "handlers": [], "access": _access(),
            "inputs": [], "outputs": [{"name": "orderNo", "label": "Order number",
                                       "kind": "field", "fields": [],
                                       "source": "web/complete.jsp:5"}],
            "actions": [_action("UIS-004.A1", "Sign out", "link", target="UIS-001",
                                command="LogOut", scope="global",
                                source="web/header.jspf:4")],
            "messages": [], "components": ["UIC-001"], "embedded_logic": [], "lang": "en",
            "images": [], "color_pairs": [],
        },
        {
            "id": "UIS-005", "name": "Help", "route": "/help.jsp", "source": "web/help.jsp",
            "entry": False, "handlers": [], "access": _access(roles=()),
            "inputs": [], "outputs": [],
            "actions": [_action("UIS-005.A1", "Menu", "link", target="UIS-002",
                                source="web/help.jsp:3")],
            "messages": [], "components": [], "embedded_logic": [], "lang": "en",
            "images": [], "color_pairs": [],
        },
    ],
    "components": [
        {"id": "UIC-001", "name": "Header", "kind": "include", "level": "organism",
         "source": "web/header.jspf", "variants": [], "states": [],
         "used_by": ["UIS-002", "UIS-003", "UIS-004"], "token_refs": ["color.hex-333333"],
         "duplicates": []},
        {"id": "UIC-002", "name": "Button", "kind": "tag", "level": "atom",
         "source": "web/tags/button.tag", "variants": ["primary", "secondary"], "states": [],
         "used_by": ["UIS-003"], "token_refs": ["color.hex-0066cc"], "duplicates": []},
        {"id": "UIC-003", "name": "Inline order button", "kind": "inline-style", "level": "atom",
         "source": "web/cart.jsp:30", "variants": [], "states": [], "used_by": ["UIS-003"],
         "token_refs": ["color.hex-1a73e8"], "duplicates": ["UIC-002"]},
    ],
    "features": [
        {"id": "UIF-001", "name": "Log in", "command": "LogIn", "actions": ["UIS-001.A1"],
         "screens": ["UIS-001"], "actors": ["customer"], "entities": ["User"],
         "handlers": ["LoginServlet#doPost"]},
        {"id": "UIF-002", "name": "Remove a cart line", "command": "RemoveCartLine",
         "actions": ["UIS-003.A2"], "screens": ["UIS-003"], "actors": ["customer"],
         "entities": ["Cart"], "handlers": ["CartServlet#doPost"]},
        {"id": "UIF-003", "name": "Place an order", "command": "PlaceOrder",
         "actions": ["UIS-003.A3"], "screens": ["UIS-003"], "actors": ["customer"],
         "entities": ["Order"], "handlers": ["CartServlet#doPost"]},
    ],
    "coverage": {"template_files": 7, "screens": 5, "unresolved": []},
}


def _raw(value, kind, sources, count, cluster=None):
    ext = {"sources": list(sources), "usage_count": count}
    if cluster:
        ext["cluster"] = cluster
    return {"$type": kind, "$value": value, "$extensions": {"nexus-architect": ext}}


_TOKENS = {
    "$description": "As-is design tokens of shop",
    "color": {
        "hex-0066cc": _raw("#0066cc", "color", ["web/css/common.css:3"], 6, "primary-blue"),
        "hex-1a73e8": _raw("#1a73e8", "color", ["web/cart.jsp:30"], 1, "primary-blue"),
        "hex-333333": _raw("#333333", "color", ["web/css/common.css:5"], 9, "text-dark"),
        "hex-aaaaaa": _raw("#aaaaaa", "color", ["web/css/common.css:14"], 2, "text-muted"),
    },
    "font": {"size": {"px-14": _raw("14px", "dimension", ["web/css/common.css:7"], 12)}},
    "space": {"px-8": _raw("8px", "dimension", ["web/css/common.css:9"], 10)},
    "semantic": {"color": {"primary": {"$type": "color", "$value": "{color.hex-0066cc}",
                                       "$description": "candidate: most-used of primary-blue"}}},
}

# What ui_metrics.compute must say about the model above (asserted by ui_metrics.test.py and
# relied on by ux_evaluation.test.py): H 4 (one unconfirmed delete), A 2 (two of five screens
# violate), E 4 (one redundant input), C 2 (fragmented blue, drift, duplicate), N 3 (orphan,
# dead end).
EXPECTED_CAPS = {"H": 4, "A": 2, "E": 4, "C": 2, "N": 3}


def inventory():
    return copy.deepcopy(_INVENTORY)


def tokens():
    return copy.deepcopy(_TOKENS)


def write_project(root, inv=None, tok=None):
    """A scratch project: the inventory and token file under reports/, and the analysed
    codebase under target/ with every file the model cites, long enough for its line refs."""
    import json
    for relative, lines in SOURCE_FILES.items():
        path = os.path.join(root, "target", relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join("line %d" % n for n in range(1, lines + 1)))
    for relative, data in ((INVENTORY_PATH, inv if inv is not None else inventory()),
                           (TOKENS_PATH, tok if tok is not None else tokens())):
        path = os.path.join(root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
