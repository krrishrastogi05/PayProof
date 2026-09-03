"""
What this does: time, injected. SimClock runs at N x; WallClock is real time.
Same shape, so a correctly-sized 14-day test finishes in seconds on screen while
every duration stays honest.
What it must never do: branch on which clock it is — callers depend only on Clock.
Where its numbers come from: `speed` is passed in; the caller decides the run rate.
"""

from __future__ import annotations

import time
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    speed: float
    def now(self) -> float: ...           # simulated seconds since start
    def real_elapsed(self) -> float: ...  # real wall seconds since start
    def advance(self, sim_seconds: float) -> None: ...


class SimClock:
    """Fast-forward clock. `advance` moves sim time and sleeps only the real
    fraction (dt / speed), capped so a demo never stalls."""

    def __init__(self, speed: float = 10_000.0, max_real_sleep: float = 0.05) -> None:
        self.speed = speed
        self._sim = 0.0
        self._real_start = time.monotonic()
        self._max_real_sleep = max_real_sleep

    def now(self) -> float:
        return self._sim

    def real_elapsed(self) -> float:
        return time.monotonic() - self._real_start

    def advance(self, sim_seconds: float) -> None:
        self._sim += sim_seconds
        nap = min(sim_seconds / self.speed, self._max_real_sleep)
        if nap > 0:
            time.sleep(nap)


class WallClock:
    """Real time. `advance` actually waits — used when riding live webhooks."""

    speed = 1.0

    def __init__(self) -> None:
        self._start = time.monotonic()

    def now(self) -> float:
        return time.monotonic() - self._start

    def real_elapsed(self) -> float:
        return time.monotonic() - self._start

    def advance(self, sim_seconds: float) -> None:
        time.sleep(sim_seconds)
