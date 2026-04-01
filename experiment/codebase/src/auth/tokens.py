"""Token creation and validation.

IMPORTANT IMPLICIT CONTRACT:
    validate_token() sets threading.local().current_user to the authenticated
    User object. The payments module reads this thread-local to determine who
    is making a payment, rather than accepting an explicit user parameter.
    This avoids passing user objects through every call in the request chain
    but creates a hidden coupling — if validate_token() is not called before
    payment processing, payments will fail or act on the wrong user.
"""

import hashlib
import hmac
import json
import threading
import time
from typing import Optional

from src.config import TOKEN_SECRET, TOKEN_EXPIRY_SECONDS, get_db
from src.models.user import User
from src.utils.logging import log_event

# Thread-local storage for the currently authenticated user.
# This is set by validate_token() and read by other modules.
_thread_local = threading.local()


def get_current_user() -> Optional[User]:
    """Return the currently authenticated user for this thread, or None.

    This value is populated by validate_token() during request processing.
    """
    return getattr(_thread_local, "current_user", None)


def set_current_user(user: Optional[User]) -> None:
    """Explicitly set the current user on the thread-local.

    Primarily used in tests and middleware. In normal request flow,
    validate_token() handles this automatically.
    """
    _thread_local.current_user = user


def clear_current_user() -> None:
    """Remove the current user from the thread-local. Called after request."""
    _thread_local.current_user = None


def create_token(user: User) -> str:
    """Create an authentication token for the given user.

    The token is a base64-like string encoding the user_id and an expiry
    timestamp, signed with HMAC-SHA256.

    Args:
        user: The user to create a token for.

    Returns:
        A token string that can be passed to validate_token().
    """
    db = get_db()

    payload = {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
    }

    payload_json = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        TOKEN_SECRET.encode(),
        payload_json.encode(),
        hashlib.sha256,
    ).hexdigest()

    token = f"{payload_json}|{signature}"

    # Store token in the database for revocation support
    db["tokens"][token] = {
        "user_id": user.user_id,
        "created_at": time.time(),
        "revoked": False,
    }

    log_event("token_created", user_id=user.user_id)
    return token


def validate_token(token: str) -> bool:
    """Validate a token and set the current user on the thread-local.

    On success, sets threading.local().current_user to the authenticated
    User object. Downstream code (especially payments) relies on this
    side effect.

    Args:
        token: The token string to validate.

    Returns:
        True if the token is valid and the user was set, False otherwise.
    """
    db = get_db()

    try:
        payload_json, signature = token.rsplit("|", 1)
    except ValueError:
        log_event("token_invalid", level="warning", reason="malformed")
        set_current_user(None)
        return False

    # Verify signature
    expected_sig = hmac.new(
        TOKEN_SECRET.encode(),
        payload_json.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        log_event("token_invalid", level="warning", reason="bad_signature")
        set_current_user(None)
        return False

    payload = json.loads(payload_json)

    # Check expiry
    if payload.get("exp", 0) < time.time():
        log_event("token_expired", user_id=payload.get("user_id"))
        set_current_user(None)
        return False

    # Check revocation
    token_record = db["tokens"].get(token)
    if token_record and token_record.get("revoked"):
        log_event("token_revoked", user_id=payload.get("user_id"))
        set_current_user(None)
        return False

    # Look up the user
    user_id = payload["user_id"]
    user_data = db["users"].get(user_id)
    if user_data is None:
        log_event("token_user_not_found", user_id=user_id, level="warning")
        set_current_user(None)
        return False

    user = User.from_dict(user_data)

    if not user.is_active:
        log_event("token_user_inactive", user_id=user_id, level="warning")
        set_current_user(None)
        return False

    # --- THIS IS THE KEY SIDE EFFECT ---
    # Set the current user on the thread-local so downstream modules
    # (payments, api routes, etc.) can access it without explicit passing.
    set_current_user(user)

    log_event("token_validated", user_id=user_id)
    return True


def revoke_token(token: str) -> bool:
    """Revoke a token so it can no longer be used.

    Args:
        token: The token string to revoke.

    Returns:
        True if the token was found and revoked, False if not found.
    """
    db = get_db()
    token_record = db["tokens"].get(token)
    if token_record is None:
        return False
    token_record["revoked"] = True
    log_event("token_revoked_explicit", user_id=token_record["user_id"])
    return True
