#!/usr/bin/env python3
"""Contract test for tools/lib/ui_inventory.py — the nine rules of @rules/ui-analysis.md §4.

Each negative case below is an inventory that reads perfectly well and is wrong: a transition to a
screen nobody declared, a component whose `used_by` disagrees with the screens that use it, a submit
button no feature owns, a source line past the end of its file. The validator must name each one,
and must never answer a hostile shape with a traceback.

Run: python3 tools/lib/ui_inventory.test.py
Exit 0 = all checks pass, 1 = at least one failed (the repo-wide convention).
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ui_fixture  # noqa: E402
from ui_inventory import validate_inventory, validate_tokens  # noqa: E402

TOOL = os.path.join(HERE, "ui_inventory.py")
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


def rejects(label, mutate, *, expect):
    """The mutated fixture must fail, with a message containing `expect`. A crash fails too:
    a crash is the one answer a validator may never give."""
    inv = ui_fixture.inventory()
    mutate(inv)
    try:
        errors = validate_inventory(inv)
    except Exception as exc:  # noqa: BLE001
        check(label, False, "raised %r" % exc)
        return
    check(label, any(expect in e for e in errors), errors)


def accepts(label, mutate):
    inv = ui_fixture.inventory()
    mutate(inv)
    errors = validate_inventory(inv)
    check(label, errors == [], errors)


def screen(inv, sid):
    return next(s for s in inv["screens"] if s["id"] == sid)


print("the fixture is well-formed")
check("shape only", validate_inventory(ui_fixture.inventory()) == [],
      validate_inventory(ui_fixture.inventory()))

print("rule 1 — unique, well-formed ids")
rejects("duplicate screen id", lambda i: screen(i, "UIS-002").update(id="UIS-001"),
        expect="duplicate screen id")
rejects("malformed screen id", lambda i: screen(i, "UIS-005").update(id="SCR-005"),
        expect="id must be UIS-###")
rejects("action id of another screen",
        lambda i: screen(i, "UIS-002")["actions"][0].update(id="UIS-003.A9"),
        expect="id must be UIS-002.A<n>")
rejects("duplicate action id",
        lambda i: screen(i, "UIS-003")["actions"][1].update(id="UIS-003.A1"),
        expect="duplicate action id")

print("rule 2 — name, source, route")
rejects("a screen without a name", lambda i: screen(i, "UIS-002").pop("name"),
        expect="name is required")
rejects("a null route with no reason", lambda i: screen(i, "UIS-005").update(route=None),
        expect="route is required unless route_unresolved")
accepts("a null route that says why",
        lambda i: screen(i, "UIS-005").update(route=None, route_unresolved="forwarded dynamically"))
rejects("entry that is not a boolean", lambda i: screen(i, "UIS-001").update(entry="yes"),
        expect="entry must be a boolean")

print("rule 3 — typed inputs and accessibility facts")
rejects("an unknown control",
        lambda i: screen(i, "UIS-001")["inputs"][0].update(control="combo"),
        expect="control must be one of")
rejects("required as a string",
        lambda i: screen(i, "UIS-001")["inputs"][0].update(required="true"),
        expect="required must be a boolean")
rejects("a validation that does not say where it runs",
        lambda i: screen(i, "UIS-001")["inputs"][0]["validation"][0].pop("where"),
        expect="rule and where")
rejects("a missing label association",
        lambda i: screen(i, "UIS-003")["inputs"][0].pop("label_association"),
        expect="label_association must be one of")
rejects("an image that does not state alt",
        lambda i: screen(i, "UIS-003")["images"][0].pop("alt"),
        expect="alt must be stated")
rejects("a color pair that is not hex",
        lambda i: screen(i, "UIS-003")["color_pairs"][0].update(fg="gray"),
        expect="fg and bg must be hex")

print("rule 4 — every action resolves")
rejects("a target nobody declared",
        lambda i: screen(i, "UIS-002")["actions"][0].update(target="UIS-099"),
        expect="is not a declared screen")
rejects("no target, no endpoint, no reason",
        lambda i: screen(i, "UIS-005")["actions"][0].update(target=None),
        expect="resolves to neither")
accepts("an action that says why it is unresolved",
        lambda i: screen(i, "UIS-005")["actions"][0].update(
            target=None, unresolved="URL built in JavaScript at runtime"))

print("rule 5 — component references agree both ways")
rejects("a screen listing an undeclared component",
        lambda i: screen(i, "UIS-005")["components"].append("UIC-099"),
        expect="is not declared")
rejects("used_by that disagrees with the screens",
        lambda i: i["components"][0]["used_by"].remove("UIS-004"),
        expect="disagrees with the screens that list it")
rejects("an unused component not marked unused",
        lambda i: (screen(i, "UIS-003")["components"].remove("UIC-003"),
                   i["components"][2].update(used_by=[])),
        expect="mark it unused: true")
accepts("an unused component marked unused",
        lambda i: (screen(i, "UIS-003")["components"].remove("UIC-003"),
                   i["components"][2].update(used_by=[], unused=True)))
rejects("a component duplicating itself",
        lambda i: i["components"][1].update(duplicates=["UIC-002"]),
        expect="not another declared component")

print("rule 6 — features own every submit and AJAX action")
rejects("a submit action no feature owns", lambda i: i["features"].pop(2),
        expect="belongs to 0 features")
rejects("an action two features claim",
        lambda i: i["features"][1]["actions"].append("UIS-003.A3"),
        expect="belongs to 2 features")
rejects("a feature citing a missing action",
        lambda i: i["features"][0]["actions"].append("UIS-001.A7"),
        expect="does not exist")
rejects("feature screens that are not its actions' screens",
        lambda i: i["features"][0].update(screens=["UIS-002"]),
        expect="are not the screens of its actions")

print("rule 7 — embedded logic is classified")
rejects("logic without a home",
        lambda i: screen(i, "UIS-003")["embedded_logic"][0].pop("should_live_in"),
        expect="should_live_in")
rejects("logic of an unknown kind",
        lambda i: screen(i, "UIS-003")["embedded_logic"][0].update(kind="magic"),
        expect="kind, should_live_in")

print("structural contracts")
rejects("coverage that does not count the screens",
        lambda i: i["coverage"].update(screens=4), expect="coverage.screens is 4")
rejects("an unresolved entry without a reason",
        lambda i: i["coverage"]["unresolved"].append({"ref": "web/x.jsp"}),
        expect="needs ref and reason")
rejects("no token file named", lambda i: i.pop("design_tokens"),
        expect="design_tokens must name")

print("hostile shapes report, never crash")
for label, mutate, expect in (
        ("screens as an object", lambda i: i.update(screens={"a": 1}), "non-empty array"),
        ("a screen as a string", lambda i: i["screens"].append("UIS-006"), "must be an object"),
        ("inputs as an object", lambda i: screen(i, "UIS-001").update(inputs={"x": 1}), ""),
        ("an action as a string", lambda i: screen(i, "UIS-002")["actions"].append("go"),
         "must be an object"),
        ("an id as a list", lambda i: screen(i, "UIS-002").update(id=["UIS-002"]), "UIS-###"),
        ("components as a string", lambda i: i.update(components="none"), "must be an array"),
        ("a feature as a number", lambda i: i["features"].append(7), "must be an object")):
    rejects(label, mutate, expect=expect) if expect else accepts(label, mutate)

print("rule 9 — the token file is valid DTCG")
tok = ui_fixture.tokens()
check("the fixture tokens are valid", validate_tokens(tok)[0] == [], validate_tokens(tok)[0])
bad = copy.deepcopy(tok)
bad["color"]["hex-0066cc"].pop("$type")
check("a token without $type", any("$type" in e for e in validate_tokens(bad)[0]))
bad = copy.deepcopy(tok)
bad["semantic"]["color"]["primary"]["$value"] = "{color.hex-999999}"
check("an alias that resolves to nothing", any("not a token" in e for e in validate_tokens(bad)[0]))
bad = copy.deepcopy(tok)
bad["space"]["px-8"]["$extensions"]["nexus-architect"]["sources"] = []
check("a raw token without sources", any("no $extensions" in e for e in validate_tokens(bad)[0]))
bad = copy.deepcopy(tok)
bad["color"]["hex-aaaaaa"]["$value"] = "grey"
check("a color that is not hex", any("not a hex color" in e for e in validate_tokens(bad)[0]))
bad = copy.deepcopy(tok)
bad["color"]["hex-aaaaaa"]["$extensions"]["nexus-architect"]["usage_count"] = 0
check("a zero usage count", any("positive integer" in e for e in validate_tokens(bad)[0]))

print("rules 8 and 9 against a scratch project")
tmp = tempfile.mkdtemp(prefix="ui-inventory-test-")


def project(name, inv=None, tok=None, drop=()):
    root = os.path.join(tmp, name)
    ui_fixture.write_project(root, inv, tok)
    for relative in drop:
        os.remove(os.path.join(root, relative))
    return root


def run(root, *extra):
    return subprocess.run([sys.executable, TOOL, root] + list(extra),
                          capture_output=True, text=True)


try:
    root = project("clean")
    errors = validate_inventory(ui_fixture.inventory(), root)
    check("the scratch project is well-formed, sources and tokens included", errors == [], errors)
    proc = run(root)
    check("CLI exit 0 on a clean project", proc.returncode == 0, proc.stdout + proc.stderr)
    check("CLI names what it validated", "is well-formed (5 screens, 3 components, 3 features)"
          in proc.stdout, proc.stdout)

    root = project("missing-file", drop=("target/js/cart.js",))
    errors = validate_inventory(ui_fixture.inventory(), root)
    check("a cited file that does not exist", any("js/cart.js:4" in e and "does not exist" in e
                                                   for e in errors), errors)

    inv = ui_fixture.inventory()
    screen(inv, "UIS-003")["inputs"][0]["source"] = "web/cart.jsp:400"
    errors = validate_inventory(inv, project("past-eof", inv))
    check("a line past the end of the file", any("past the end of the file" in e for e in errors),
          errors)

    inv = ui_fixture.inventory()
    screen(inv, "UIS-003")["inputs"][0]["source"] = "../../etc/passwd"
    errors = validate_inventory(inv, project("escape", inv))
    check("a source outside the target", any("does not exist under the target" in e
                                              for e in errors), errors)

    inv = ui_fixture.inventory()
    screen(inv, "UIS-003")["inputs"][0]["source"] = "web/cart.jsp:9-3"
    errors = validate_inventory(inv)
    check("a range that ends before it starts", any("ends before it starts" in e for e in errors),
          errors)

    inv = ui_fixture.inventory()
    inv["target_path"] = "nowhere"
    errors = validate_inventory(inv, project("no-target", inv))
    check("a target that is not a directory", any("is not a directory" in e for e in errors),
          errors)
    proc = run(os.path.join(tmp, "no-target"), "--target-root=%s"
               % os.path.join(tmp, "no-target", "target"))
    check("--target-root overrides a moved target", proc.returncode == 0, proc.stdout)

    inv = ui_fixture.inventory()
    inv["components"][0]["token_refs"] = ["color.hex-123456"]
    errors = validate_inventory(inv, project("bad-ref", inv))
    check("a component token_ref that is not a token", any("token_refs names" in e for e in errors),
          errors)

    root = project("no-tokens", drop=(ui_fixture.TOKENS_PATH,))
    errors = validate_inventory(ui_fixture.inventory(), root)
    check("a token file that does not exist", any("is unreadable" in e for e in errors), errors)

    tok = ui_fixture.tokens()
    tok["color"]["hex-0066cc"]["$extensions"]["nexus-architect"]["sources"] = ["web/none.css:1"]
    errors = validate_inventory(ui_fixture.inventory(), project("token-source", tok=tok))
    check("a token source that does not exist", any("token color.hex-0066cc" in e for e in errors),
          errors)

    inv = ui_fixture.inventory()
    inv["screens"][1]["actions"][0]["target"] = "UIS-099"
    proc = run(project("cli-fail", inv))
    check("CLI exit 1 and a count on violations",
          proc.returncode == 1 and "violation(s)" in proc.stdout, proc.stdout)

    empty = os.path.join(tmp, "empty")
    os.makedirs(os.path.join(empty, "reports"))
    proc = run(empty)
    check("CLI exit 0 when there is nothing to validate",
          proc.returncode == 0 and "nothing to validate" in proc.stdout, proc.stdout)

    root = project("unreadable")
    with open(os.path.join(root, ui_fixture.INVENTORY_PATH), "w") as handle:
        handle.write("{not json")
    proc = run(root)
    check("an unreadable inventory is a violation, not a traceback",
          proc.returncode == 1 and "unreadable" in proc.stdout and "Traceback" not in proc.stderr,
          proc.stdout + proc.stderr)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d checks, %d failed" % (PASSED + FAILED, FAILED))
sys.exit(1 if FAILED else 0)
