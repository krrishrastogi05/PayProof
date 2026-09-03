"""
What this does: the hidden truth of the simulated world — the REAL effect of
showing cards first, per slice. The simulator uses it to decide outcomes; the
whole point of the project is that the agent must *discover* these numbers.
What it must never do: be imported by any agent-side module (watcher, reasoner,
rules, feasibility, scoreboard). test_reasoner_cannot_see_ground_truth enforces it.
Where its numbers come from: hand-seeded for the demo. Effects are INFLATED vs
reality (real payment effects are 1-3 pp) so the loop is visible in a 5-min video;
LIMITATIONS.md says so plainly.

Only sim/world.py may import this file.
"""

from __future__ import annotations

BASELINE_COMPLETION = 0.72

# Effect of showing CARDS first (vs the current UPI-first default), in percentage
# points. Checked most-specific first. Anything unlisted is 0 (no real effect).
_EFFECTS_PP: list[tuple[dict[str, str], float]] = [
    ({"device": "mobile", "customer_type": "returning", "order_band": "1k-3k"}, +7.0),
    ({"device": "mobile", "customer_type": "returning", "order_band": ">5k"}, -4.0),  # harmful
    ({"device": "tablet", "customer_type": "returning"}, 0.0),                        # honesty test
    ({"device": "mobile", "customer_type": "new"}, +0.5),
    ({"device": "desktop"}, -1.0),
]


def _matches(rule: dict[str, str], device: str, customer_type: str, order_band: str) -> bool:
    got = {"device": device, "customer_type": customer_type, "order_band": order_band}
    return all(got[k] == v for k, v in rule.items())


def true_effect_pp(device: str, customer_type: str, order_band: str) -> float:
    for rule, pp in _EFFECTS_PP:
        if _matches(rule, device, customer_type, order_band):
            return pp
    return 0.0


def true_completion_rate(device: str, customer_type: str, order_band: str, cards_first: bool) -> float:
    rate = BASELINE_COMPLETION + (true_effect_pp(device, customer_type, order_band) / 100.0 if cards_first else 0.0)
    return max(0.0, min(1.0, rate))
