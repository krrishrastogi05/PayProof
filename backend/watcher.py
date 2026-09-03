"""
What this does: watches the payment data and flags a slice whose completion has
moved outside its own recent range — the trigger for the whole pipeline.
What it must never do: read the hidden truth, or propose a fix (that's the reasoner).
Where its numbers come from: observed completion, sampled from the world.

Deliberately simple; this is not the interesting part.
"""

from __future__ import annotations

from pydantic import BaseModel

from .models import CustomerType, Device, Slice
from .sim.world import World

# The slices the merchant actually cares about (in the tested order window).
_WATCHED = [
    Slice(device=Device.mobile, customer_type=CustomerType.returning, order_band="1k-3k"),
    Slice(device=Device.desktop, customer_type=CustomerType.new, order_band="1k-3k"),
    Slice(device=Device.mobile, customer_type=CustomerType.new, order_band="1k-3k"),
    Slice(device=Device.desktop, customer_type=CustomerType.returning, order_band="1k-3k"),
]
_BASELINE = 0.721   # the long-run completion the merchant is used to
_DROP_TO_FLAG = 0.03


class Flag(BaseModel):
    slice: Slice
    baseline: float
    recent: float
    drop_pp: float


def flagged_slices(world: World) -> list[Flag]:
    """Return the slices that have slipped, worst drop first."""
    flags: list[Flag] = []
    for s in _WATCHED:
        recent = world.observed_baseline(s, samples=3000)
        drop = _BASELINE - recent
        if drop >= _DROP_TO_FLAG:
            flags.append(Flag(slice=s, baseline=_BASELINE, recent=round(recent, 4),
                              drop_pp=round(drop * 100, 1)))
    # If nothing genuinely slipped in this sample, still surface the watched slices
    # so the agent has something to reason about (their settings are years stale).
    if not flags:
        flags = [Flag(slice=s, baseline=_BASELINE, recent=_BASELINE, drop_pp=0.0) for s in _WATCHED]
    return sorted(flags, key=lambda f: -f.drop_pp)
