"""Payment processing.

IMPLICIT CONTRACT: This module reads the current user from the thread-local
set by auth.tokens.validate_token(). Callers MUST ensure that validate_token()
has been called on the current thread before invoking process_payment().
If no current_user is set, payment functions will raise a RuntimeError.
"""

from typing import Optional

from src.auth.tokens import get_current_user
from src.config import get_db
from src.models.payment import Payment
from src.utils.logging import log_event


def process_payment(
    amount_cents: int,
    description: str = "",
    currency: str = "USD",
    subscription_id: Optional[str] = None,
) -> Payment:
    """Process a payment for the currently authenticated user.

    The user is determined from the thread-local current_user, NOT passed
    as a parameter. This is intentional — it ensures payments are always
    tied to the authenticated session.

    Args:
        amount_cents: Amount to charge in cents (integer).
        description: Human-readable description of the charge.
        currency: ISO 4217 currency code.
        subscription_id: Associated subscription ID, if any.

    Returns:
        The created Payment object.

    Raises:
        RuntimeError: If no user is authenticated on the current thread.
        ValueError: If amount_cents is invalid.
    """
    user = get_current_user()
    if user is None:
        raise RuntimeError(
            "No authenticated user. Call auth.validate_token() before "
            "processing payments."
        )

    if not isinstance(amount_cents, int) or amount_cents <= 0:
        raise ValueError(f"Invalid payment amount: {amount_cents}")

    payment = Payment(
        user_id=user.user_id,
        amount_cents=amount_cents,
        currency=currency,
        description=description,
        subscription_id=subscription_id,
        status="completed",
    )

    # Simulate gateway call
    db = get_db()
    db["payments"][payment.payment_id] = payment.to_dict()

    log_event(
        "payment_processed",
        user_id=user.user_id,
        payment_id=payment.payment_id,
        amount_cents=amount_cents,
    )

    return payment


def get_user_payments(user_id: Optional[str] = None) -> list[Payment]:
    """Retrieve all payments for a user.

    If user_id is not provided, uses the current authenticated user.

    Args:
        user_id: The user whose payments to retrieve. Defaults to current user.

    Returns:
        List of Payment objects, newest first.

    Raises:
        RuntimeError: If no user_id is provided and no user is authenticated.
    """
    if user_id is None:
        user = get_current_user()
        if user is None:
            raise RuntimeError(
                "No user_id provided and no authenticated user."
            )
        user_id = user.user_id

    db = get_db()
    payments = [
        Payment.from_dict(p)
        for p in db["payments"].values()
        if p["user_id"] == user_id
    ]
    # Sort newest first
    payments.sort(key=lambda p: p.created_at, reverse=True)
    return payments
