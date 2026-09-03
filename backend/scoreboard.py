"""
What this does: says whether a test worked — uplift, an always-valid range, and a
split check. Deliberately lopsided: strong evidence to promote, weak evidence to
stop for harm. Because we look continuously, it uses a sequential (mSPRT) test, not
a fixed-horizon p-value re-checked over and over (that inflates 5% to ~30%).
What it must never do: ask the model, or read the hidden truth. Pure arithmetic.
Where its numbers come from: counts from the runner; alphas from policy.yaml.
"""

from __future__ import annotations

import math
from pydantic import BaseModel

# Prior scale for the mixture (mSPRT): effects are on the order of a few points.
_TAU = 0.05


class Analysis(BaseModel):
    n_control: int
    n_treatment: int
    rate_control: float
    rate_treatment: float
    uplift: float          # treatment - control, as a fraction
    ci_low: float
    ci_high: float
    excludes_zero: bool


def _rate(wins: int, n: int) -> float:
    return (wins + 0.5) / (n + 1)  # +0.5 smoothing so variance is never exactly 0


def analyze(n_control: int, wins_control: int, n_treatment: int, wins_treatment: int,
            alpha: float) -> Analysis:
    pc, pt = _rate(wins_control, n_control), _rate(wins_treatment, n_treatment)
    delta = pt - pc
    var = pc * (1 - pc) / max(n_control, 1) + pt * (1 - pt) / max(n_treatment, 1)
    # mSPRT always-valid CI radius: the set of nulls the mixture LR can't reject at alpha.
    radius = math.sqrt(var * (var + _TAU**2) / _TAU**2 * (2 * math.log(1 / alpha) + math.log((var + _TAU**2) / var)))
    lo, hi = delta - radius, delta + radius
    return Analysis(
        n_control=n_control, n_treatment=n_treatment, rate_control=pc, rate_treatment=pt,
        uplift=round(delta, 5), ci_low=round(lo, 5), ci_high=round(hi, 5),
        excludes_zero=(lo > 0 or hi < 0),
    )


def is_a_winner(a: Analysis, require_excludes_zero: bool) -> bool:
    """Strong evidence, positive: the CI is entirely above zero."""
    return a.uplift > 0 and (a.ci_low > 0 if require_excludes_zero else a.uplift > 0)


def is_harmful(a_harm: "Analysis", failure_rise_threshold_pp: float,
               min_per_group_seen: int, seen: int) -> bool:
    """Weak evidence is enough (a_harm is analyzed at the loose harm alpha), but it
    must be *evidence*: the point estimate is worse than the brake threshold AND the
    (tolerant) range excludes zero on the harmful side. A raw threshold alone trips
    on noise — which would false-brake a test where the truth is no difference."""
    if seen < min_per_group_seen:
        return False
    return a_harm.uplift < -(failure_rise_threshold_pp / 100.0) and a_harm.ci_high < 0


def split_is_healthy(n_control: int, n_treatment: int) -> tuple[bool, float]:
    """Chi-square on actual vs intended 50/50. p < 0.001 means the plumbing is
    broken (not that the idea is bad), so the result would be meaningless."""
    total = n_control + n_treatment
    if total < 50:
        return True, 1.0
    exp = total / 2
    chi2 = (n_control - exp) ** 2 / exp + (n_treatment - exp) ** 2 / exp
    p = math.erfc(math.sqrt(chi2 / 2))  # survival of chi-square, df=1
    return p >= 0.001, round(p, 4)
