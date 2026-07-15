#!/usr/bin/env python3
"""Nexus Architect token-usage recorder.

A fail-safe Claude Code hook (PostToolUse on Write|Edit|MultiEdit|Task|Agent,
plus Stop / SubagentStop). It reads the session transcript *incrementally*
(byte-offset per transcript file), sums billed tokens per model from newly
appended assistant turns, and attributes each delta to a pipeline phase:

  1. If phases are `in_progress` in work/pipeline-progress.json -> those phases
     (joined with "+" when parallel), including any previously pending tokens.
  2. Else if phases newly transitioned to `completed` since the last checkpoint
     -> those phases receive the pending bucket + this delta (this covers the
     standard single-skill flow, where skills only write "completed" at the end).
  3. Else the delta accumulates in a pending bucket; at turn end (Stop /
     SubagentStop) with still nothing to attribute to, pending is flushed to
     the permanent "_unassigned" bucket.

Artifacts (both under work/, git-ignored):
  - token-usage.json   aggregated per-phase / per-model usage + USD cost
  - token-usage.jsonl  append-only audit log, one record per firing

Design rules:
  - NEVER fail the session: any error -> exit 0 (set NEXUS_TOKEN_DEBUG=1 to
    append tracebacks to work/token-usage.err).
  - Inert outside initialized pipeline projects (work/pipeline-progress.json
    must exist).
  - Pricing (incl. time-limited introductory prices) comes from
    skills/common/references/model-pricing.json — the single source of truth
    shared with /architect:estimate-token-cost.
  - Concurrent firings are serialized with an flock'd lockfile; a firing that
    cannot get the lock within ~2s gives up silently (the next firing will
    pick up the same transcript bytes, since offsets only advance under lock).
"""

import sys
import os
import json
import time
import errno
from datetime import datetime, timezone, date

USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_5m",
    "cache_creation_1h",
    "web_search_requests",
)

RECENT_IDS_KEEP = 200  # message ids remembered per transcript to dedupe across chunk boundaries
TURN_END_EVENTS = ("Stop", "SubagentStop")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def zero_usage():
    return {k: 0 for k in USAGE_KEYS}


def add_usage(dst, src):
    for k in USAGE_KEYS:
        dst[k] = dst.get(k, 0) + src.get(k, 0)


def usage_is_zero(u):
    return all(u.get(k, 0) == 0 for k in USAGE_KEYS)


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def find_pricing():
    roots = []
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        roots.append(os.environ["CLAUDE_PLUGIN_ROOT"])
    roots.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for r in roots:
        p = os.path.join(r, "skills", "common", "references", "model-pricing.json")
        data = load_json(p)
        if data:
            return data
    return None


def resolve_family(model, pricing):
    m = (model or "").lower()
    for fam in pricing.get("families", []):
        for sub in fam.get("match", []):
            if sub in m:
                return fam["name"], fam
    d = pricing.get("default", {"name": "unknown", "input": 3.0, "output": 15.0})
    return d.get("name", "unknown"), d


def effective_prices(fam):
    """Return (input, output) per-1M prices, honoring introductory pricing windows."""
    inp = fam.get("input", 3.0)
    out = fam.get("output", 15.0)
    until = fam.get("intro_until")
    if until and "intro_input" in fam:
        try:
            if date.today() <= date.fromisoformat(until):
                inp = fam.get("intro_input", inp)
                out = fam.get("intro_output", out)
        except Exception:
            pass
    return inp, out


def usage_cost(usage, fam, pricing):
    mult = pricing.get("cache_multipliers", {})
    inp, out = effective_prices(fam)
    cost = (
        usage.get("input_tokens", 0) * inp
        + usage.get("output_tokens", 0) * out
        + usage.get("cache_read_input_tokens", 0) * inp * mult.get("read", 0.1)
        + usage.get("cache_creation_5m", 0) * inp * mult.get("write_5m", 1.25)
        + usage.get("cache_creation_1h", 0) * inp * mult.get("write_1h", 2.0)
    ) / 1_000_000.0
    per_1k = (pricing.get("server_tools") or {}).get("web_search_per_1k", 0.0)
    cost += usage.get("web_search_requests", 0) * per_1k / 1000.0
    return cost


def by_model_cost(by_model, pricing):
    total = 0.0
    for fam_name, usage in by_model.items():
        _, fam = resolve_family(fam_name, pricing)
        total += usage_cost(usage, fam, pricing)
    return total


