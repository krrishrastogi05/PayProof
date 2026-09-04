"""
What this does: the observable simulated world — how many sessions each slice
sees, and whether a checkout completes. Outcomes are drawn using the hidden
truth, so we know the right answers and can check whether the agent found them.
What it must never do: expose the hidden effect to callers. It returns only what a
merchant could actually observe (counts, outcomes, revenue) — never the effect size.
Where its numbers come from: shares below are observable; the completion odds come
from sim/truth.py (this simulator is allowed to know the truth; the agent is not).
"""

from __future__ import annotations

import random
from ..models import Slice, TestKind
from . import truth

# Observable traffic mix. Tuned so the demo slices hit the numbers in the PRD:
# desktop/returning/1k-3k ~= 412 sessions/day (too small for a 2pp test),
# mobile/returning/1k-3k ~= 727/day (a 7pp test fits inside 14 days).
TOTAL_PER_DAY = 4900
DEVICE_SHARE = {"mobile": 0.60, "desktop": 0.34, "tablet": 0.06}
CTYPE_SHARE = {"returning": 0.55, "new": 0.45}
BAND_SHARE = {"<1k": 0.20, "1k-3k": 0.45, "3k-5k": 0.22, ">5k": 0.13}
AVG_ORDER_INR = {"<1k": 700, "1k-3k": 2000, "3k-5k": 3900, ">5k": 8200}


def arrival_per_day(s: Slice) -> float:
    dev = DEVICE_SHARE.get(s.device.value, 0.02)
    ct = CTYPE_SHARE.get(s.customer_type.value, 0.5)
    band = BAND_SHARE.get(s.order_band, 0.05)
    return round(TOTAL_PER_DAY * dev * ct * band, 1)


def avg_order_inr(order_band: str) -> int:
    return AVG_ORDER_INR.get(order_band, 1500)


class World:
    """Deterministic given a seed. Generates checkout outcomes."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    def completes(self, s: Slice, cards_first: bool) -> bool:
        """Draw one checkout outcome for this slice under the given setting."""
        rate = truth.true_completion_rate(s.device.value, s.customer_type.value, s.order_band, cards_first)
        return self.rng.random() < rate

    def recovers(self, s: Slice, faster_retry: bool) -> bool:
        """Draw one failed-payment recovery outcome under the given retry schedule."""
        rate = truth.true_recovery_rate(s.device.value, s.customer_type.value, s.order_band, faster_retry)
        return self.rng.random() < rate

    def draw(self, s: Slice, test_kind: TestKind, treatment: bool) -> bool:
        """One outcome for whichever lever this test pulls — the runner stays
        family-agnostic; only the world knows which truth to consult."""
        if test_kind == TestKind.retry_timing:
            return self.recovers(s, treatment)
        return self.completes(s, treatment)

    def observed_baseline(self, s: Slice, samples: int = 4000) -> float:
        """What the merchant currently sees for this slice (UPI-first / control)."""
        wins = sum(1 for _ in range(samples) if self.completes(s, cards_first=False))
        return wins / samples
