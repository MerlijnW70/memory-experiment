"""Authentication and authorization module.

This module handles token validation, middleware, and permission checks.
Token validation sets a thread-local `current_user` that downstream modules
(notably payments) rely on implicitly.
"""

from src.auth.tokens import validate_token, create_token, get_current_user
from src.auth.permissions import require_role, has_permission

__all__ = [
    "validate_token",
    "create_token",
    "get_current_user",
    "require_role",
    "has_permission",
]