def recompute(ledger, pricing):
    totals = zero_usage()
    grand = 0.0
    for phase in ledger.get("phases", {}).values():
        pu = zero_usage()
        for usage in phase.get("by_model", {}).values():
            add_usage(pu, usage)
        phase["usage"] = pu
        phase["cost_usd"] = round(by_model_cost(phase.get("by_model", {}), pricing), 4)
        add_usage(totals, pu)
        grand += phase["cost_usd"]
    pend = ledger.get("_pending", {}).get("by_model", {})
    pend_usage = zero_usage()
    for usage in pend.values():
        add_usage(pend_usage, usage)
    add_usage(totals, pend_usage)
    pend_cost = round(by_model_cost(pend, pricing), 4)
    ledger["pending_usage"] = pend_usage
    ledger["pending_cost_usd"] = pend_cost
    ledger["totals"] = totals
    ledger["total_cost_usd"] = round(grand + pend_cost, 4)


def read_progress(progress_path):
    data = load_json(progress_path) or {}
    phases = data.get("phases", {}) or {}
    in_progress = sorted(n for n, p in phases.items() if isinstance(p, dict) and p.get("status") == "in_progress")
    completed = sorted(n for n, p in phases.items() if isinstance(p, dict) and p.get("status") == "completed")
    return data.get("project_name", ""), in_progress, completed


def parse_new_usage(text, recent_ids):
    """Sum usage per model from newly appended assistant lines.

    One API response can span multiple transcript lines sharing the same
    message.id (each carrying an identical usage object) — count each id once,
    including across chunk boundaries via the persisted recent_ids list.
    """
    seen = set(recent_ids)
    per_model = {}
    new_ids = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") != "assistant":
            continue
        msg = obj.get("message") or {}
        u = msg.get("usage") or {}
        mid = msg.get("id") or obj.get("uuid")
        if not mid or mid in seen:
            continue
        seen.add(mid)
        new_ids.append(mid)
        model = msg.get("model") or "unknown"
        acc = per_model.setdefault(model, zero_usage())
        acc["input_tokens"] += int(u.get("input_tokens") or 0)
        acc["output_tokens"] += int(u.get("output_tokens") or 0)
        acc["cache_read_input_tokens"] += int(u.get("cache_read_input_tokens") or 0)
        cc = u.get("cache_creation") or {}
        c5 = int(cc.get("ephemeral_5m_input_tokens") or 0)
        c1 = int(cc.get("ephemeral_1h_input_tokens") or 0)
        if c5 or c1:
            acc["cache_creation_5m"] += c5
            acc["cache_creation_1h"] += c1
        else:
            acc["cache_creation_5m"] += int(u.get("cache_creation_input_tokens") or 0)
        st = u.get("server_tool_use") or {}
        acc["web_search_requests"] += int(st.get("web_search_requests") or 0)
    return per_model, new_ids


def merge_by_model(dst_by_model, src_by_model, pricing):
    """Merge raw-model-keyed or family-keyed usage into a family-keyed dict."""
    for model, usage in src_by_model.items():
        fam_name, _ = resolve_family(model, pricing)
        acc = dst_by_model.setdefault(fam_name, zero_usage())
        add_usage(acc, usage)


class Lock:
    """flock-based lock with a short retry window; None-safe context manager."""

    def __init__(self, path, timeout=2.0):
        self.path = path
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        import fcntl
        deadline = time.monotonic() + self.timeout
        self.fd = open(self.path, "a+")
        while True:
            try:
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError as e:
                if e.errno not in (errno.EAGAIN, errno.EACCES):
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError("token-usage lock busy")
                time.sleep(0.05)

    def __exit__(self, *exc):
        try:
            import fcntl
            fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            self.fd.close()
        except Exception:
            pass
        return False


