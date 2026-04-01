"""User profile management.

Handles read and update operations for user profile data, which is a
subset of the full user record focused on display and preference fields.
"""

from typing import Any, Optional

from src.config import get_db
from src.models.user import User
from src.utils.logging import log_event
from src.utils.validation import validate_email, sanitize_string


def get_profile(user_id: str) -> Optional[dict[str, Any]]:
    """Get the public profile for a user.

    Returns a subset of user fields suitable for display.

    Args:
        user_id: The user's ID.

    Returns:
        A dict with profile fields, or None if user not found.
    """
    db = get_db()
    user_data = db["users"].get(user_id)
    if user_data is None:
        return None

    return {
        "user_id": user_data["user_id"],
        "username": user_data["username"],
        "display_name": user_data.get("display_name") or user_data["username"],
        "email": user_data["email"],
        "role": user_data["role"],
        "created_at": user_data["created_at"],
        "metadata": user_data.get("metadata", {}),
    }


def update_profile(
    user_id: str,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Update profile fields for a user.

    Args:
        user_id: The user whose profile to update.
        display_name: New display name (will be sanitized).
        email: New email address (will be validated).
        metadata: Metadata dict to merge with existing metadata.

    Returns:
        The updated profile dict, or None if user not found.

    Raises:
        ValueError: If the new email is invalid.
    """
    db = get_db()
    user_data = db["users"].get(user_id)
    if user_data is None:
        return None

    if display_name is not None:
        user_data["display_name"] = sanitize_string(display_name, max_length=100)

    if email is not None:
        if not validate_email(email):
            raise ValueError(f"Invalid email: {email}")
        # Check uniqueness
        for uid, existing in db["users"].items():
            if uid != user_id and existing["email"] == email:
                raise ValueError(f"Email '{email}' is already registered")
        user_data["email"] = email

    if metadata is not None:
        existing_meta = user_data.get("metadata", {})
        existing_meta.update(metadata)
        user_data["metadata"] = existing_meta

    db["users"][user_id] = user_data

    log_event("profile_updated", user_id=user_id)
    return get_profile(user_id)
