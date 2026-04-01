"""Refund processing logic.

Handles full and partial refunds for completed payments.
"""

from typing import Optional

from src.auth.tokens import get_current_user
from src.config import get_db
from src.models.payment import Payment
from src.utils.logging import log_event


def process_refund(
    payment_id: str,
    reason: str = "",
    amount_cents: Optional[int] = None,
) -> Optional[Payment]:
    """Process a refund for a completed payment.

    If amount_cents is not specified, a full refund is issued.

    Args:
        payment_id: The payment to refund.
        reason: Human-readable reason for the refund.
        amount_cents: Partial refund amount in cents. If None, full refund.

    Returns:
        The refund Payment object, or None if the original payment was not
        found or was not in a refundable state.

    Raises:
        ValueError: If the refund amount exceeds the original payment.
    """
    db = get_db()
    original_data = db["payments"].get(payment_id)

    if original_data is None:
        log_event(
            "refund_payment_not_found",
            level="warning",
            payment_id=payment_id,
        )
        return None

    if original_data["status"] != "completed":
        log_event(
            "refund_invalid_status",
            level="warning",
            payment_id=payment_id,
            status=original_data["status"],
        )
        return None

    original = Payment.from_dict(original_data)

    if amount_cents is None:
        amount_cents = original.amount_cents

    if amount_cents > original.amount_cents:
        raise ValueError(
            f"Refund amount ({amount_cents}) exceeds original "
            f"payment ({original.amount_cents})"
        )

    # Create the refund payment record
    refund = Payment(
        user_id=original.user_id,
        amount_cents=amount_cents,
        currency=original.currency,
        description=f"Refund for payment {payment_id}",
        status="refunded",
        subscription_id=original.subscription_id,
        refund_reason=reason,
    )

    db["payments"][refund.payment_id] = refund.to_dict()

    # Mark original as refunded
    original_data["status"] = "refunded"
    original_data["refund_reason"] = reason

    log_event(
        "refund_processed",
        payment_id=payment_id,
        refund_id=refund.payment_id,
        amount_cents=amount_cents,
        user_id=original.user_id,
    )

    return refund
