"""
What this does: loads policy.yaml into a typed object so every boundary in the
code traces to a line a human wrote. Also loads .env for service keys.
What it must never do: let code write policy.yaml, or hide a limit as a constant.
Where its numbers come from: policy.yaml only. A magic number in a conditional is a bug.
"""

from __future__ import annotations

from functools import lru_cache
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


@lru_cache(maxsize=1)
def load_policy(path: str | Path = POLICY_PATH) -> Policy:
    with Path(path).open(encoding="utf-8") as fh:
        return Policy(**yaml.safe_load(fh))
