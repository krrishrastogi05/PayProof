"""Feasibility — the gate nobody else has. Sample size + the spending cap."""

from backend.config import load_policy
from backend.feasibility import can_we_measure_this, days_to_run, group_size_needed
from backend.models import CustomerType, Device, Proposal, Slice, TestKind

POLICY = load_policy()


def _p(effect_pp: float, band: str = "1k-3k", device: Device = Device.mobile) -> Proposal:
    return Proposal(
        what_changed="show cards first", test_kind=TestKind.payment_method_order,
        slice=Slice(device=device, customer_type=CustomerType.returning, order_band=band),
        traffic_share=0.10, metric_to_watch="completion", why="x", effect_to_detect_pp=effect_pp,
    )


def test_a_two_point_change_needs_thousands_per_group():
    # 16 * .72 * .28 / .02^2 ~= 8064
    assert 7900 <= group_size_needed(0.72, 2.0) <= 8200


def test_a_seven_point_change_needs_only_hundreds():
    assert 600 <= group_size_needed(0.72, 7.0) <= 720


def test_declines_when_the_slice_is_too_small():
    # desktop/returning/1k-3k ~= 412/day; a 2pp test needs ~39 days > 14.
    f = can_we_measure_this(_p(2.0, device=Device.desktop), POLICY, baseline=0.72,
                            arrival_per_day=412, avg_order_inr=2000)
    assert not f.admitted and f.needed_days > POLICY.limits.max_minutes / 1440
    assert "days" in f.note


def test_admits_a_well_powered_test_and_prints_a_cap_under_budget():
    f = can_we_measure_this(_p(7.0), POLICY, baseline=0.72, arrival_per_day=727, avg_order_inr=2000)
    assert f.admitted and f.feasible
    assert 0 < f.max_loss_inr <= POLICY.limits.max_loss_per_test_inr
    assert f.needed_days <= POLICY.limits.max_minutes / 1440


def test_days_scale_with_how_fast_the_slice_arrives():
    fast = days_to_run(660, 727)
    slow = days_to_run(660, 200)
    assert slow > fast
