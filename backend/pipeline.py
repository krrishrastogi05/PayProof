"""
What this does: walks one proposal through the stages — rules, feasibility, and (if
admitted) the run — emitting one event-log card per stage and writing to the ledger.
What it must never do: compute an uplift itself (that's the scoreboard) or read truth.
Where its numbers come from: rules + feasibility + runner, all reading policy.yaml.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from .clock import Clock
from .config import Policy
from .eventlog import EventLog
from .feasibility import Feasibility, can_we_measure_this
from .ledger import record_test
from .models import Proposal, TestStatus
from .rules import is_this_allowed
from .runner import run_test
from .sim.world import World, arrival_per_day, avg_order_inr


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate(proposal: Proposal, *, policy: Policy, world: World, log: EventLog,
             conn: sqlite3.Connection, run_id: str) -> tuple[TestStatus, str, Feasibility | None]:
    """Emit cards for rules + feasibility and persist the outcome. Returns
    (status, test_id, feasibility) so an admitted test can then be run."""
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
        record_test(conn, row)
        return TestStatus.blocked, test_id, None

    baseline = world.observed_baseline(proposal.slice)
    arrival = arrival_per_day(proposal.slice)
    feas = can_we_measure_this(proposal, policy, baseline, arrival, avg_order_inr(proposal.slice.order_band))
    row.update(needed_per_group=feas.needed_per_group, arrival_rate=arrival,
               feasible=int(feas.feasible), feasibility_note=feas.note, max_loss_inr=feas.max_loss_inr)

    if not feas.admitted:
        log.append("TOO_SMALL", test_id=test_id, note=feas.note,
                   needed_per_group=feas.needed_per_group, needed_days=feas.needed_days)
        row["status"] = TestStatus.declined_too_small.value
        record_test(conn, row)
        return TestStatus.declined_too_small, test_id, feas

    log.append("CAP_SET", test_id=test_id, max_loss_inr=feas.max_loss_inr, note=feas.note)
    row["status"] = TestStatus.admitted.value
    record_test(conn, row)
    return TestStatus.admitted, test_id, feas


def conduct(proposal: Proposal, *, policy: Policy, world: World, log: EventLog,
            conn: sqlite3.Connection, run_id: str, clock: Clock) -> TestStatus:
    """Evaluate, and run it if it's admitted. The whole life of one proposal."""
    status, test_id, feas = evaluate(proposal, policy=policy, world=world, log=log, conn=conn, run_id=run_id)
    if status is TestStatus.admitted and feas is not None:
        return run_test(proposal, feas, policy=policy, world=world, log=log,
                        conn=conn, test_id=test_id, clock=clock)
    return status
