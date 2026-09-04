"""
What this does: runs an admitted test. Assigns each session to a group by hash (so
it's replayable), tallies outcomes day by day, tracks realized loss, and stops the
moment the brake, the split check, or the scoreboard says to. Emits one card per day.
What it must never do: read the hidden truth, or let realized loss pass the cap —
the brake fires first. A false stop costs one test; a false promotion bleeds forever.
Where its numbers come from: the scoreboard + policy.yaml; outcomes from the world.
"""

from __future__ import annotations

import hashlib
import sqlite3

from .clock import Clock
from .config import Policy
from .eventlog import EventLog
from .feasibility import Feasibility
from .ledger import record_decision, update_test
from .models import Proposal, TestKind, TestStatus
from .scoreboard import analyze, is_a_winner, is_harmful, split_is_healthy
from .sim.world import World, avg_order_inr

_MIN_PER_GROUP = 200          # a floor of evidence before any stop decision
_SECONDS_PER_DAY = 86_400


def group_of(session_id: str, test_id: str) -> str:
    h = hashlib.sha256(f"{session_id}{test_id}".encode()).hexdigest()
    return "treatment" if int(h, 16) / 2**256 < 0.5 else "control"


def _realized_loss(harm_ci_high: float, nt: int, avg_order: float) -> float:
    """Money we can be confident the treatment cost — the harm we're sure of at the
    brake's evidence level, valued at the order size. Using the confidence bound (not
    the raw point estimate) keeps noise from inflating loss on a zero-effect test."""
    confident_extra_rate = max(0.0, -harm_ci_high)  # >0 only once harm is credible
    return round(confident_extra_rate * nt * avg_order, 0)


def run_test(proposal: Proposal, feas: Feasibility, *, policy: Policy, world: World,
             log: EventLog, conn: sqlite3.Connection, test_id: str, clock: Clock) -> TestStatus:
    slice_ = proposal.slice
    avg_order = avg_order_inr(slice_.order_band)
    cap = feas.max_loss_inr
    arrival = int(round(feas.arrival_per_day))
    # Give the sequential test room past the fixed-horizon size; harm/winner stop early.
    max_days = int(min(feas.needed_days * 2 + 3, policy.limits.max_minutes / 1440))
    thr_pp = policy.brake.failure_rate_rise_pp
    kind = proposal.test_kind

    n = {"control": 0, "treatment": 0}
    w = {"control": 0, "treatment": 0}
    log.append("RUNNING", test_id=test_id, headline=proposal.what_changed,
               slice=slice_.label(), max_loss_inr=cap, day=0, test_kind=kind.value)

    effect = proposal.effect_to_detect_pp / 100.0
    need = feas.needed_per_group
    total = arrival * max_days
    batch = 40                # check the brake this often, so loss can't jump the cap
    loss, done, day, next_card = 0.0, 0, 0, arrival
    end = TestStatus.no_difference

    while done < total:
        for _ in range(batch):
            g = group_of(f"{test_id}-{done}", test_id)
            n[g] += 1
            if world.draw(slice_, kind, treatment=(g == "treatment")):
                w[g] += 1
            done += 1
        clock.advance(batch / arrival * _SECONDS_PER_DAY)

        pc = w["control"] / n["control"] if n["control"] else 0.0
        pt = w["treatment"] / n["treatment"] if n["treatment"] else 0.0
        seen = min(n["control"], n["treatment"])
        split_ok, _p = split_is_healthy(n["control"], n["treatment"])
        a_harm = analyze(n["control"], w["control"], n["treatment"], w["treatment"], policy.brake.harm_alpha)
        a = analyze(n["control"], w["control"], n["treatment"], w["treatment"], policy.promote.alpha)
        loss = _realized_loss(a_harm.ci_high, n["treatment"], avg_order)

        if done >= next_card:                 # one RUNNING card per simulated day
            day += 1
            next_card += arrival
            log.append("RUNNING", test_id=test_id, day=day, test_kind=kind.value,
                       sessions_control=n["control"], sessions_treatment=n["treatment"],
                       rate_control=round(pc, 4), rate_treatment=round(pt, 4),
                       realized_loss_inr=loss, max_loss_inr=cap,
                       failure_rise_pp=round((pc - pt) * 100, 2), split_ok=split_ok)

        if not split_ok:
            end = TestStatus.stopped_bad_split
            break
        if loss + avg_order > cap or is_harmful(a_harm, thr_pp, _MIN_PER_GROUP, seen):
            end = TestStatus.found_harmful
            break
        if seen >= _MIN_PER_GROUP and is_a_winner(a, policy.promote.require_range_excludes_zero):
            end = TestStatus.found_winner
            break
        # Futility: enough evidence, and the range rules out an effect as big as the
        # one we set out to find — call it no difference, don't wait for the clock.
        if seen >= need and a.ci_low > -effect and a.ci_high < effect and a.ci_low < 0 < a.ci_high:
            end = TestStatus.no_difference
            break

    return _finish(end, proposal, test_id, n, w, loss, cap, clock, log, conn, policy)


