"""Payment data model.

All monetary amounts are stored as integers in cents. For example, a charge
of $49.99 is represented as amount_cents=4999. Conversion to dollar floats
happens only at the API serialization boundary via utils.money.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Payment:
    """Represents a single payment transaction.

    Attributes:
        payment_id: Unique identifier (UUID string).
        user_id: The paying user's ID.
        amount_cents: Payment amount in cents (integer).
        currency: ISO 4217 currency code.
        status: One of 'pending', 'completed', 'failed', 'refunded'.
        description: Human-readable description.
        subscription_id: Associated subscription, if any.
        created_at: Transaction timestamp.
        refund_reason: Reason for refund, if applicable.
    """

    user_id: str
    amount_cents: int
    currency: str = "USD"
    status: str = "pending"
    description: str = ""
    payment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subscription_id: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    refund_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.amount_cents, int):
            raise TypeError(
                f"amount_cents must be int, got {type(self.amount_cents).__name__}"
            )
        if self.amount_cents < 0:
            raise ValueError("amount_cents must be non-negative")

    def to_dict(self) -> dict:
        """Serialize the payment to a plain dictionary."""
        return {
            "payment_id": self.payment_id,
            "user_id": self.user_id,
            "amount_cents": self.amount_cents,
            "currency": self.currency,
            "status": self.status,
            "description": self.description,
            "subscription_id": self.subscription_id,
            "created_at": self.created_at,
            "refund_reason": self.refund_reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Payment":
        """Create a Payment from a dictionary."""
        return cls(
            payment_id=data["payment_id"],
            user_id=data["user_id"],
            amount_cents=data["amount_cents"],
            currency=data.get("currency", "USD"),
            status=data.get("status", "pending"),
            description=data.get("description", ""),
            subscription_id=data.get("subscription_id"),
            created_at=data.get(
                "created_at", datetime.now(timezone.utc).isoformat()
            ),
            refund_reason=data.get("refund_reason"),
        )
