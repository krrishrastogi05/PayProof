"""
What this does: the evidence runs behind the README's claims — the false-positive
inflation from peeking, the cap-violation count, and cold-vs-experienced. Numbers,
not adjectives.
What it must never do: read the hidden truth (except via the simulator, as any run
does), or cherry-pick a lucky seed — everything is averaged over many seeds.
Where its numbers come from: the scoreboard + runner, over fixed seeds.

    python -m backend.evidence
"""

from __future__ import annotations

import math
import random
import tempfile
from pathlib import Path

from .clock import SimClock
from .config import load_policy
from .eventlog import EventLog
from .ledger import cap_broken_count, connect
from .models import CustomerType, Device, Proposal, Slice, TestKind
from .pipeline import conduct
from .scoreboard import analyze
from .sim.world import World

POLICY = load_policy()
_TMP = Path(tempfile.gettempdir()) / "thaw_evidence"


def _clock():
    return SimClock(speed=1.0, max_real_sleep=0.0)


# ---- false-positive inflation: peeking at a fixed-horizon p-value vs the sequential test ----

def _p_two_sided(delta: float, se: float) -> float:
    if se <= 0:
        return 1.0
    return math.erfc(abs(delta / se) / math.sqrt(2))


def false_positive_inflation(trials: int = 400, n_max: int = 4000, batch: int = 50) -> tuple[float, float]:
    """Both groups are drawn from the SAME rate (no real difference). How often does
    each rule declare a 'winner' if we look after every batch?"""
    naive_hits = seq_hits = 0
    for t in range(trials):
        rng = random.Random(10_000 + t)
        nc = nt = wc = wt = 0
        naive = seq = False
        while nc < n_max:
            for _ in range(batch):
                if rng.random() < 0.72:
                    wc += 1
                nc += 1
                if rng.random() < 0.72:
                    wt += 1
                nt += 1
            pc, pt = wc / nc, wt / nt
            se = math.sqrt(pc * (1 - pc) / nc + pt * (1 - pt) / nt)
            if not naive and _p_two_sided(pt - pc, se) < 0.05:
                naive = True
            if not seq and analyze(nc, wc, nt, wt, 0.05).excludes_zero:
                seq = True
            if naive and seq:
                break
        naive_hits += naive
        seq_hits += seq
    return naive_hits / trials, seq_hits / trials


# ---- cap violations across seeds ----

_CURATED = [
    (Device.mobile, CustomerType.returning, 0.10, 7),
    (Device.desktop, CustomerType.new, 0.10, 5),
    (Device.mobile, CustomerType.new, 0.10, 5),
    (Device.desktop, CustomerType.returning, 0.10, 2),
]


def _proposal(dev, ct, share, eff):
    return Proposal(what_changed="cards first", test_kind=TestKind.payment_method_order,
                    slice=Slice(device=dev, customer_type=ct, order_band="1k-3k"),
                    traffic_share=share, metric_to_watch="completion", why="x", effect_to_detect_pp=eff)


def cap_violations(seeds: int = 20) -> tuple[int, int]:
    tests = broken = 0
    for seed in range(seeds):
        conn = connect(":memory:")
        log = EventLog(f"ev{seed}", _clock(), runs_dir=_TMP)
        for dev, ct, share, eff in _CURATED:
            conduct(_proposal(dev, ct, share, eff), policy=POLICY, world=World(seed=seed),
                    log=log, conn=conn, run_id="ev", clock=_clock())
        log.close()
        tests += conn.execute("SELECT COUNT(*) FROM tests").fetchone()[0]
        broken += cap_broken_count(conn)
    return tests, broken


# ---- cold vs experienced: does reading the ledger save tests and money? ----

def cold_vs_experienced(seeds: int = 20) -> dict:
    """Cold: try every candidate slice, including one that turns out harmful.
    Experienced: the ledger already says which slices HURT or are a wash, so the
    agent skips them and goes straight to the real win."""
    harm = (Device.desktop, CustomerType.new, 5)
    wash = (Device.mobile, CustomerType.new, 5)
    win = (Device.mobile, CustomerType.returning, 7)

    def one(seed, experienced):
        conn = connect(":memory:")
        log = EventLog(f"cw{seed}", _clock(), runs_dir=_TMP)
        candidates = [win] if experienced else [harm, wash, win]  # experience skips known dead ends
        for dev, ct, eff in candidates:
            conduct(_proposal(dev, ct, 0.10, eff), policy=POLICY, world=World(seed=seed),
                    log=log, conn=conn, run_id="cw", clock=_clock())
        log.close()
        tests = conn.execute("SELECT COUNT(*) FROM tests").fetchone()[0]
        loss = conn.execute("SELECT COALESCE(SUM(realized_loss_inr),0) FROM tests").fetchone()[0]
        return tests, loss

    cold = [one(s, False) for s in range(seeds)]
    exp = [one(s, True) for s in range(seeds)]
    return {
        "cold_tests": sum(t for t, _ in cold) / seeds,
        "cold_loss": sum(l for _, l in cold) / seeds,
        "experienced_tests": sum(t for t, _ in exp) / seeds,
        "experienced_loss": sum(l for _, l in exp) / seeds,
    }


def main() -> None:
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("Measuring… (a few seconds)\n")
    naive, seq = false_positive_inflation()
    tests, broken = cap_violations()
    cw = cold_vs_experienced()
    print("FALSE-POSITIVE INFLATION (both options identical, we peek after every batch)")
    print(f"  naive re-checking declares a winner on {naive*100:.1f}% of runs")
    print(f"  the sequential test:                    {seq*100:.1f}%\n")
    print("SPENDING CAP")
    print(f"  across {tests} tests over 20 seeds, cap_broken = {broken}\n")
    print("COLD vs EXPERIENCED (mean over 20 seeds)")
    print(f"  cold:        {cw['cold_tests']:.1f} tests · ₹{cw['cold_loss']:,.0f} lost")
    print(f"  experienced: {cw['experienced_tests']:.1f} tests · ₹{cw['experienced_loss']:,.0f} lost")


if __name__ == "__main__":
    main()
