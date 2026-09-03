"""Runner + scoreboard — the safety claims, checked across many seeds."""

from backend.cli import _proposals
from backend.clock import SimClock
from backend.config import load_policy
from backend.eventlog import EventLog
from backend.ledger import cap_broken_count, connect
from backend.models import CustomerType, Device, Proposal, Slice, TestKind, TestStatus
from backend.pipeline import conduct
from backend.sim.world import World

POLICY = load_policy()


def _fast_clock():
    return SimClock(speed=1.0, max_real_sleep=0.0)  # never actually sleep in tests


def _run_all(seed, tmp_path):
    conn = connect(":memory:")
    log = EventLog(f"t{seed}", _fast_clock(), runs_dir=tmp_path)
    world = World(seed=seed)
    for p in _proposals():
        conduct(p, policy=POLICY, world=world, log=log, conn=conn, run_id=f"t{seed}", clock=_fast_clock())
    log.close()
    return conn


def _run_one(proposal, seed, tmp_path):
    conn = connect(":memory:")
    log = EventLog(f"o{seed}", _fast_clock(), runs_dir=tmp_path)
    status = conduct(proposal, policy=POLICY, world=World(seed=seed), log=log,
                     conn=conn, run_id=f"o{seed}", clock=_fast_clock())
    log.close()
    return status, conn


def test_cap_is_never_exceeded_across_20_seeds(tmp_path):
    for seed in range(20):
        conn = _run_all(seed, tmp_path)
        assert cap_broken_count(conn) == 0, f"cap broken on seed {seed}"


def _honesty():
    s = Slice(device=Device.mobile, customer_type=CustomerType.new, order_band="1k-3k")
    return Proposal(what_changed="cards first, mobile new", test_kind=TestKind.payment_method_order,
                    slice=s, traffic_share=0.10, metric_to_watch="completion", why="x", effect_to_detect_pp=5)


def test_the_honesty_test_never_promotes_a_winner(tmp_path):
    # Both options are secretly identical — an agent that finds a winner here is broken.
    for seed in range(12):
        status, _ = _run_one(_honesty(), seed, tmp_path)
        assert status is not TestStatus.found_winner, f"promoted a non-existent win on seed {seed}"


def _harmful():
    s = Slice(device=Device.desktop, customer_type=CustomerType.new, order_band="1k-3k")
    return Proposal(what_changed="cards first, desktop new", test_kind=TestKind.payment_method_order,
                    slice=s, traffic_share=0.10, metric_to_watch="completion", why="x", effect_to_detect_pp=5)


def test_a_harmful_test_is_stopped_by_the_brake_under_cap(tmp_path):
    status, conn = _run_one(_harmful(), 42, tmp_path)
    assert status is TestStatus.found_harmful
    row = conn.execute("SELECT realized_loss_inr, max_loss_inr, cap_broken FROM tests").fetchone()
    assert row[0] <= row[1] and row[2] == 0


def _winner():
    s = Slice(device=Device.mobile, customer_type=CustomerType.returning, order_band="1k-3k")
    return Proposal(what_changed="cards first, mobile returning", test_kind=TestKind.payment_method_order,
                    slice=s, traffic_share=0.10, metric_to_watch="completion", why="x", effect_to_detect_pp=7)


def test_a_real_win_is_promoted_on_most_seeds(tmp_path):
    kept = sum(_run_one(_winner(), s, tmp_path)[0] is TestStatus.found_winner for s in range(12))
    assert kept >= 9, f"only promoted the real win {kept}/12 times"
