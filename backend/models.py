"""
What this does: the shared vocabulary of Thaw — slices, proposals, the test
lifecycle. Everything else imports these.
What it must never do: hold behaviour or talk to the model / DB / network.
Where its numbers come from: nowhere. These are shapes, not values.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Device(str, Enum):
    mobile = "mobile"
    desktop = "desktop"
    tablet = "tablet"


class CustomerType(str, Enum):
    new = "new"
    returning = "returning"


class TestKind(str, Enum):
    # Only two kinds exist, on purpose (PRD non-goal: no more than two).
    payment_method_order = "payment_method_order"
    retry_timing = "retry_timing"


class Slice(BaseModel):
    """A cut of traffic. Order bands are strings like '1k-3k' or '>5k'."""

    device: Device
    customer_type: CustomerType
    order_band: str

    def label(self) -> str:
        return f"{self.device.value} · {self.customer_type.value} · {self.order_band}"


class Proposal(BaseModel):
    """The reasoner's only output shape. If Gemini returns anything else, we reject it."""

    what_changed: str
    test_kind: TestKind
    slice: Slice
    traffic_share: float = Field(gt=0, le=1)
    metric_to_watch: str
    why: str
    # What the change would affect. Clean tests touch nothing on the `never` list;
    # a proposal that would (e.g.) skip authentication declares it here and is blocked.
    touches: list[str] = Field(default_factory=list)
    # The change the agent expects to detect, in percentage points — drives feasibility.
    effect_to_detect_pp: float = 2.0


class TestStatus(str, Enum):
    """The lifecycle. Six ways to end without a winner — each is a demo beat."""

    proposed = "PROPOSED"
    rules_check = "RULES_CHECK"
    blocked = "BLOCKED"
    feasibility_check = "FEASIBILITY_CHECK"
    declined_too_small = "DECLINED_TOO_SMALL"
    admitted = "ADMITTED"
    running = "RUNNING"
    stopped_by_brake = "STOPPED_BY_BRAKE"
    stopped_bad_split = "STOPPED_BAD_SPLIT"
    no_difference = "NO_DIFFERENCE"
    found_harmful = "FOUND_HARMFUL"
    found_winner = "FOUND_WINNER"
    promoted = "PROMOTED"
    holding = "HOLDING"
    rolled_back = "ROLLED_BACK"


# The only transitions that are allowed to happen. Anything else is a bug.
ALLOWED_TRANSITIONS: dict[TestStatus, set[TestStatus]] = {
    TestStatus.proposed: {TestStatus.rules_check},
    TestStatus.rules_check: {TestStatus.blocked, TestStatus.feasibility_check},
    TestStatus.feasibility_check: {TestStatus.declined_too_small, TestStatus.admitted},
    TestStatus.admitted: {TestStatus.running},
    TestStatus.running: {
        TestStatus.stopped_by_brake,
        TestStatus.stopped_bad_split,
        TestStatus.no_difference,
        TestStatus.found_harmful,
        TestStatus.found_winner,
    },
    TestStatus.found_winner: {TestStatus.promoted},
    TestStatus.promoted: {TestStatus.holding, TestStatus.rolled_back},
}


def can_move(src: TestStatus, dst: TestStatus) -> bool:
    return dst in ALLOWED_TRANSITIONS.get(src, set())
