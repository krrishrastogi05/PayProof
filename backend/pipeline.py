"""
What this does: walks one proposal through the authority stages — rules, then
feasibility — emitting one event-log card per stage and writing the test row to
the ledger. This is the spine beats 3 and 4 ride on.
What it must never do: run the test or compute an uplift (that's runner/scoreboard).
Where its numbers come from: rules + feasibility, which read policy.yaml.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from .config import Policy
from .eventlog import EventLog
from .feasibility import can_we_measure_this
from .models import Proposal, TestStatus
from .rules import is_this_allowed
from .sim.world import World, arrival_per_day, avg_order_inr


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate(proposal: Proposal, *, policy: Policy, world: World,
             log: EventLog, conn: sqlite3.Connection, run_id: str) -> TestStatus:
    """Emit the cards for one proposal and persist its outcome. Returns the end state."""
    test_id = uuid.uuid4().hex[:8]
    log.append("PROPOSED", test_id=test_id, headline=proposal.what_changed,
               slice=proposal.slice.label(), traffic_share=proposal.traffic_share, why=proposal.why)

    row: dict = {
        "id": test_id, "run_id": run_id, "layer_id": proposal.test_kind.value,
        "headline": proposal.what_changed, "test_kind": proposal.test_kind.value,
        "slice_json": proposal.slice.model_dump_json(), "traffic_share": proposal.traffic_share,
        "proposed_by": "hardcoded", "registered_at": _now(),
        "realized_loss_inr": 0.0, "cap_broken": 0,
    }

    verdict = is_this_allowed(proposal, policy)
    row["rules_verdict"] = "allowed" if verdict.allowed else "blocked"
    row["rules_reason"] = verdict.reason
    if not verdict.allowed:
        log.append("BLOCKED", test_id=test_id, reason=verdict.reason)
        row["status"] = TestStatus.blocked.value
        _save(conn, row)
        return TestStatus.blocked

    baseline = world.observed_baseline(proposal.slice)
    arrival = arrival_per_day(proposal.slice)
    feas = can_we_measure_this(proposal, policy, baseline, arrival, avg_order_inr(proposal.slice.order_band))
    row.update(needed_per_group=feas.needed_per_group, arrival_rate=arrival,
               feasible=int(feas.feasible), feasibility_note=feas.note, max_loss_inr=feas.max_loss_inr)

    if not feas.admitted:
        log.append("TOO_SMALL", test_id=test_id, note=feas.note,
                   needed_per_group=feas.needed_per_group, needed_days=feas.needed_days)
        row["status"] = TestStatus.declined_too_small.value
        _save(conn, row)
        return TestStatus.declined_too_small

    log.append("CAP_SET", test_id=test_id, max_loss_inr=feas.max_loss_inr, note=feas.note)
    row["status"] = TestStatus.admitted.value
    _save(conn, row)
    return TestStatus.admitted


def _save(conn: sqlite3.Connection, row: dict) -> None:
    from .ledger import record_test
    record_test(conn, row)
