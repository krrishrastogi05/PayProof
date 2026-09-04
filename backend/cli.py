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

import json
import sqlite3
import sys
from datetime import datetime, timezone

from .clock import Clock, SimClock
from .config import Policy, load_policy
from .eventlog import EventLog, read_log
from .ledger import clear_run, connect, record_run, summarize_run
from .models import CustomerType, Device, Proposal, Slice, TestKind
from .pipeline import conduct, reason_and_conduct
from .sim.world import World
from .watcher import flagged_slices

C = {"grey": "\033[90m", "red": "\033[91m", "amber": "\033[93m", "blue": "\033[94m",
     "green": "\033[92m", "violet": "\033[95m", "cyan": "\033[96m", "bold": "\033[1m", "off": "\033[0m"}

CARD = {
    "THINKING": ("✦", "violet", "THINKING"),
    "PROPOSED": ("✎", "violet", "PROPOSED"),
    "BLOCKED": ("✕", "red", "BLOCKED"),
    "TOO_SMALL": ("⊘", "amber", "TOO SMALL TO MEASURE"),
    "CAP_SET": ("₹", "blue", "CAP SET · ADMITTED"),
    "RUNNING": ("▸", "cyan", "RUNNING"),
    "BRAKE_PULLED": ("■", "red", "BRAKE PULLED"),
    "REVERTED": ("↩", "amber", "REVERTED"),
    "KEPT": ("✓", "green", "KEPT"),
    "NO_DIFFERENCE": ("=", "grey", "NO DIFFERENCE"),
    "LEARNED": ("✦", "violet", "LEARNED"),
}


def _proposals() -> list[Proposal]:
    win = Slice(device=Device.mobile, customer_type=CustomerType.returning, order_band="1k-3k")
    harm = Slice(device=Device.desktop, customer_type=CustomerType.new, order_band="1k-3k")
    honest = Slice(device=Device.mobile, customer_type=CustomerType.new, order_band="1k-3k")
    small = Slice(device=Device.desktop, customer_type=CustomerType.returning, order_band="1k-3k")
    tail = Slice(device=Device.mobile, customer_type=CustomerType.returning, order_band=">5k")
    P = Proposal
    return [
        # Beat 3 — asks for too much, blocked; then within the ceiling, runs and wins.
        P(what_changed="Show cards first for mobile returning buyers (₹1k–3k)",
          test_kind=TestKind.payment_method_order, slice=win, traffic_share=0.25,
          metric_to_watch="checkout completion", why="completion fell 8pp here", effect_to_detect_pp=7),
        P(what_changed="Show cards first for mobile returning buyers (₹1k–3k)",
          test_kind=TestKind.payment_method_order, slice=win, traffic_share=0.10,
          metric_to_watch="checkout completion", why="same idea, within the ceiling", effect_to_detect_pp=7),
        # Beat 5 — a test that turns harmful mid-flight; the brake stops it.
        P(what_changed="Show cards first for desktop new buyers (₹1k–3k)",
          test_kind=TestKind.payment_method_order, slice=harm, traffic_share=0.10,
          metric_to_watch="checkout completion", why="try the same win on desktop new", effect_to_detect_pp=5),
        # Beat 6 — the honesty test: both options are secretly identical.
        P(what_changed="Show cards first for mobile new buyers (₹1k–3k)",
          test_kind=TestKind.payment_method_order, slice=honest, traffic_share=0.10,
          metric_to_watch="checkout completion", why="unclear signal, worth checking", effect_to_detect_pp=5),
        # A different family: retry timing. Waiting longer before the first retry
        # recovers more failed charges for mobile new buyers — the agent generalizes.
        P(what_changed="Wait 6h, not 30m, before the first retry — mobile new buyers (₹1k–3k)",
          test_kind=TestKind.retry_timing, slice=honest, traffic_share=0.10,
          metric_to_watch="recovery rate", why="early retries fail while the bank is still cooling off", effect_to_detect_pp=6),
        # Beat 4 — too small to measure.
        P(what_changed="Show cards first for desktop returning buyers (₹1k–3k)",
          test_kind=TestKind.payment_method_order, slice=small, traffic_share=0.10,
          metric_to_watch="checkout completion", why="small wobble, want to detect 2pp", effect_to_detect_pp=2),
        # Prohibited action, and out-of-window orders — both blocked.
        P(what_changed="Retry without re-authenticating to speed recovery",
          test_kind=TestKind.retry_timing, slice=win, traffic_share=0.10,
          metric_to_watch="recovery rate", why="faster retries", touches=["skip_authentication"]),
        P(what_changed="Show cards first for high-value orders (>₹5k)",
          test_kind=TestKind.payment_method_order, slice=tail, traffic_share=0.10,
          metric_to_watch="checkout completion", why="chase the big baskets", effect_to_detect_pp=5),
    ]