def _finish(end, proposal, test_id, n, w, loss, cap, clock, log, conn, policy) -> TestStatus:
    a = analyze(n["control"], w["control"], n["treatment"], w["treatment"], policy.promote.alpha)
    ci = f"[{a.ci_low*100:+.1f}, {a.ci_high*100:+.1f}] pp"
    sl = proposal.slice.label()
    # read correctly for whichever lever this test pulled
    is_retry = proposal.test_kind == TestKind.retry_timing
    change = "the new retry timing" if is_retry else "cards-first"
    revert_to = "the previous retry timing" if is_retry else "UPI-first"
    record_decision(conn, {"test_id": test_id, "decision": end.value, "uplift": a.uplift,
                           "ci_low": a.ci_low, "ci_high": a.ci_high, "p_value": None,
                           "reason": ci, "sim_ts": round(clock.now(), 1)})
    update_test(conn, test_id, status=end.value, realized_loss_inr=loss,
                cap_broken=int(loss > cap))

    if end == TestStatus.found_harmful:
        log.append("BRAKE_PULLED", test_id=test_id, realized_loss_inr=loss, max_loss_inr=cap,
                   sim_days=round(clock.now() / _SECONDS_PER_DAY, 1),
                   reason=f"treatment failures rose past the brake — halted; ₹{loss:,.0f} lost of ₹{cap:,.0f} allowed")
        log.append("REVERTED", test_id=test_id, note=f"settings rolled back to {revert_to}")
        log.append("LEARNED", test_id=test_id, claim=f"{change} HURTS {sl} — do not repeat")
    elif end == TestStatus.found_winner:
        log.append("KEPT", test_id=test_id, uplift_pp=round(a.uplift * 100, 1),
                   ci_low_pp=round(a.ci_low * 100, 1), ci_high_pp=round(a.ci_high * 100, 1), ci=ci,
                   note=f"{change} wins by {a.uplift*100:+.1f}pp, range {ci} excludes zero")
        log.append("LEARNED", test_id=test_id, claim=f"{change} WINS for {sl}")
    elif end == TestStatus.stopped_bad_split:
        log.append("BRAKE_PULLED", test_id=test_id, realized_loss_inr=loss, max_loss_inr=cap,
                   reason="assignment split broke — result would be meaningless, halted")
    else:
        log.append("NO_DIFFERENCE", test_id=test_id, uplift_pp=round(a.uplift * 100, 1),
                   ci_low_pp=round(a.ci_low * 100, 1), ci_high_pp=round(a.ci_high * 100, 1), ci=ci,
                   note=f"no difference found — range {ci} includes zero; not promoted")
        log.append("LEARNED", test_id=test_id, claim=f"{change} is a wash for {sl}")
    return end
