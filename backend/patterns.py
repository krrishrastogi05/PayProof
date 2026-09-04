"""
What this does: demonstrates that the agent EXTRACTS the real patterns from noisy
observations. For each watched slice it runs the agent across many seeds, aggregates
the verdict the agent discovered (from its OWN decisions, never the truth), then
reveals the simulator's hidden truth as an answer key and scores the match.

This is the judge's view, not the agent's. Importing truth HERE is legitimate — it is
the answer key used only to score. The agent-side modules can never import it, and
test_truth_isolation enforces that. So "the agent found the pattern" means something.

Where its numbers come from: the agent's decisions (observed) scored against
sim/truth.py (revealed only here).
"""

from __future__ import annotations

import tempfile
from collections import Counter
from pathlib import Path

from .config import load_policy
from .clock import SimClock
from .eventlog import EventLog
from .ledger import connect
from .models import CustomerType, Device, Proposal, Slice, TestKind
from .pipeline import conduct
from .sim import truth  # the ANSWER KEY — read only to score, never by the agent
from .sim.world import World

_POLICY = load_policy()
_TMP = Path(tempfile.gettempdir()) / "thaw_patterns"
_LABEL = {"FOUND_WINNER": "WINS", "FOUND_HARMFUL": "HURT", "NO_DIFFERENCE": "wash"}

# (device, customer_type, test_kind, effect_to_detect_pp)
_WATCHED = [
    (Device.mobile, CustomerType.returning, TestKind.payment_method_order, 7),
    (Device.desktop, CustomerType.new, TestKind.payment_method_order, 5),
    (Device.mobile, CustomerType.new, TestKind.payment_method_order, 5),
    (Device.mobile, CustomerType.new, TestKind.retry_timing, 6),
]


def _clock() -> SimClock:
    return SimClock(speed=1.0, max_real_sleep=0.0)


def _prop(dev: Device, ct: CustomerType, kind: TestKind, eff: int) -> Proposal:
    metric = "recovery rate" if kind == TestKind.retry_timing else "completion"
    return Proposal(what_changed="x", test_kind=kind, metric_to_watch=metric, why="x",
                    slice=Slice(device=dev, customer_type=ct, order_band="1k-3k"),
                    traffic_share=0.10, effect_to_detect_pp=eff)


def _one(dev: Device, ct: CustomerType, kind: TestKind, eff: int, seed: int) -> tuple[str, float]:
    conn = connect(":memory:")
    log = EventLog(f"pat{seed}", _clock(), runs_dir=_TMP)
    conduct(_prop(dev, ct, kind, eff), policy=_POLICY, world=World(seed=seed),
            log=log, conn=conn, run_id="pat", clock=_clock())
    log.close()
    dec = conn.execute("SELECT decision, uplift FROM decisions LIMIT 1").fetchone()
    st = conn.execute("SELECT status FROM tests LIMIT 1").fetchone()
    conn.close()
    if dec:
        return dec[0], (dec[1] or 0.0)
    return (st[0] if st else "NONE"), 0.0


def _true_pp(dev: Device, ct: CustomerType, kind: TestKind) -> float:
    if kind == TestKind.retry_timing:
        return truth.true_retry_effect_pp(dev.value, ct.value, "1k-3k")
    return truth.true_effect_pp(dev.value, ct.value, "1k-3k")


def discover_patterns(seeds: int = 15) -> list[dict]:
    """For each slice: what verdict did the agent extract across seeds, how stable
    was it, and does it match the hidden truth?"""
    out = []
    for dev, ct, kind, eff in _WATCHED:
        verdicts, uplifts = [], []
        for s in range(seeds):
            d, u = _one(dev, ct, kind, eff, s)
            verdicts.append(_LABEL.get(d, d))
            uplifts.append(u)
        top, n = Counter(verdicts).most_common(1)[0]
        mean_pp = round(sum(uplifts) / len(uplifts) * 100, 1)
        true_pp = _true_pp(dev, ct, kind)
        disc_sign = 1 if top == "WINS" else -1 if top == "HURT" else 0
        true_sign = 1 if true_pp > 1 else -1 if true_pp < -1 else 0
        family = "retry timing" if kind == TestKind.retry_timing else "cards-first"
        out.append({
            "slice": f"{dev.value} · {ct.value}", "family": family,
            "verdict": top, "stability": f"{n}/{seeds}", "seeds": seeds,
            "discovered_pp": mean_pp, "true_pp": true_pp,
            "match": disc_sign == true_sign,
        })
    return out


def main() -> None:
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("Discovering patterns across seeds (agent's view), scoring vs truth…\n")
    for p in discover_patterns():
        ok = "OK " if p["match"] else "XX "
        print(f"  {ok}{p['slice']:<24} {p['family']:<13} "
              f"discovered {p['verdict']:<5} {p['discovered_pp']:+.1f}pp ({p['stability']})   "
              f"truth {p['true_pp']:+.1f}pp")


if __name__ == "__main__":
    main()
