"""User management module.

Handles user CRUD, profiles, and notifications.
"""

from src.users.manager import create_user, get_user, update_user, delete_user
from src.users.profile import get_profile, update_profile

__all__ = [
    "create_user",
    "get_user",
    "update_user",
    "delete_user",
    "get_profile",
    "update_profile",
]
