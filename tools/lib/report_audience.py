"""Which reports open with an ELI5 section, and when.

One list, read by three consumers so they cannot drift: `hooks/validate-frontmatter.sh` (rejects a
technical report that lacks the section), `rules/eli5-summary.md` (names this module instead of
copying the list) and `tools/docs_consistency.test.py` (every name here is a registered skill).

A report is "technical" when the `skill:` in its frontmatter is one of TECHNICAL_REPORT_SKILLS —
the skills whose documents are written for engineers: investigation and evaluation scores, tactical
models, transaction boundaries, API contracts, review synthesis. The seven review-* phases write JSON
only, so their plain-language rendering is the synthesizer's Markdown.
"""
import re

ELI5_MODES = ("technical", "all", "off")
DEFAULT_ELI5_MODE = "technical"

# The fixed heading token. A localized subtitle may follow it: `## ELI5 — the short version`.
ELI5_HEADING = re.compile(r"^## ELI5\b", re.M)

TECHNICAL_REPORT_SKILLS = frozenset({
    # architect — investigation, analysis, evaluation
    "investigate", "investigate-security", "investigate-db-design", "investigate-db-live",
    "analyze", "analyze-data-model", "analyze-ui",
    "evaluate-mmi", "evaluate-ddd", "evaluate-ux", "integrate-evaluations",
    # architect — design
    "redesign", "design-aggregate", "design-state-machine", "design-microservices",
    "select-scalardb-edition", "design-scalardb", "design-scalardb-analytics", "design-data-layer",
    "design-api", "design-graphql", "design-implementation", "design-infrastructure",
    "design-security", "design-observability", "design-disaster-recovery",
    "design-sql-migration", "verify-sql-migration",
    # architect — review synthesis, verification, estimation
    "review-synthesizer", "verify-implementation", "estimate-cost",
    # product — the technical tail of the product pipeline
    "define-data-model", "map-domains", "design-sla", "define-nfr", "design-architecture",
    # infra — the `skill:` values templates/infra/*.md carry
    "infra-design", "infra-review",
})


def eli5_mode(options):
    """`options.eli5` of work/pipeline-progress.json; absent or unknown → the default."""
    mode = (options or {}).get("eli5")
    return mode if mode in ELI5_MODES else DEFAULT_ELI5_MODE


def eli5_required(frontmatter, options):
    """Whether this Markdown report has to open with a `## ELI5` section.

    An Architecture Decision Record (its frontmatter carries `decided_at` — the shape of
    rules/architecture-decision-records.md §2), a document with no `skill:` key, and a document
    declaring `eli5: false` (a technical skill's non-prose output — an environment matrix) are
    exempt whatever the mode.
    """
    fm = frontmatter or {}
    if fm.get("eli5") is False or "decided_at" in fm:
        return False
    skill = fm.get("skill")
    if not skill:
        return False
    mode = eli5_mode(options)
    if mode == "off":
        return False
    if mode == "all":
        return True
    return str(skill) in TECHNICAL_REPORT_SKILLS


def has_eli5_section(body):
    return bool(ELI5_HEADING.search(body or ""))


def extract_eli5(body):
    """The ELI5 section's Markdown — from its heading to the next `##` — or `None`."""
    m = ELI5_HEADING.search(body or "")
    if not m:
        return None
    rest = body[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    section = rest[:nxt.start()] if nxt else rest
    # Drop the heading's own subtitle text (the remainder of the heading line).
    section = section.split("\n", 1)[1] if "\n" in section else ""
    return section.strip("\n")
