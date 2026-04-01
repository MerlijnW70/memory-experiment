"""Notification stubs.

In production, these would send actual emails via SMTP or a notification
service. For now, they log the notification and store it in a buffer
that tests can inspect.
"""

from typing import Any, Optional

from src.utils.logging import log_event


# In-memory notification store for testing
_sent_notifications: list[dict[str, Any]] = []


def send_notification(
    user_id: str,
    notification_type: str,
    message: str,
    channel: str = "email",
) -> bool:
    """Send a notification to a user.

    Currently a stub that records the notification for test verification
    rather than actually sending anything.

    Args:
        user_id: The recipient's user ID.
        notification_type: Category of notification (e.g. 'welcome',
                          'payment_receipt', 'subscription_cancelled').
        message: The notification body.
        channel: Delivery channel ('email', 'sms', 'push'). Defaults to email.

    Returns:
        True if the notification was "sent" (recorded) successfully.
    """
    notification = {
        "user_id": user_id,
        "type": notification_type,
        "message": message,
        "channel": channel,
    }

    _sent_notifications.append(notification)

    log_event(
        "notification_sent",
        user_id=user_id,
        notification_type=notification_type,
        channel=channel,
    )

    return True


def get_sent_notifications(
    user_id: Optional[str] = None,
    notification_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Retrieve sent notifications, optionally filtered.

    Args:
        user_id: Filter by recipient user ID.
        notification_type: Filter by notification type.

    Returns:
        List of notification dicts matching the filters.
    """
    results = _sent_notifications
    if user_id is not None:
        results = [n for n in results if n["user_id"] == user_id]
    if notification_type is not None:
        results = [n for n in results if n["type"] == notification_type]
    return list(results)


def clear_notifications() -> None:
    """Clear the notification buffer. Used in test teardown."""
    _sent_notifications.clear()
