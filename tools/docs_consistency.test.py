#!/usr/bin/env python3
"""Consistency checks for the documentation that describes the skill corpus.

The catalogue of commands lives in docs/skill-reference.md (+ _ja); CLAUDE.md, README.md and
AGENTS.md carry only a grouped summary and pointers. That split is only safe if something asserts
the pieces still agree with the registry (.claude-plugin/marketplace.json), with the manifests, and
with each SKILL.md — otherwise the summaries rot exactly the way the full lists did.

Every check here exists because the corresponding drift was found in a real review:
a flag invented by prose instead of read off the skill, a catalogue missing a command, a hardcoded
count left behind, a runtime doc that never learned about five skills.

Usage: python3 tools/docs_consistency.test.py     (exit 1 on failure)
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

failures = 0
checks = 0


def check(label, condition, detail=""):
    global failures, checks
    checks += 1
    print("  [%s] %s%s" % (
        "ok" if condition else "FAIL",
        label,
        " — " + str(detail) if detail and not condition else "",
    ))
    if not condition:
        failures += 1


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def registered():
    """{plugin: [skill dir, ...]} exactly as marketplace.json ships them."""
    data = json.loads(read(".claude-plugin/marketplace.json"))
    return {p["name"]: [os.path.normpath(s) for s in p.get("skills", [])]
            for p in data["plugins"]}


def commands(reg):
    return ["/%s:%s" % (plugin, os.path.basename(d))
            for plugin, dirs in reg.items() for d in dirs]


def manifest_phases(path):
    return set(re.findall(r"^  ([a-z][a-z0-9-]*):", read(path), re.M))


def phase_set(name):
    """A dict literal's top-level keys in pipeline_status_data.py."""
    src = read("tools/lib/pipeline_status_data.py")
    block = src.split(name + " = {", 1)[1].split("\n}", 1)[0]
    return set(re.findall(r'^    "([a-z-]+)"', block, re.M))


def codegen_phases():
    src = read("tools/lib/pipeline_status_data.py")
    block = src.split("CODEGEN_PHASES = {", 1)[1].split("\n}", 1)[0]
    return set(re.findall(r'"([a-z-]+)"', block)) - {"architect", "product"}


REG = registered()
CMDS = commands(REG)
EN = read("docs/skill-reference.md")
JA = read("docs/skill-reference_ja.md")
CLAUDE = read("CLAUDE.md")
README = read("README.md")
AGENTS = read("AGENTS.md")

# ---------------------------------------------------------------- catalogue

print("Catalogue covers every registered command")

SIG_HEADINGS = ("## Invocation signatures", "## 呼び出しシグネチャ")


def mentions(doc, cmd):
    """`/architect:update-knowledge` must not be satisfied by `…-knowledgeX`."""
    return re.search(re.escape(cmd) + r"(?![A-Za-z0-9_-])", doc) is not None


def catalogue_body(doc):
    """The described tables — everything above the signature block, which is checked separately."""
    for heading in SIG_HEADINGS:
        if heading in doc:
            return doc.split(heading, 1)[0]
    return doc


for doc_name, doc in (("skill-reference.md", EN), ("skill-reference_ja.md", JA)):
    body = catalogue_body(doc)
    missing = [c for c in CMDS if not mentions(body, c)]
    check("%s describes all %d commands" % (doc_name, len(CMDS)), not missing, missing)

def signature_block(doc):
    for heading in SIG_HEADINGS:
        if heading in doc:
            return doc.split(heading, 1)[1]
    return ""


def signatures(doc):
    block = signature_block(doc)
    return {line.split()[0]: line.strip()
            for line in block.splitlines() if line.startswith("/")}


EN_SIGS = signatures(EN)
JA_SIGS = signatures(JA)

check("signature block exists in both catalogues", bool(EN_SIGS) and bool(JA_SIGS))
check("signature block covers all %d commands" % len(CMDS),
      set(EN_SIGS) == set(CMDS),
      "missing %s / unknown %s" % (sorted(set(CMDS) - set(EN_SIGS)),
                                   sorted(set(EN_SIGS) - set(CMDS))))
check("both languages ship the same signatures", EN_SIGS == JA_SIGS,
      [c for c in EN_SIGS if EN_SIGS.get(c) != JA_SIGS.get(c)])

# ------------------------------------------------------- no invented flags

print("Every documented flag exists in the skill that would receive it")

skill_dir = {"/%s:%s" % (plugin, os.path.basename(d)): d
             for plugin, dirs in REG.items() for d in dirs}
