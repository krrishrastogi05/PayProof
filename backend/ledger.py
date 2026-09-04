"""
What this does: the record. SQLite tables for every test, what it risked, what it
lost, what it learned. Any decision can be re-derived from these rows.
What it must never do: store opinions or model output as fact. Every number in
`decisions` comes from the scoreboard, never from Gemini.
Where its numbers come from: the pipeline stages write here; nothing is typed by hand.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "thaw.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tests (
  id TEXT PRIMARY KEY, run_id TEXT, layer_id TEXT, headline TEXT,
  test_kind TEXT, slice_json TEXT, status TEXT, traffic_share REAL,
  control_json TEXT, treatment_json TEXT,
  needed_per_group INTEGER, arrival_rate REAL, feasible INTEGER, feasibility_note TEXT,
  max_loss_inr REAL, realized_loss_inr REAL, cap_broken INTEGER,
  proposed_by TEXT, rules_verdict TEXT, rules_reason TEXT,
  registered_at TEXT, started_at TEXT, ended_at TEXT
);
CREATE TABLE IF NOT EXISTS decisions (
  test_id TEXT, decision TEXT, uplift REAL, ci_low REAL, ci_high REAL,
  p_value REAL, reason TEXT, sim_ts REAL
);
CREATE TABLE IF NOT EXISTS learnings (
  id INTEGER PRIMARY KEY AUTOINCREMENT, test_id TEXT, claim TEXT,
  slice_json TEXT, confidence_from_stats REAL
);
CREATE TABLE IF NOT EXISTS brake_events (
  test_id TEXT, rule TEXT, threshold REAL, observed REAL, action TEXT, sim_ts REAL
);
CREATE TABLE IF NOT EXISTS policy_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, yaml_text TEXT
);
-- the run registry: one archived row per invocation, so runs persist and compare
-- even after the ledger's per-test rows are overwritten by the next same-seed run.
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, created_at TEXT,
  seed INTEGER, live INTEGER, policy_json TEXT,
  n_tests INTEGER, n_winners INTEGER, n_harmful INTEGER, n_wash INTEGER,
  n_blocked INTEGER, n_too_small INTEGER, n_learnings INTEGER,
  total_loss_inr REAL, cap_broken INTEGER, sim_seconds REAL
);
"""


def connect(path: str | Path = DB_PATH) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def record_test(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    cols = ", ".join(row)
    marks = ", ".join(f":{c}" for c in row)
    conn.execute(f"INSERT OR REPLACE INTO tests ({cols}) VALUES ({marks})", row)
    conn.commit()


def set_status(conn: sqlite3.Connection, test_id: str, status: str) -> None:
    conn.execute("UPDATE tests SET status = ? WHERE id = ?", (status, test_id))
    conn.commit()


def update_test(conn: sqlite3.Connection, test_id: str, **fields: Any) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    conn.execute(f"UPDATE tests SET {sets} WHERE id = :id", {**fields, "id": test_id})
    conn.commit()


def record_decision(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    cols = ", ".join(row)
    marks = ", ".join(f":{c}" for c in row)
    conn.execute(f"INSERT INTO decisions ({cols}) VALUES ({marks})", row)
    conn.commit()


def all_tests(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT * FROM tests ORDER BY registered_at")]


def clear_run(conn: sqlite3.Connection, run_id: str) -> None:
    """Wipe a run_id's per-test rows before it re-runs, so the tests/decisions
    tables hold exactly the latest run (the registry keeps the historical summary)."""
    ids = [r[0] for r in conn.execute("SELECT id FROM tests WHERE run_id = ?", (run_id,))]
    if ids:
        marks = ",".join("?" * len(ids))
        conn.execute(f"DELETE FROM decisions WHERE test_id IN ({marks})", ids)
        conn.execute(f"DELETE FROM learnings WHERE test_id IN ({marks})", ids)
    conn.execute("DELETE FROM tests WHERE run_id = ?", (run_id,))
    conn.commit()


def cap_broken_count(conn: sqlite3.Connection) -> int:
    """The headline safety claim: this must be 0 across every run and seed."""
    return conn.execute("SELECT COUNT(*) FROM tests WHERE cap_broken = 1").fetchone()[0]


# --- run registry -------------------------------------------------------------
_STATUS_COUNTS = {
    "n_winners": "FOUND_WINNER", "n_harmful": "FOUND_HARMFUL", "n_wash": "NO_DIFFERENCE",
    "n_blocked": "BLOCKED", "n_too_small": "DECLINED_TOO_SMALL",
}


def summarize_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    """Roll this run's per-test rows up into the metrics a run is judged on."""
    rows = [dict(r) for r in conn.execute("SELECT * FROM tests WHERE run_id = ?", (run_id,))]
    counts = {k: sum(1 for r in rows if r["status"] == v) for k, v in _STATUS_COUNTS.items()}
    return {
        "n_tests": len(rows), **counts,
        "n_learnings": counts["n_winners"] + counts["n_harmful"] + counts["n_wash"],
        "total_loss_inr": round(sum(r["realized_loss_inr"] or 0 for r in rows), 0),
        "cap_broken": sum(int(r["cap_broken"] or 0) for r in rows),
    }


def record_run(conn: sqlite3.Connection, row: dict[str, Any]) -> int:
    cols = ", ".join(row)
    marks = ", ".join(f":{c}" for c in row)
    cur = conn.execute(f"INSERT INTO runs ({cols}) VALUES ({marks})", row)
    conn.commit()
    return int(cur.lastrowid or 0)


def list_runs(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))]


def get_run(conn: sqlite3.Connection, run_pk: int) -> dict[str, Any] | None:
    r = conn.execute("SELECT * FROM runs WHERE id = ?", (run_pk,)).fetchone()
    return dict(r) if r else None
