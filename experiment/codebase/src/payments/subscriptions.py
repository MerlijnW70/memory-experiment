"""Subscription management.

Handles creation, cancellation, and querying of user subscriptions.
"""

from datetime import datetime, timezone
from typing import Optional

from src.auth.tokens import get_current_user
from src.config import get_db
from src.models.subscription import Subscription, PLAN_PRICES_CENTS
from src.utils.logging import log_event


def create_subscription(
    plan: str,
    user_id: Optional[str] = None,
) -> Subscription:
    """Create a new subscription.

    Args:
        plan: Plan name ('basic', 'pro', or 'enterprise').
        user_id: The user to subscribe. Defaults to the current authenticated
                 user from the thread-local.

    Returns:
        The created Subscription object.

    Raises:
        RuntimeError: If no user_id provided and no user is authenticated.
        ValueError: If the plan is invalid or user already has an active sub.
    """
    if user_id is None:
        user = get_current_user()
        if user is None:
            raise RuntimeError(
                "No user_id provided and no authenticated user."
            )
        user_id = user.user_id

    # Check for existing active subscription
    existing = get_user_subscriptions(user_id)
    active_subs = [s for s in existing if s.status == "active"]
    if active_subs:
        raise ValueError(
            f"User {user_id} already has an active subscription "
            f"(plan={active_subs[0].plan})"
        )

    subscription = Subscription(
        user_id=user_id,
        plan=plan,
    )

    db = get_db()
    db["subscriptions"][subscription.subscription_id] = subscription.to_dict()

    log_event(
        "subscription_created",
        user_id=user_id,
        subscription_id=subscription.subscription_id,
        plan=plan,
        price_cents=subscription.price_cents,
    )

    return subscription


def cancel_subscription(subscription_id: str) -> Optional[Subscription]:
    """Cancel a specific subscription by ID.

    Args:
        subscription_id: The subscription to cancel.

    Returns:
        The updated Subscription object, or None if not found.
    """
    db = get_db()
    sub_data = db["subscriptions"].get(subscription_id)
    if sub_data is None:
        return None

    if sub_data["status"] == "cancelled":
        return Subscription.from_dict(sub_data)

    sub_data["status"] = "cancelled"
    sub_data["cancelled_at"] = datetime.now(timezone.utc).isoformat()
    db["subscriptions"][subscription_id] = sub_data

    log_event(
        "subscription_cancelled",
        subscription_id=subscription_id,
        user_id=sub_data["user_id"],
    )

    return Subscription.from_dict(sub_data)


def cancel_all_user_subscriptions(user_id: str) -> int:
    """Cancel all active subscriptions for a user.

    This is called during user deletion to clean up payment obligations.

    Args:
        user_id: The user whose subscriptions to cancel.

    Returns:
        The number of subscriptions that were cancelled.
    """
    db = get_db()
    cancelled_count = 0
    now = datetime.now(timezone.utc).isoformat()

    for sub_id, sub_data in db["subscriptions"].items():
        if sub_data["user_id"] == user_id and sub_data["status"] == "active":
            sub_data["status"] = "cancelled"
            sub_data["cancelled_at"] = now
            cancelled_count += 1

    if cancelled_count > 0:
        log_event(
            "subscriptions_bulk_cancelled",
            user_id=user_id,
            count=cancelled_count,
        )

    return cancelled_count


def get_user_subscriptions(user_id: str) -> list[Subscription]:
    """Retrieve all subscriptions for a user.

    Args:
        user_id: The user whose subscriptions to retrieve.

    Returns:
        List of Subscription objects.
    """
    db = get_db()
    return [
        Subscription.from_dict(s)
        for s in db["subscriptions"].values()
        if s["user_id"] == user_id
    ]
