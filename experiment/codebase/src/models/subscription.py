"""Subscription data model.

Subscription pricing follows the same cents-as-integers convention as payments.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


VALID_PLANS = ("basic", "pro", "enterprise")
PLAN_PRICES_CENTS: dict[str, int] = {
    "basic": 999,       # $9.99/month
    "pro": 2999,        # $29.99/month
    "enterprise": 9999, # $99.99/month
}


@dataclass
class Subscription:
    """Represents a recurring subscription.

    Attributes:
        subscription_id: Unique identifier (UUID string).
        user_id: The subscriber's user ID.
        plan: Plan name, one of 'basic', 'pro', 'enterprise'.
        price_cents: Monthly price in cents.
        status: One of 'active', 'cancelled', 'paused', 'expired'.
        created_at: When the subscription was created.
        cancelled_at: When the subscription was cancelled, if applicable.
    """

    user_id: str
    plan: str
    price_cents: int = 0
    status: str = "active"
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cancelled_at: Optional[str] = None

    def __post_init__(self) -> None:
        if self.plan not in VALID_PLANS:
            raise ValueError(
                f"Invalid plan '{self.plan}', must be one of {VALID_PLANS}"
            )
        # Auto-set price from plan if not explicitly provided
        if self.price_cents == 0:
            self.price_cents = PLAN_PRICES_CENTS[self.plan]

    def to_dict(self) -> dict:
        """Serialize the subscription to a plain dictionary."""
        return {
            "subscription_id": self.subscription_id,
            "user_id": self.user_id,
            "plan": self.plan,
            "price_cents": self.price_cents,
            "status": self.status,
            "created_at": self.created_at,
            "cancelled_at": self.cancelled_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Subscription":
        """Create a Subscription from a dictionary."""
        return cls(
            subscription_id=data["subscription_id"],
            user_id=data["user_id"],
            plan=data["plan"],
            price_cents=data.get("price_cents", 0),
            status=data.get("status", "active"),
            created_at=data.get(
                "created_at", datetime.now(timezone.utc).isoformat()
            ),
            cancelled_at=data.get("cancelled_at"),
        )