def flag_tokens(text):
    """Flags as spelled, keeping the placeholder: --skip-{phase} stays distinct from --skip-<phase>."""
    return set(re.findall(r"--[a-z][a-z0-9-]*(?:\{[a-z]+\}|<[a-z_-]+>)?", text))


invented = []
for cmd, sig in sorted(EN_SIGS.items()):
    body = read(os.path.join(skill_dir[cmd], "SKILL.md"))
    for token in flag_tokens(sig):
        # A flag is documented only if the skill spells it the same way. Accepting a mere
        # prefix match would let prose rewrite --skip-{phase} into --skip-<phase> unnoticed,
        # since the skill's own --skip-* wildcard would still "contain" it.
        if token not in body:
            invented.append("%s: %s" % (cmd, token))
check("no signature flag is absent from its SKILL.md", not invented, invented)

# The other direction: where a skill states its own signature, the catalogue must not quietly
# offer a different flag set (added, dropped, or renamed).
mismatched = []
for cmd, sig in sorted(EN_SIGS.items()):
    front = read(os.path.join(skill_dir[cmd], "SKILL.md")).split("---", 2)[1]
    # Frontmatter signatures wrap across lines, so flatten before slicing — reading only the
    # first physical line would report a truncated flag set as a mismatch.
    flat = " ".join(front.split())
    at = flat.find(cmd + " [")
    if at < 0:
        continue
    declared = flag_tokens(flat[at:at + 400].split(" to invoke")[0])
    if declared and declared != flag_tokens(sig):
        mismatched.append("%s: skill %s vs catalogue %s" % (
            cmd, sorted(declared), sorted(flag_tokens(sig))))
check("catalogue flag set == the skill's own declared set", not mismatched, mismatched)

FLAG = r"--[a-z][a-z0-9-]*(?:\{[a-z]+\}|<[a-z_-]+>)?"


def body_flags(cmd, body):
    """Flags a skill documents about itself, in the three shapes the corpus actually uses.

    Deliberately not "every --token in the file": bodies quote other skills' flags
    (`verify-implementation --gate`) and shell flags, which are not this command's surface.
    """
    found = set()
    found |= set(re.findall(r"^- `(" + FLAG + r")`", body, re.M))          # bullet list
    for line in body.splitlines():
        stripped = line.strip()
        row = re.match(r"\|\s*`(" + FLAG + r")`(?:\s*/\s*`(" + FLAG + r")`)?", stripped)
        if row:                                                            # option table row
            found |= {g for g in row.groups() if g}
        if cmd in line:                                                    # its own invocation
            found |= set(re.findall(FLAG, line[line.index(cmd):]))
    return found


# Every flag a skill documents about itself must be offered by the catalogue. A subset relation,
# not equality: these lists are often partial, so equality would fail on correct skills.
# This is what caught /architect:pipeline's --analyze-only (documented in the body, present in no
# summary) and /product:generate-frontend's three version flags (in its usage line and option
# table, missing from its own frontmatter signature and therefore from the catalogue).
# Residual gap, stated rather than implied: a flag mentioned only in free prose is not checked.
undocumented = []
for cmd, sig in sorted(EN_SIGS.items()):
    body = read(os.path.join(skill_dir[cmd], "SKILL.md")).split("---", 2)[2]
    absent = body_flags(cmd, body) - flag_tokens(sig)
    if absent:
        undocumented.append("%s: %s" % (cmd, sorted(absent)))
check("every flag a skill documents about itself is in the catalogue", not undocumented, undocumented)

# Where a skill is a thin wrapper over a shell tool, the catalogue must not offer a flag that
# tool would reject. This is the only check backed by an argument parser rather than by prose,
# and it is the one that would have caught /architect:report-status documenting --view/--exec in
# one place and not another: the tool is the arbiter. Tools with no long-flag parser (positional
# subcommands, e.g. update-okf-bundle.sh) are skipped rather than guessed at.
rejected = []
for cmd, sig in sorted(EN_SIGS.items()):
    skill = read(os.path.join(skill_dir[cmd], "SKILL.md"))
    wrapped = set(re.findall(r"tools/([a-z0-9_-]+\.sh)", skill))
    # A skill may name several tools (the status skills cross-reference each other), so the
    # arbiter is the union of what the tools it names accept, not each one separately.
    accepted, arbiters = set(), []
    for tool in sorted(wrapped):
        path = os.path.join("tools", tool)
        if not os.path.exists(os.path.join(ROOT, path)):
            continue
        src = read(path)
        flags = set(re.findall(r"(--[a-z][a-z0-9-]*)[=*]{0,2}\)", src))
        flags |= set(re.findall(r"(--[a-z][a-z0-9-]*)\|", src))
        if len(flags) < 5:             # not a flag-driven tool; nothing to arbitrate
            continue
        accepted |= flags
        arbiters.append(tool)
    if arbiters:
        unknown = {f.split("=")[0] for f in flag_tokens(sig)} - accepted
        if unknown:
            rejected.append("%s: %s not accepted by %s" % (cmd, sorted(unknown), arbiters))
