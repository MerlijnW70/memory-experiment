"""Role-based permission checks.

Works with the thread-local current_user set by auth.tokens.validate_token().
"""

from typing import Callable, Any

from src.auth.tokens import get_current_user
from src.utils.logging import log_event


# Role hierarchy: higher index = more privileged
ROLE_HIERARCHY = {
    "user": 0,
    "support": 1,
    "admin": 2,
}

# Permission matrix: permission_name -> minimum required role
PERMISSIONS = {
    "view_own_profile": "user",
    "edit_own_profile": "user",
    "make_payment": "user",
    "view_own_payments": "user",
    "view_all_users": "support",
    "view_all_payments": "support",
    "issue_refund": "support",
    "delete_user": "admin",
    "manage_subscriptions": "admin",
    "view_system_logs": "admin",
}


def has_permission(permission: str) -> bool:
    """Check if the current user has the given permission.

    Reads the current user from the thread-local. Returns False if no user
    is authenticated.

    Args:
        permission: The permission name to check.

    Returns:
        True if the user's role meets or exceeds the required level.
    """
    user = get_current_user()
    if user is None:
        return False

    required_role = PERMISSIONS.get(permission)
    if required_role is None:
        log_event(
            "unknown_permission",
            level="warning",
            permission=permission,
        )
        return False

    user_level = ROLE_HIERARCHY.get(user.role, -1)
    required_level = ROLE_HIERARCHY.get(required_role, 999)

    return user_level >= required_level


def require_role(minimum_role: str) -> Callable:
    """Decorator that enforces a minimum role on a handler.

    Must be used after authentication (the current_user must already be set).

    Args:
        minimum_role: The minimum role required (e.g. 'admin').

    Returns:
        Decorator function.
    """
    def decorator(handler: Callable) -> Callable:
        def wrapper(request: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            user = get_current_user()
            if user is None:
                return {"status": 401, "error": "Authentication required"}

            user_level = ROLE_HIERARCHY.get(user.role, -1)
            required_level = ROLE_HIERARCHY.get(minimum_role, 999)

            if user_level < required_level:
                log_event(
                    "permission_denied",
                    level="warning",
                    user_id=user.user_id,
                    required_role=minimum_role,
                    actual_role=user.role,
                )
                return {
                    "status": 403,
                    "error": f"Requires {minimum_role} role",
                }

            return handler(request, **kwargs)

        wrapper.__name__ = handler.__name__
        wrapper.__doc__ = handler.__doc__
        return wrapper

    return decorator
