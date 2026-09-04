"""
What this does: "what happened last time" — pulls the few most relevant past tests
and learnings from the ledger, so the reasoner's next proposal is informed by
history instead of starting cold.
What it must never do: read the hidden truth, or invent history. Only the ledger.
Where its numbers come from: the SQLite ledger written by past runs.
"""

from __future__ import annotations

import sqlite3

from .models import Slice, TestKind

_VERDICT = {"FOUND_WINNER": "won", "FOUND_HARMFUL": "HURT", "NO_DIFFERENCE": "wash"}
_NOTE = {
    "won": "memory: this won here before — keep it, no need to re-spend traffic",
    "HURT": "memory: this HURT here before — not relearning it",
    "wash": "memory: this was a wash before — no point re-testing",
}


def recall_for(conn: sqlite3.Connection, slice_: Slice, kind: TestKind) -> dict:
    """What memory holds for this EXACT segment + lever, checked before we act.
    If the agent already concluded this test, it should not spend traffic to relearn it."""
    rows = conn.execute(
        "SELECT status FROM tests WHERE slice_json = ? AND test_kind = ? "
        "AND status IN ('FOUND_WINNER','FOUND_HARMFUL','NO_DIFFERENCE') "
        "ORDER BY registered_at DESC", (slice_.model_dump_json(), kind.value)
    ).fetchall()
    if not rows:
        return {"seen": 0, "verdict": None, "skip": False,
                "note": "no prior signal for this segment — testing fresh"}
    verdict = _VERDICT[rows[0]["status"]]
    return {"seen": len(rows), "verdict": verdict, "skip": True, "note": _NOTE[verdict]}


def relevant_history(conn: sqlite3.Connection, slice_: Slice, limit: int = 4) -> list[str]:
    """Plain sentences the reasoner can read: what we tried on this or a similar
    slice, and how it ended."""
    rows = conn.execute(
        "SELECT headline, status, slice_json FROM tests "
        "WHERE status IN ('FOUND_WINNER','FOUND_HARMFUL','NO_DIFFERENCE','DECLINED_TOO_SMALL','BLOCKED') "
        "ORDER BY registered_at DESC LIMIT 60"
    ).fetchall()
    notes: list[str] = []
    for r in rows:
        same_device = f'"{slice_.device.value}"' in (r["slice_json"] or "")
        tag = {"FOUND_WINNER": "won", "FOUND_HARMFUL": "HURT — do not retry",
               "NO_DIFFERENCE": "no difference", "DECLINED_TOO_SMALL": "too small to measure",
               "BLOCKED": "blocked by policy"}.get(r["status"], r["status"])
        note = f"{'(same device) ' if same_device else ''}{r['headline']} → {tag}"
        if note not in notes:
            notes.append(note)
        if len(notes) >= limit:
            break
    return notes


def learnings(conn: sqlite3.Connection, limit: int = 6) -> list[str]:
    rows = conn.execute("SELECT claim FROM learnings ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [r["claim"] for r in rows]
