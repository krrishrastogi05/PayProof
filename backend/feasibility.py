"""
What this does: answers two questions before a test may run — "can we even measure
this?" (sample size vs how fast the slice arrives) and "most we can lose?" (the
spending cap, written to the ledger before anything starts).
What it must never do: call the model, or look at the hidden truth. It only does
arithmetic on observable numbers.
Where its numbers come from: baseline/arrival/avg-order are observed and passed in;
the limits and the worst tolerated failure rise come from policy.yaml.
"""

from __future__ import annotations

import math
from pydantic import BaseModel

from .config import Policy
from .models import Proposal


class Feasibility(BaseModel):
    feasible: bool
    admitted: bool
    needed_per_group: int
    arrival_per_day: float
    needed_days: float
    max_days: float
    max_loss_inr: float
    within_budget: bool
    note: str


def group_size_needed(baseline: float, effect_pp: float) -> int:
    """per_group ~= 16 * p(1-p) / effect^2. The 16 bakes in a=0.05, power=0.80."""
    effect = effect_pp / 100.0
    if effect <= 0:
        return 10**9
    return math.ceil(16 * baseline * (1 - baseline) / (effect * effect))


def days_to_run(per_group: int, arrival_per_day: float) -> float:
    """Both groups draw from the slice 50/50, so we need 2 * per_group sessions."""
    if arrival_per_day <= 0:
        return float("inf")
    return round(2 * per_group / arrival_per_day, 1)


def most_we_can_lose(arrival_per_day: float, days: float, baseline: float,
                     avg_order_inr: float, worst_drop: float) -> float:
    """Conservative: assume the worst tolerated failure rise across all enrolled
    traffic for the whole run. The brake fires long before this in practice, so
    realized loss is always well under it — that gap is the safety claim."""
    enrolled = arrival_per_day * days
    return round(enrolled * baseline * avg_order_inr * worst_drop, 0)


def can_we_measure_this(proposal: Proposal, policy: Policy, baseline: float,
                        arrival_per_day: float, avg_order_inr: float) -> Feasibility:
    per_group = group_size_needed(baseline, proposal.effect_to_detect_pp)
    days = days_to_run(per_group, arrival_per_day)
    max_days = policy.limits.max_minutes / 1440.0
    feasible = days <= max_days

    worst_drop = policy.brake.failure_rate_rise_pp / 100.0
    cap = most_we_can_lose(arrival_per_day, days if feasible else max_days,
                           baseline, avg_order_inr, worst_drop)
    within_budget = cap <= policy.limits.max_loss_per_test_inr

    if not feasible:
        note = (f"this slice gets {arrival_per_day:.0f} sessions/day; telling a "
                f"{proposal.effect_to_detect_pp:.0f}-point change apart needs ~{per_group:,} per group "
                f"— that's {days:.0f} days, over the {max_days:.0f}-day limit")
    elif not within_budget:
        note = f"the cap ₹{cap:,.0f} exceeds the ₹{policy.limits.max_loss_per_test_inr:,} per-test budget"
    else:
        note = (f"~{per_group:,} per group at {arrival_per_day:.0f}/day = {days:.0f} days; "
                f"most this can lose before the brake fires: ₹{cap:,.0f}")

    return Feasibility(
        feasible=feasible, admitted=feasible and within_budget,
        needed_per_group=per_group, arrival_per_day=arrival_per_day,
        needed_days=days, max_days=round(max_days, 1),
        max_loss_inr=cap, within_budget=within_budget, note=note,
    )
