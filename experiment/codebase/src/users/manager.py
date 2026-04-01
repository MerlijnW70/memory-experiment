"""User CRUD operations.

HIDDEN DEPENDENCY: delete_user() must cancel all of a user's active
subscriptions before removing them. Failing to do this leaves orphaned
subscription records that the billing system will attempt to charge.
This cleanup is handled by calling
payments.subscriptions.cancel_all_user_subscriptions().
"""

from typing import Optional

from src.config import get_db
from src.models.user import User
from src.payments.subscriptions import cancel_all_user_subscriptions
from src.users.notifications import send_notification
from src.utils.logging import log_event
from src.utils.validation import validate_email, validate_username


def create_user(
    username: str,
    email: str,
    role: str = "user",
    display_name: Optional[str] = None,
) -> User:
    """Create a new user account.

    Args:
        username: Unique username (3-32 alphanumeric + underscore).
        email: Valid email address.
        role: User role, defaults to 'user'.
        display_name: Optional display name.

    Returns:
        The created User object.

    Raises:
        ValueError: If username or email is invalid, or username is taken.
    """
    if not validate_username(username):
        raise ValueError(
            f"Invalid username '{username}': must be 3-32 alphanumeric "
            f"characters or underscores"
        )

    if not validate_email(email):
        raise ValueError(f"Invalid email address: {email}")

    db = get_db()

    # Check uniqueness
    for existing in db["users"].values():
        if existing["username"] == username:
            raise ValueError(f"Username '{username}' is already taken")
        if existing["email"] == email:
            raise ValueError(f"Email '{email}' is already registered")

    user = User(
        username=username,
        email=email,
        role=role,
        display_name=display_name,
    )

    db["users"][user.user_id] = user.to_dict()

    log_event("user_created", user_id=user.user_id, username=username)
    send_notification(
        user.user_id,
        "welcome",
        f"Welcome to the platform, {display_name or username}!",
    )

    return user


def get_user(user_id: str) -> Optional[User]:
    """Retrieve a user by ID.

    Args:
        user_id: The user's unique identifier.

    Returns:
        The User object, or None if not found.
    """
    db = get_db()
    user_data = db["users"].get(user_id)
    if user_data is None:
        return None
    return User.from_dict(user_data)


def get_user_by_username(username: str) -> Optional[User]:
    """Retrieve a user by username.

    Args:
        username: The username to look up.

    Returns:
        The User object, or None if not found.
    """
    db = get_db()
    for user_data in db["users"].values():
        if user_data["username"] == username:
            return User.from_dict(user_data)
    return None


def update_user(user_id: str, **updates: object) -> Optional[User]:
    """Update fields on an existing user.

    Args:
        user_id: The user to update.
        **updates: Field names and new values. Only 'email', 'display_name',
                   'role', 'is_active', and 'metadata' can be updated.

    Returns:
        The updated User object, or None if user not found.

    Raises:
        ValueError: If an invalid field is specified or validation fails.
    """
    db = get_db()
    user_data = db["users"].get(user_id)
    if user_data is None:
        return None

    allowed_fields = {"email", "display_name", "role", "is_active", "metadata"}
    for key in updates:
        if key not in allowed_fields:
            raise ValueError(f"Cannot update field '{key}'")

    if "email" in updates:
        if not validate_email(str(updates["email"])):
            raise ValueError(f"Invalid email: {updates['email']}")
        # Check uniqueness
        for uid, existing in db["users"].items():
            if uid != user_id and existing["email"] == updates["email"]:
                raise ValueError(
                    f"Email '{updates['email']}' is already registered"
                )

    for key, value in updates.items():
        user_data[key] = value

    db["users"][user_id] = user_data

    log_event(
        "user_updated",
        user_id=user_id,
        fields=list(updates.keys()),
    )

    return User.from_dict(user_data)


def delete_user(user_id: str) -> bool:
    """Delete a user and clean up all associated resources.

    IMPORTANT: This function cancels all active subscriptions before
    deleting the user record. This prevents orphaned subscriptions from
    being billed. If you modify this function, ensure the subscription
    cleanup step is preserved.

    Args:
        user_id: The user to delete.

    Returns:
        True if the user was deleted, False if not found.
    """
    db = get_db()

    if user_id not in db["users"]:
        return False

    # Step 1: Cancel all active subscriptions.
    # This MUST happen before the user record is removed, because the
    # subscription cancellation logic may reference the user.
    cancelled_count = cancel_all_user_subscriptions(user_id)
    if cancelled_count > 0:
        log_event(
            "user_delete_subscriptions_cleaned",
            user_id=user_id,
            cancelled_count=cancelled_count,
        )

    # Step 2: Send farewell notification (best-effort)
    send_notification(
        user_id,
        "account_deleted",
        "Your account has been deleted.",
    )

    # Step 3: Remove user record
    del db["users"][user_id]

    # Step 4: Invalidate all tokens for this user
    tokens_to_revoke = [
        token_str
        for token_str, token_data in db["tokens"].items()
        if token_data.get("user_id") == user_id
    ]
    for token_str in tokens_to_revoke:
        db["tokens"][token_str]["revoked"] = True

    log_event("user_deleted", user_id=user_id)
    return True


def list_users(
    include_inactive: bool = False,
) -> list[User]:
    """List all users, optionally including inactive ones.

    Args:
        include_inactive: If True, include deactivated users.

    Returns:
        List of User objects.
    """
    db = get_db()
    users = []
    for user_data in db["users"].values():
        if include_inactive or user_data.get("is_active", True):
            users.append(User.from_dict(user_data))
    return users
