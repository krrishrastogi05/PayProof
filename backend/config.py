"""
What this does: loads policy.yaml into a typed object so every boundary in the
code traces to a line a human wrote. Also loads .env for service keys.
What it must never do: let code write policy.yaml, or hide a limit as a constant.
Where its numbers come from: policy.yaml only. A magic number in a conditional is a bug.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "policy.yaml"

load_dotenv(ROOT / ".env")


class Limits(BaseModel):
    max_traffic_share: float
    max_minutes: int
    max_loss_per_test_inr: int
    max_loss_per_day_inr: int
    max_tests_at_once: int


class OrderWindow(BaseModel):
    min_inr: int
    max_inr: int


class Brake(BaseModel):
    failure_rate_rise_pp: float
    refund_rate_rise_pp: float
    latency_rise_ms: int
    harm_alpha: float


class Promote(BaseModel):
    alpha: float
    min_power: float
    require_range_excludes_zero: bool


class DiscoveryBudget(BaseModel):
    max_promotions_per_10_tests: int


class Policy(BaseModel):
    merchant: str
    autonomy: str
    limits: Limits
    allowed_tests: list[str]
    never: list[str]
    only_include_orders: OrderWindow
    brake: Brake
    promote: Promote
    discovery_budget: DiscoveryBudget


# A human may tune limits at runtime (the CLI stands in for editing policy.yaml).
# We keep overrides in memory so the committed file is never mutated.
# key -> (yaml section or "top", python type)
_TUNABLE: dict[str, tuple[str, type]] = {
    "max_traffic_share": ("limits", float), "max_loss_per_test_inr": ("limits", int),
    "max_loss_per_day_inr": ("limits", int), "max_minutes": ("limits", int),
    "max_tests_at_once": ("limits", int), "harm_alpha": ("brake", float),
    "alpha": ("promote", float), "min_power": ("promote", float), "autonomy": ("top", str),
}
_OVERRIDE: dict[str, object] = {}


def load_policy(path: str | Path = POLICY_PATH) -> Policy:
    with Path(path).open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    for key, val in _OVERRIDE.items():
        section, _ = _TUNABLE[key]
        if section == "top":
            raw[key] = val
        else:
            raw.setdefault(section, {})[key] = val
    return Policy(**raw)


def set_override(key: str, value: str) -> str:
    if key not in _TUNABLE:
        raise KeyError(f"'{key}' is not tunable. try: {', '.join(_TUNABLE)}")
    _, caster = _TUNABLE[key]
    _OVERRIDE[key] = caster(value)
    return f"{key} = {_OVERRIDE[key]}"


def clear_overrides() -> None:
    _OVERRIDE.clear()


def tunables() -> list[str]:
    return list(_TUNABLE)
