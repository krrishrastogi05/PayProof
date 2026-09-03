"""Rules engine — the highest-coverage file in the repo. One test per boundary."""

import pytest

from backend.config import load_policy
from backend.models import CustomerType, Device, Proposal, Slice, TestKind

POLICY = load_policy()


def _p(**over) -> Proposal:
    base = dict(
        what_changed="show cards first",
        test_kind=TestKind.payment_method_order,
        slice=Slice(device=Device.mobile, customer_type=CustomerType.returning, order_band="1k-3k"),
        traffic_share=0.10, metric_to_watch="completion", why="because",
    )
    base.update(over)
    return Proposal(**base)


def _verdict(p: Proposal):
    from backend.rules import is_this_allowed
    return is_this_allowed(p, POLICY)


def test_allows_a_test_within_the_traffic_ceiling():
    assert _verdict(_p(traffic_share=0.10)).allowed


def test_blocks_a_test_that_asks_for_too_much_traffic():
    v = _verdict(_p(traffic_share=0.25))
    assert not v.allowed and "25%" in v.reason and "10%" in v.reason


def test_blocks_orders_outside_the_tested_window():
    s = Slice(device=Device.mobile, customer_type=CustomerType.returning, order_band=">5k")
    v = _verdict(_p(slice=s))
    assert not v.allowed and "window" in v.reason


@pytest.mark.parametrize("action", load_policy().never)
def test_blocks_every_prohibited_action(action):
    # PRD §14: one test per prohibited action. A proposal that would do it is blocked.
    v = _verdict(_p(touches=[action]))
    assert not v.allowed and action.replace("_", " ") in v.reason