def _archive_run(conn: sqlite3.Connection, run_id: str, seed: int, live: bool,
                 policy: Policy, clock: Clock) -> None:
    """Snapshot this run into the registry — the moving levers plus the outcome —
    so runs persist and can be compared even after the next same-seed run."""
    levers = {
        "max_traffic_share": policy.limits.max_traffic_share,
        "max_loss_per_test_inr": policy.limits.max_loss_per_test_inr,
        "max_minutes": policy.limits.max_minutes,
        "harm_alpha": policy.brake.harm_alpha,
        "alpha": policy.promote.alpha,
        "autonomy": policy.autonomy,
    }
    record_run(conn, {
        "run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": seed, "live": int(live), "policy_json": json.dumps(levers),
        "sim_seconds": round(clock.now(), 1), **summarize_run(conn, run_id),
    })


def run_demo(seed: int = 42, speed: float = 10_000.0) -> str:
    policy = load_policy()
    clock = SimClock(speed=speed)
    run_id = f"run_{seed:03d}"
    from .eventlog import RUNS_DIR
    (RUNS_DIR / f"{run_id}.jsonl").unlink(missing_ok=True)  # start clean so replays are exact
    log = EventLog(run_id, clock)
    conn = connect()
    clear_run(conn, run_id)  # drop this run_id's prior rows; the registry keeps its summary
    world = World(seed=seed)
    log.append("WATCHING", slice="mobile · returning · 1k-3k",
               note="completion 72.1% → 63.7% over 14 days · set 19 months ago, never re-tested")
    for p in _proposals():
        clock.advance(3600)  # an hour of sim time between proposals
        conduct(p, policy=policy, world=world, log=log, conn=conn, run_id=run_id, clock=clock)
    _archive_run(conn, run_id, seed, live=False, policy=policy, clock=clock)
    log.close()
    conn.close()
    return str(log.path)


def run_live(seed: int = 42, speed: float = 10_000.0) -> str:
    """The real loop: the watcher flags slices, Gemini proposes, the gates decide."""
    policy = load_policy()
    clock = SimClock(speed=speed)
    run_id = f"live_{seed:03d}"
    from .eventlog import RUNS_DIR
    (RUNS_DIR / f"{run_id}.jsonl").unlink(missing_ok=True)
    log = EventLog(run_id, clock)
    conn = connect()
    world = World(seed=seed)
    flags = flagged_slices(world)[:4]
    log.append("WATCHING", slice=flags[0].slice.label(),
               note=f"completion {flags[0].recent*100:.1f}% vs usual {flags[0].baseline*100:.1f}% · settings set long ago, never re-tested")
    for f in flags:
        clock.advance(3600)
        reason_and_conduct(f, policy=policy, world=world, log=log, conn=conn, run_id=run_id, clock=clock)
    _archive_run(conn, run_id, seed, live=True, policy=policy, clock=clock)
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
        if kind == "THINKING":
            print(f"  {C['grey']}{e.get('note','')}{C['off']}")
        elif kind == "PROPOSED":
            by = e.get("proposed_by", "curated")
            tag = f"  {C['violet']}[Gemini]{C['off']}" if by == "gemini" else f"  {C['grey']}[{by}]{C['off']}"
            print(f"  {e['headline']}{tag}\n  {C['grey']}{e['slice']} · asked {int(e['traffic_share']*100)}% of traffic{('  · '+e['degraded']) if e.get('degraded') else ''}{C['off']}")
        elif kind == "BLOCKED":
            print(f"  {C['red']}{e['reason']}{C['off']}")
        elif kind in ("TOO_SMALL", "CAP_SET", "KEPT", "NO_DIFFERENCE", "REVERTED"):
            print(f"  {e.get('note', '')}")
        elif kind == "RUNNING" and e.get("day"):
            print(f"  day {e['day']}: control {e['rate_control']*100:.1f}%  treatment {e['rate_treatment']*100:.1f}%  "
                  f"· at risk ₹{e['realized_loss_inr']:,.0f} / ₹{e['max_loss_inr']:,.0f}")
        elif kind == "BRAKE_PULLED":
            print(f"  {C['red']}{e['reason']}{C['off']}")
        elif kind == "LEARNED":
            print(f"  {C['grey']}{e['claim']}{C['off']}")
        print()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    except Exception:
        pass
    if len(sys.argv) >= 3 and sys.argv[1] == "replay":
        render(sys.argv[2])
        return
    live = len(sys.argv) >= 2 and sys.argv[1] == "live"
    path = run_live() if live else run_demo()
    render(path)
    print(f"{C['grey']}log: {path}{('  (live · Gemini)' if live else '  (curated replay)')}{C['off']}")


if __name__ == "__main__":
    main()
