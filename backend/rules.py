"""
What this does: decides whether a proposal is *allowed*. Reads policy.yaml and
returns yes, or no-with-a-reason. This is the file with the most tests.
What it must never do: guess, compute a statistic, or ask the model. Allowed is not
the same as sensible — feasibility.py judges whether it's worth running.
Where its numbers come from: policy.yaml, every one of them.
"""

from __future__ import annotations

from pydantic import BaseModel

from .config import Policy
from .models import Proposal

# INR bounds for each order band, so we can check a slice sits inside the tested window.
_BAND_RANGE_INR: dict[str, tuple[int, int]] = {
    "<1k": (0, 1000),
    "1k-3k": (1000, 3000),
    "3k-5k": (3000, 5000),
    ">5k": (5000, 10_000_000),
}


class Verdict(BaseModel):
    allowed: bool
    reason: str


def is_this_allowed(proposal: Proposal, policy: Policy) -> Verdict:
    """First failing check wins, so the reason is always the real blocker."""

    if proposal.test_kind.value not in policy.allowed_tests:
        return Verdict(allowed=False, reason=f"{proposal.test_kind.value} is not an allowed kind of test")

    forbidden = [t for t in proposal.touches if t in policy.never]
    if forbidden:
        return Verdict(allowed=False, reason=f"would {forbidden[0].replace('_', ' ')} — never allowed")

    if proposal.traffic_share > policy.limits.max_traffic_share:
        asked = round(proposal.traffic_share * 100)
        ceiling = round(policy.limits.max_traffic_share * 100)
        return Verdict(allowed=False, reason=f"asked for {asked}% of traffic; ceiling is {ceiling}%")

    lo, hi = _BAND_RANGE_INR.get(proposal.slice.order_band, (0, 0))
    if lo < policy.only_include_orders.min_inr or hi > policy.only_include_orders.max_inr:
        return Verdict(
            allowed=False,
            reason=f"orders {proposal.slice.order_band} fall outside the tested window "
                   f"₹{policy.only_include_orders.min_inr}–₹{policy.only_include_orders.max_inr}",
        )

    # Structural guarantees: a test must be stoppable. The brake block must exist.
    if policy.brake.harm_alpha <= 0:
        return Verdict(allowed=False, reason="no stop rule defined — a test must be haltable")

    return Verdict(allowed=True, reason="within policy")
