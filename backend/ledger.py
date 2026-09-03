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


def record_decision(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    cols = ", ".join(row)
    marks = ", ".join(f":{c}" for c in row)
    conn.execute(f"INSERT INTO decisions ({cols}) VALUES ({marks})", row)
    conn.commit()


def all_tests(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT * FROM tests ORDER BY registered_at")]


def cap_broken_count(conn: sqlite3.Connection) -> int:
    """The headline safety claim: this must be 0 across every run and seed."""
    return conn.execute("SELECT COUNT(*) FROM tests WHERE cap_broken = 1").fetchone()[0]
