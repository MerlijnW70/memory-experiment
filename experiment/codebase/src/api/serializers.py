"""API response serializers.

SUBTLE INVARIANT: All monetary amounts are stored internally as integers
(cents) but must be serialized as floats (dollars) in API responses.
This module handles that conversion using utils.money.cents_to_dollars().
If you add a new model with monetary fields, make sure to convert here.
"""

from typing import Any

from src.models.payment import Payment
from src.models.subscription import Subscription
from src.models.user import User
from src.utils.money import cents_to_dollars


def serialize_user(user: User) -> dict[str, Any]:
    """Serialize a User for API output.

    Args:
        user: The User object to serialize.

    Returns:
        A dict suitable for JSON serialization.
    """
    return {
        "id": user.user_id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name or user.username,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }


def serialize_payment(payment: Payment) -> dict[str, Any]:
    """Serialize a Payment for API output.

    Converts amount_cents (int) to amount (float, dollars).

    Args:
        payment: The Payment object to serialize.

    Returns:
        A dict with 'amount' as a dollar float (NOT cents).
    """
    return {
        "id": payment.payment_id,
        "user_id": payment.user_id,
        "amount": cents_to_dollars(payment.amount_cents),
        "currency": payment.currency,
        "status": payment.status,
        "description": payment.description,
        "subscription_id": payment.subscription_id,
        "created_at": payment.created_at,
    }


def serialize_subscription(subscription: Subscription) -> dict[str, Any]:
    """Serialize a Subscription for API output.

    Converts price_cents (int) to price (float, dollars).

    Args:
        subscription: The Subscription object to serialize.

    Returns:
        A dict with 'price' as a dollar float (NOT cents).
    """
    return {
        "id": subscription.subscription_id,
        "user_id": subscription.user_id,
        "plan": subscription.plan,
        "price": cents_to_dollars(subscription.price_cents),
        "status": subscription.status,
        "created_at": subscription.created_at,
        "cancelled_at": subscription.cancelled_at,
    }


def serialize_list(items: list, serializer: callable) -> list[dict[str, Any]]:
    """Serialize a list of objects using the given serializer function.

    Args:
        items: List of model objects.
        serializer: A serializer function (e.g. serialize_payment).

    Returns:
        List of serialized dicts.
    """
    return [serializer(item) for item in items]


def serialize_error(status: int, message: str) -> dict[str, Any]:
    """Create a standard error response dict.

    Args:
        status: HTTP status code.
        message: Error message.

    Returns:
        Error response dict.
    """
    return {
        "status": status,
        "error": message,
    }