def main():
    raw = sys.stdin.read()
    try:
        ev = json.loads(raw) if raw.strip() else {}
    except Exception:
        return

    cwd = ev.get("cwd") or os.getcwd()
    transcript = ev.get("transcript_path")
    session_id = ev.get("session_id") or "unknown"
    hook_event = ev.get("hook_event_name") or ""

    if not transcript or not os.path.isfile(transcript):
        return

    work = os.path.join(cwd, "work")
    progress_path = os.path.join(work, "pipeline-progress.json")
    if not os.path.isfile(progress_path):
        return  # not an initialized pipeline project -> stay inert

    pricing = find_pricing()
    if not pricing:
        return

    ledger_path = os.path.join(work, "token-usage.json")

    with Lock(os.path.join(work, ".token-usage.lock")):
        ledger = load_json(ledger_path)
        first_run = ledger is None
        if first_run:
            ledger = {
                "$schema": "token-usage-v2",
                "project_name": "",
                "created_at": now_iso(),
                "pricing_version": pricing.get("version"),
                "phases": {},
                "_pending": {"by_model": {}},
                "_progress": {"completed_seen": []},
                "_transcripts": {},
            }

        # --- read the new transcript bytes (offset keyed by transcript path) ---
        tstate = ledger.setdefault("_transcripts", {}).setdefault(
            transcript, {"offset": 0, "recent_ids": []}
        )
        size = os.path.getsize(transcript)
        if size < tstate.get("offset", 0):  # rotated/truncated -> restart
            tstate["offset"] = 0
            tstate["recent_ids"] = []
        with open(transcript, "r", encoding="utf-8", errors="replace") as f:
            f.seek(tstate.get("offset", 0))
            new_text = f.read()
            tstate["offset"] = f.tell()

        per_model, new_ids = parse_new_usage(new_text, tstate.get("recent_ids", []))
        if new_ids:
            tstate["recent_ids"] = (tstate.get("recent_ids", []) + new_ids)[-RECENT_IDS_KEEP:]

        # --- decide attribution ---
        project, in_progress, completed = read_progress(progress_path)
        prog = ledger.setdefault("_progress", {"completed_seen": []})
        if first_run:
            # Baseline: phases already completed before tracking started must not
            # receive a retroactive flush.
            prog["completed_seen"] = completed
            newly_completed = []
        else:
            seen = set(prog.get("completed_seen", []))
            newly_completed = [p for p in completed if p not in seen]
            prog["completed_seen"] = sorted(set(prog.get("completed_seen", [])) | set(completed))

        delta = {}
        merge_by_model(delta, per_model, pricing)

        pending = ledger.setdefault("_pending", {"by_model": {}})["by_model"]

        target = None
        if newly_completed:
            target = "+".join(newly_completed)
        elif in_progress:
            target = "+".join(in_progress)

        flushed_pending = False
        if target:
            entry = ledger.setdefault("phases", {}).setdefault(
                target, {"by_model": {}, "usage": zero_usage(), "cost_usd": 0.0}
            )
            merge_by_model(entry["by_model"], pending, pricing)
            merge_by_model(entry["by_model"], delta, pricing)
            flushed_pending = bool(pending)
            ledger["_pending"] = {"by_model": {}}
        elif hook_event in TURN_END_EVENTS:
            # Turn ended with nothing attributable: pending + delta is permanent
            # non-pipeline work.
            if not (usage_is_zero_by_model(pending) and usage_is_zero_by_model(delta)):
                entry = ledger.setdefault("phases", {}).setdefault(
                    "_unassigned", {"by_model": {}, "usage": zero_usage(), "cost_usd": 0.0}
                )
                merge_by_model(entry["by_model"], pending, pricing)
                merge_by_model(entry["by_model"], delta, pricing)
                flushed_pending = bool(pending)
                ledger["_pending"] = {"by_model": {}}
                target = "_unassigned"
        else:
            merge_by_model(pending, delta, pricing)

        recompute(ledger, pricing)
        ledger["updated_at"] = now_iso()
        ledger["pricing_version"] = pricing.get("version")
        if project and not ledger.get("project_name"):
            ledger["project_name"] = project
        save_json(ledger_path, ledger)

        # --- append-only audit record (only when something happened) ---
        if not usage_is_zero_by_model(delta) or flushed_pending:
            try:
                rec = {
                    "ts": now_iso(),
                    "hook": hook_event,
                    "session_id": session_id,
                    "attributed_to": target or "_pending",
                    "newly_completed": newly_completed,
                    "in_progress": in_progress,
                    "delta_by_model": delta,
                    "delta_cost_usd": round(by_model_cost(delta, pricing), 4),
                    "pending_flushed": flushed_pending,
                }
                with open(os.path.join(work, "token-usage.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception:
                pass


def usage_is_zero_by_model(by_model):
    return all(usage_is_zero(u) for u in by_model.values()) if by_model else True


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if os.environ.get("NEXUS_TOKEN_DEBUG"):
            import traceback
            try:
                os.makedirs("work", exist_ok=True)
                with open("work/token-usage.err", "a", encoding="utf-8") as f:
                    f.write(now_iso() + "\n" + traceback.format_exc() + "\n")
            except Exception:
                pass
    sys.exit(0)
