#!/usr/bin/env python3
"""The project audit log: `work/audit/events.jsonl`, append-only.

One JSON object per line, one line per event, never rewritten — the registry
(`work/pipeline-progress.json`) says where a run *is*, this says what *happened* and who
did it: which phases started and ended, which gates a human approved or rejected, which
questions were asked and answered, which decisions were recorded, which pull requests were
opened and merged. Both pipelines append to the one file (`skills/common/progress-registry.md`
§ Audit Log).

Who writes what:
  - phase events: `hooks/record_token_usage.py`, which already watches the registry's status
    transitions, appends one event per transition (source "hook");
  - gate, question, decision, verdict and PR events: the skill that owns the moment, through
    the command line below (source "skill").

Command line (positional, key=value — no `--flags`, so a skill can quote the invocation):

    python3 tools/lib/audit_log.py <project_dir> <EVENT> [phase=…] [plugin=…] [ref=…] [detail=…] [actor=…]
    python3 tools/lib/audit_log.py <project_dir> list [tail=N] [event=…] [phase=…]

Exit 0 on success, 2 on a usage error (unknown event, missing directory). The actor defaults
to `git config user.name` of the project (never the email); pass actor=… to override.
"""
import fcntl
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

AUDIT_DIR = os.path.join("work", "audit")
AUDIT_FILE = "events.jsonl"

# The taxonomy. A category per line; adding an event means adding it here and naming its
# writer in skills/common/progress-registry.md § Audit Log.
EVENTS = {
    "phase": ("PHASE_STARTED", "PHASE_COMPLETED", "PHASE_FAILED", "PHASE_SKIPPED",
              "PHASE_AWAITING_APPROVAL", "PHASE_REVISING"),
    "gate": ("GATE_APPROVED", "GATE_REJECTED", "GATE_SKIPPED"),
    "question": ("QUESTION_ASKED", "QUESTION_ANSWERED", "QUESTION_DEFERRED"),
    "decision": ("ADR_RECORDED", "VERDICT_RECORDED"),
    "delivery": ("PR_OPENED", "PR_MERGED"),
}
CATEGORY = {event: category for category, events in EVENTS.items() for event in events}

# Registry status -> the phase event its transition emits. `pending` emits nothing: it is the
# initial value and what `--rerun-from` resets to, not something that happened.
STATUS_EVENT = {
    "in_progress": "PHASE_STARTED",
    "completed": "PHASE_COMPLETED",
    "failed": "PHASE_FAILED",
    "skipped": "PHASE_SKIPPED",
    "awaiting_approval": "PHASE_AWAITING_APPROVAL",
    "revising": "PHASE_REVISING",
}

FIELDS = ("ts", "event", "category", "phase", "plugin", "actor", "ref", "detail", "source")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def audit_path(project_dir):
    return os.path.join(project_dir, AUDIT_DIR, AUDIT_FILE)


def actor_name(project_dir=None):
    """`git config user.name` for the project, or None. The email is never read."""
    try:
        out = subprocess.run(["git", "config", "user.name"], cwd=project_dir or None,
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    name = (out.stdout or "").strip()
    return name or None


def make_event(event, phase=None, plugin=None, actor=None, ref=None, detail=None,
               source="skill", ts=None):
    if event not in CATEGORY:
        raise ValueError("unknown audit event %r; one of %s" % (
            event, ", ".join(sorted(CATEGORY))))
    return {
        "ts": ts or now_iso(),
        "event": event,
        "category": CATEGORY[event],
        "phase": phase or None,
        "plugin": plugin or None,
        "actor": actor or None,
        "ref": ref or None,
        "detail": detail or None,
        "source": source or None,
    }


def append_events(project_dir, events):
    """Append the records in order under a lock. Returns the records written."""
    if not events:
        return []
    path = audit_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [json.dumps(e, ensure_ascii=False) + "\n" for e in events]
    with open(path, "a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.writelines(lines)
            fh.flush()
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    return events


def append_event(project_dir, event, **fields):
    """Validate, stamp and append one event; fills the actor from git when not given."""
    if "actor" not in fields or fields["actor"] is None:
        fields["actor"] = actor_name(project_dir)
    record = make_event(event, **fields)
    append_events(project_dir, [record])
    return record


def read_events(project_dir, tail=None, event=None, phase=None):
    """The events on file, oldest first; a malformed line is skipped, never raised."""
    path = audit_path(project_dir)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read().splitlines()
    except OSError:
        return []
    out = []
    for line in raw:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict) or not rec.get("event"):
            continue
        if event and rec.get("event") != event:
            continue
        if phase and rec.get("phase") != phase:
            continue
        out.append(rec)
    if tail:
        out = out[-int(tail):]
    return out


def registry_statuses(progress):
    """{phase: {"status", "plugin"}} from a loaded registry, tolerating loose shapes."""
    phases = (progress or {}).get("phases") if isinstance(progress, dict) else None
    out = {}
    for name, entry in (phases or {}).items():
        if isinstance(entry, dict):
            status, plugin = entry.get("status"), entry.get("plugin")
        elif isinstance(entry, str):
            status, plugin = entry, None
        else:
            continue
        if isinstance(status, str):
            out[name] = {"status": status, "plugin": plugin if isinstance(plugin, str) else None}
    return out


def diff_registry(before, after, actor=None, source="hook", ts=None):
    """The phase events the transition from `before` to `after` emits.

    `before` is {phase: status} (a checkpoint); `after` is registry_statuses(). A phase whose
    status is unchanged, or that moved to `pending`, emits nothing. A phase that re-enters a
    status it already left (a rerun) emits again — that is a new occurrence.
    """
    events = []
    for name in sorted(after):
        status = after[name]["status"]
        if before.get(name) == status:
            continue
        event = STATUS_EVENT.get(status)
        if not event:
            continue
        events.append(make_event(event, phase=name, plugin=after[name]["plugin"],
                                 actor=actor, source=source, ts=ts))
    return events


def _parse_kv(args):
    fields = {}
    for arg in args:
        key, sep, value = arg.partition("=")
        if not sep or key not in ("phase", "plugin", "ref", "detail", "actor", "tail", "event"):
            raise ValueError("expected key=value with one of phase, plugin, ref, detail, actor "
                             "(or tail, event for list), got %r" % arg)
        fields[key] = value
    return fields


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    project_dir, verb = argv[0], argv[1]
    if not os.path.isdir(project_dir):
        sys.stderr.write("audit_log: not a directory: %s\n" % project_dir)
        return 2
    try:
        fields = _parse_kv(argv[2:])
    except ValueError as exc:
        sys.stderr.write("audit_log: %s\n" % exc)
        return 2
    if verb == "list":
        for rec in read_events(project_dir, tail=fields.get("tail"), event=fields.get("event"),
                               phase=fields.get("phase")):
            sys.stdout.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return 0
    if verb not in CATEGORY:
        sys.stderr.write("audit_log: unknown event %r; one of: %s\n" % (
            verb, ", ".join(sorted(CATEGORY))))
        return 2
    if "tail" in fields or "event" in fields:
        sys.stderr.write("audit_log: tail= and event= belong to `list`\n")
        return 2
    rec = append_event(project_dir, verb, **fields)
    sys.stdout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