check("no catalogue flag would be rejected by the tool the skill wraps", not rejected, rejected)

# ------------------------------------------------------------ group counts

print("Grouped summaries partition the corpus")

core = manifest_phases("skills/common/skill-dependencies.yaml")
ext = phase_set("EXTENSION_PHASES")
backlog = {"export-backlog", "deliver-backlog", "implement-backlog", "review-issue",
           "merge-issue", "capture-followup", "report-backlog-status"}
migration = {"migrate-database", "migrate-oracle", "migrate-mysql", "migrate-postgresql"}
orchestration = {"start", "pipeline", "init-output"}

arch = {os.path.basename(d) for d in REG["architect"]}
utility = arch - core - ext - backlog - migration - orchestration

expected = {
    "Product Direction": len(REG["product"]),
    "Orchestration & setup": len(orchestration),
    "Core pipeline": len(core & arch),
    "Extension tier": len(ext & arch),
    "Backlog Delivery": len(backlog & arch),
    "Database Migration": len(migration & arch),
    "ScalarDB Development": len(REG["scalardb"]),
    "Status & utility": len(utility),
}
check("the eight groups partition all %d commands" % len(CMDS),
      sum(expected.values()) == len(CMDS), expected)

for doc_name, doc in (("CLAUDE.md", CLAUDE), ("README.md", README)):
    rows = dict(re.findall(r"^\| \*\*([^*]+)\*\*[^|]*\|.*\| (\d+) \|$", doc, re.M))
    check("%s group table is present" % doc_name, len(rows) == len(expected), sorted(rows))
    wrong = {g: (rows.get(g), n) for g, n in expected.items() if rows.get(g) != str(n)}
    check("%s group counts match the registry" % doc_name, not wrong, wrong)
    check("%s states the corpus size" % doc_name,
          ("%d slash commands" % len(CMDS)) in doc or ("%d skills" % len(CMDS)) in doc)
    check("%s points at the catalogue" % doc_name, "docs/skill-reference.md" in doc)

# The pointer must not be @-imported: CLAUDE.md @-paths are pulled into every session, which
# would re-add the catalogue this split exists to keep out.
check("CLAUDE.md does not @-import the catalogue", "@docs/skill-reference.md" not in CLAUDE)

# --------------------------------------------------------- tier enumeration

print("CLAUDE.md tier prose matches the code that renders it")

tier_para = CLAUDE.split("**manual extension tier**", 1)[0].rsplit("The manifest covers", 1)[-1]
check("extension tier list == EXTENSION_PHASES",
      set(re.findall(r"`([a-z][a-z0-9-]*)`", tier_para)) == ext,
      sorted(ext ^ set(re.findall(r"`([a-z][a-z0-9-]*)`", tier_para))))

rest_para = CLAUDE.split("The extension tier is **not** everything", 1)[1].split("Within that tier", 1)[0]
check("out-of-tier groups == the rest of the architect skills",
      set(re.findall(r"`([a-z][a-z0-9-]*)`", rest_para)) == (arch - core - ext),
      sorted((arch - core - ext) ^ set(re.findall(r"`([a-z][a-z0-9-]*)`", rest_para))))

cg = codegen_phases()
chain = CLAUDE.split("Within that tier the codegen skills", 1)[-1].split("**Product → architect handoff.**", 1)[0]
named = set(re.findall(r"`/?(?:product:)?([a-z-]+)`", chain))
check("the codegen chain names every CODEGEN_PHASES entry", cg.issubset(named), sorted(cg - named))

# ------------------------------------------------------------ other runtimes

print("The other runtime entry docs know every skill")

for plugin, dirs in REG.items():
    missing = [os.path.basename(d) for d in dirs if not mentions(AGENTS, os.path.basename(d))]
    check("AGENTS.md model table covers %s" % plugin, not missing, missing)

# ------------------------------------------------------------- rules index

print("Rules index is complete")

rules = sorted(f for f in os.listdir(os.path.join(ROOT, "rules")) if f.endswith(".md"))
missing = [r for r in rules if "rules/" + r not in CLAUDE]
check("every top-level rules/*.md is listed in CLAUDE.md", not missing, missing)

print()
print("%d check(s), %d failure(s)" % (checks, failures))
sys.exit(1 if failures else 0)
