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


def _claim(headline: str, decision: str, uplift: float | None, reason: str) -> str:
    subject = headline.replace("Show cards first for ", "Cards-first · ").strip() or headline
    pp = round((uplift or 0) * 100, 1)
    if decision == "FOUND_WINNER":
        return f"WINS +{pp}pp · {subject} — kept {reason}"
    if decision == "FOUND_HARMFUL":
        return f"HURT {pp}pp · {subject} — reverted, won't repeat"
    return f"wash · {subject} — no measurable lift {reason}"


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
            learnings.append(_claim(t["headline"], d.get("decision", t["status"]), d.get("uplift"), d.get("reason", "")))
        elif t["status"] == "BLOCKED":
            blocked.append(t.get("rules_reason") or t["headline"])

    levers = json.loads(run.get("policy_json") or "{}")
    md = _markdown(run, levers, learnings, blocked)
    return {"run": run, "levers": levers, "learnings": learnings, "blocked": blocked, "markdown": md}


def _markdown(run: dict[str, Any], levers: dict[str, Any], learnings: list[str], blocked: list[str]) -> str:
    mode = "live · Gemini" if run.get("live") else "curated"
    days = round((run.get("sim_seconds") or 0) / 86400, 1)
    loss = f"₹{int(run.get('total_loss_inr') or 0):,}"
    verdict = (f"{run['n_tests']} tests · {run['n_winners']} kept · {run['n_harmful']} braked "
               f"({loss} exposed) · {run['n_wash']} wash · {run['n_blocked']} blocked · "
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
        *([f"- {c}" for c in learnings] or ["- (nothing concluded)"]),
    ]
    if blocked:
        lines += ["", "## Refused before any spend", *[f"- {b}" for b in blocked]]
    lines += ["", "_Every number above traces to the ledger._"]
    return "\n".join(lines)
