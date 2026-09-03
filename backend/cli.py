"""
What this does: a terminal demo of the authority spine. Runs a handful of
hardcoded proposals through rules + feasibility, then renders the event log as a
card stream — exactly what the web UI will do, so the log stays the single source.
What it must never do: print anything the event log didn't record.
Where its numbers come from: the pipeline, via the ledger and policy.yaml.

    python -m backend.cli            # run + render
    python -m backend.cli replay runs/<id>.jsonl
"""

from __future__ import annotations

import sys

from .clock import SimClock
from .config import load_policy
from .eventlog import EventLog, read_log
from .ledger import connect
from .models import CustomerType, Device, Proposal, Slice, TestKind
from .pipeline import evaluate
from .sim.world import World

C = {"grey": "\033[90m", "red": "\033[91m", "amber": "\033[93m", "blue": "\033[94m",
     "green": "\033[92m", "violet": "\033[95m", "bold": "\033[1m", "off": "\033[0m"}

CARD = {
    "PROPOSED": ("✎", "violet", "PROPOSED"),
    "BLOCKED": ("✕", "red", "BLOCKED"),
    "TOO_SMALL": ("⊘", "amber", "TOO SMALL TO MEASURE"),
    "CAP_SET": ("₹", "blue", "CAP SET · ADMITTED"),
}


def _proposals() -> list[Proposal]:
    good = Slice(device=Device.mobile, customer_type=CustomerType.returning, order_band="1k-3k")
    small = Slice(device=Device.desktop, customer_type=CustomerType.returning, order_band="1k-3k")
    tail = Slice(device=Device.mobile, customer_type=CustomerType.returning, order_band=">5k")
    return [
        Proposal(what_changed="Show cards first for mobile returning buyers (₹1k–3k)",
                 test_kind=TestKind.payment_method_order, slice=good, traffic_share=0.25,
                 metric_to_watch="checkout completion", why="completion in this slice fell 8pp",
                 effect_to_detect_pp=7),
        Proposal(what_changed="Show cards first for mobile returning buyers (₹1k–3k)",
                 test_kind=TestKind.payment_method_order, slice=good, traffic_share=0.10,
                 metric_to_watch="checkout completion", why="same idea, within the ceiling",
                 effect_to_detect_pp=7),
        Proposal(what_changed="Show cards first for desktop returning buyers (₹1k–3k)",
                 test_kind=TestKind.payment_method_order, slice=small, traffic_share=0.10,
                 metric_to_watch="checkout completion", why="small wobble, want to detect 2pp",
                 effect_to_detect_pp=2),
        Proposal(what_changed="Retry without re-authenticating to speed recovery",
                 test_kind=TestKind.retry_timing, slice=good, traffic_share=0.10,
                 metric_to_watch="recovery rate", why="faster retries", touches=["skip_authentication"]),
        Proposal(what_changed="Show cards first for high-value orders (>₹5k)",
                 test_kind=TestKind.payment_method_order, slice=tail, traffic_share=0.10,
                 metric_to_watch="checkout completion", why="chase the big baskets", effect_to_detect_pp=5),
    ]


def run_demo(seed: int = 42, speed: float = 10_000.0) -> str:
    policy = load_policy()
    clock = SimClock(speed=speed)
    run_id = f"run_{seed:03d}"
    from .eventlog import RUNS_DIR
    (RUNS_DIR / f"{run_id}.jsonl").unlink(missing_ok=True)  # start clean so replays are exact
    log = EventLog(run_id, clock)
    conn = connect()
    world = World(seed=seed)
    log.append("WATCHING", slice="mobile · returning · 1k-3k",
               note="completion 72.1% → 63.7% over 14 days · set 19 months ago, never re-tested")
    for p in _proposals():
        clock.advance(3600)  # an hour of sim time between proposals
        evaluate(p, policy=policy, world=world, log=log, conn=conn, run_id=run_id)
    log.close()
    conn.close()
    return str(log.path)


def render(path: str) -> None:
    print(f"\n{C['bold']}THAW{C['off']}  Acme Electronics   mode: CANARY   ● watching\n")
    for e in read_log(path):
        kind = e["kind"]
        if kind == "WATCHING":
            print(f"{C['grey']}● WATCHING{C['off']}  {e['slice']}\n  {C['grey']}{e['note']}{C['off']}\n")
            continue
        if kind not in CARD:
            continue
        sym, color, title = CARD[kind]
        print(f"{C[color]}{C['bold']}{sym} {title}{C['off']}")
        if kind == "PROPOSED":
            print(f"  {e['headline']}  ·  {e['slice']}  ·  asked {int(e['traffic_share']*100)}% of traffic")
        elif kind == "BLOCKED":
            print(f"  {C['red']}{e['reason']}{C['off']}")
        elif kind == "TOO_SMALL":
            print(f"  {e['note']}")
        elif kind == "CAP_SET":
            print(f"  {e['note']}")
        print()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    except Exception:
        pass
    if len(sys.argv) >= 3 and sys.argv[1] == "replay":
        render(sys.argv[2])
        return
    path = run_demo()
    render(path)
    print(f"{C['grey']}log: {path}{C['off']}")


if __name__ == "__main__":
    main()
