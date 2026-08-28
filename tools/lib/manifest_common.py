"""What the design-manifest validators share.

`state_machine_manifest.py` and `aggregate_manifest.py` validate different models but read the
same kind of artifact: a JSON manifest under `reports/03_design/` whose entries each point at a
Markdown document. The document check, the size cap, the consistency-class vocabulary and the
load/report envelope are the same contract, so they live here once — two copies with one
diverging constant is how a validator quietly stops checking what the other one checks.

`api_style_decisions.py` keeps its own `MAX_DOCUMENT_BYTES` (1 MB): that artifact is a decision
record, not a design document, and its cap was set on purpose.
"""

import json
import os

MAX_DOCUMENT_BYTES = 4 * 1024 * 1024

# The transactional scope of a command or a transition (@rules/aggregate-design.md §4,
# @rules/state-modeling.md §5).
CONSISTENCY = ("local", "distributed", "saga")


def inside_file(project_dir, relative):
    """A declared document must be a non-empty file that stays inside the project."""
    if not isinstance(relative, str) or not relative.strip():
        return False
    root = os.path.realpath(project_dir) + os.sep
    path = os.path.realpath(os.path.join(project_dir, relative))
    if not path.startswith(root) or not os.path.isfile(path):
        return False
    size = os.path.getsize(path)
    return 0 < size <= MAX_DOCUMENT_BYTES


def duplicates(values):
    """True when a value repeats. Tolerates unhashable junk (a list where a string was
    expected) — that is a shape violation the caller reports separately, not a crash."""
    seen = set()
    for value in values:
        key = value if isinstance(value, (str, int, float, bool, type(None))) \
            else json.dumps(value, sort_keys=True, default=str)
        if key in seen:
            return True
        seen.add(key)
    return False


def load_manifest(project_dir, relative_path, label, validate):
    """(manifest, errors) for a project directory. A missing manifest is not an error here —
    the phase is optional, and a project that never ran it has nothing to check."""
    path = os.path.join(project_dir, relative_path)
    if not os.path.isfile(path):
        return None, []
    try:
        with open(path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, ["%s: unreadable — %s" % (label, exc)]
    return manifest, validate(manifest, project_dir)


def report(manifest, errors, project_dir, label, count_key):
    """The CLI envelope: one line per violation, exit 1 on any; 0 with a summary otherwise."""
    if manifest is None and not errors:
        print("no %s in %s — nothing to validate" % (label, project_dir))
        return 0
    for error in errors:
        print(error)
    if errors:
        print("%d violation(s)" % len(errors))
        return 1
    print("%s is well-formed (%d %s)" % (label, len(manifest.get(count_key, [])), count_key))
    return 0
