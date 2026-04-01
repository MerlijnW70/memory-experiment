"""Input validation helpers.

Provides reusable validation functions for common data formats used
throughout the application.
"""

import re
from typing import Any, Optional


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


def validate_email(email: str) -> bool:
    """Check whether a string is a valid email address.

    Args:
        email: The string to validate.

    Returns:
        True if the email is syntactically valid.
    """
    if not isinstance(email, str):
        return False
    return EMAIL_REGEX.match(email) is not None


def validate_username(username: str) -> bool:
    """Check whether a username meets format requirements.

    Usernames must be 3-32 characters, alphanumeric plus underscores.

    Args:
        username: The string to validate.

    Returns:
        True if valid.
    """
    if not isinstance(username, str):
        return False
    return USERNAME_REGEX.match(username) is not None


def validate_amount(amount: Any) -> bool:
    """Check whether a value is a valid monetary amount.

    Accepts int or float, must be non-negative.

    Args:
        amount: The value to check.

    Returns:
        True if amount is a valid non-negative number.
    """
    if isinstance(amount, bool):
        return False
    if not isinstance(amount, (int, float)):
        return False
    return amount >= 0


def validate_required_fields(
    data: dict[str, Any],
    required: list[str],
) -> Optional[str]:
    """Check that all required fields are present and non-empty in a dict.

    Args:
        data: The input dictionary.
        required: List of required field names.

    Returns:
        An error message string if validation fails, or None if all fields
        are present.
    """
    for field in required:
        if field not in data or data[field] is None or data[field] == "":
            return f"Missing required field: {field}"
    return None


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Strip whitespace and truncate a string to max_length.

    Args:
        value: The input string.
        max_length: Maximum allowed length.

    Returns:
        The sanitized string.
    """
    return value.strip()[:max_length]
