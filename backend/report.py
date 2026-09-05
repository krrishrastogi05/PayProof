"""
What this does: turns an archived run into a human-readable report — the verdict,
the levers it ran under, what it learned, what it refused. Pure formatting over the
ledger; it invents nothing.
Where its numbers come from: the runs registry + the tests/decisions tables.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .ledger import get_run


def _segment(slice_json: str) -> str:
    """Turn a slice into a plain phrase: 'returning mobile shoppers'."""
    try:
        s = json.loads(slice_json or "{}")
    except Exception:
        return "this group of shoppers"
    seg = f"{s.get('customer_type', '')} {s.get('device', '')} shoppers".strip()
    return seg or "this group of shoppers"


def humanize(test_kind: str, slice_json: str, decision: str, uplift: float | None) -> tuple[str, str]:
    """A plain-English learning + a verdict tag ('win' / 'harm' / 'wash') for colour.
    Written so a non-analyst reads it as a sentence, not a stat line."""
    seg = _segment(slice_json)
    pts = abs(round((uplift or 0) * 100))
    if test_kind == "retry_timing":
        change, metric = "waiting longer before retrying a failed charge", "payment recovery"
    else:
        change, metric = "showing cards before UPI", "checkout completion"
    if decision == "FOUND_WINNER":
        return (f"For {seg}, {change} lifted {metric} by about {pts} points — so we kept it on.", "win")
    if decision == "FOUND_HARMFUL":
        return (f"For {seg}, {change} pushed {metric} down by about {pts} points — so we reverted it and won't try it again.", "harm")
    return (f"For {seg}, {change} made no real difference either way — so we left the setting as it was.", "wash")


def build_report(conn: sqlite3.Connection, run_pk: int) -> dict[str, Any] | None:
    run = get_run(conn, run_pk)
    if not run:
        return None
    tests = [dict(r) for r in conn.execute("SELECT * FROM tests WHERE run_id = ?", (run["run_id"],))]
    dec = {d["test_id"]: dict(d) for d in conn.execute("SELECT * FROM decisions ORDER BY rowid")}

    learnings, blocked = [], []
    for t in tests:
        if t["status"] in ("FOUND_WINNER", "FOUND_HARMFUL", "NO_DIFFERENCE"):
            d = dec.get(t["id"], {})
            claim, verdict = humanize(t.get("test_kind", ""), t.get("slice_json", ""),
                                      d.get("decision", t["status"]), d.get("uplift"))
            learnings.append({"claim": claim, "verdict": verdict})
        elif t["status"] == "BLOCKED":
            blocked.append(t.get("rules_reason") or t["headline"])

    levers = json.loads(run.get("policy_json") or "{}")
    md = _markdown(run, levers, learnings, blocked)
    return {"run": run, "levers": levers, "learnings": learnings, "blocked": blocked, "markdown": md}


def _markdown(run: dict[str, Any], levers: dict[str, Any], learnings: list[dict], blocked: list[str]) -> str:
    mode = "live · Gemini" if run.get("live") else "curated"
    days = round((run.get("sim_seconds") or 0) / 86400, 1)
    loss = f"₹{int(run.get('total_loss_inr') or 0):,}"
    verdict = (f"{run['n_tests']} experiments · {run['n_winners']} kept · {run['n_harmful']} stopped by the brake "
               f"({loss} at risk) · {run['n_wash']} no change · {run['n_blocked']} blocked · "
               f"{run['cap_broken']} cap breaches")
    lev = " · ".join(f"{k} {v}" for k, v in levers.items())
    lines = [
        f"# PayProof run report · {run['run_id']} · seed {run['seed']}",
        f"{run['created_at']} · {mode} · sim horizon {days}d",
        "",
        "## Verdict",
        verdict,
        "",
        "## Policy levers",
        lev or "(defaults)",
        "",
        "## What the agent learned",
        *([f"- {c['claim']}" for c in learnings] or ["- (nothing concluded yet)"]),
    ]
    if blocked:
        lines += ["", "## Refused before any spend", *[f"- {b}" for b in blocked]]
    lines += ["", "_Every number above traces to the ledger._"]
    return "\n".join(lines)
