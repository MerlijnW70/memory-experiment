"""Tests for authentication module."""

import pytest

from src.auth.tokens import (
    create_token,
    validate_token,
    get_current_user,
    set_current_user,
    clear_current_user,
    revoke_token,
)
from src.auth.middleware import authenticate_request, require_auth
from src.auth.permissions import has_permission, require_role
from src.config import get_db
from src.models.user import User
from src.users.manager import create_user


def _make_user(
    username: str = "testuser",
    email: str = "test@example.com",
    role: str = "user",
) -> User:
    """Helper to create a user and store in DB."""
    return create_user(username=username, email=email, role=role)


class TestTokens:
    """Tests for token creation and validation."""

    def test_create_and_validate_token(self):
        user = _make_user()
        token = create_token(user)
        assert validate_token(token) is True

    def test_validate_sets_current_user(self):
        """validate_token must set thread-local current_user."""
        user = _make_user()
        token = create_token(user)

        assert get_current_user() is None
        validate_token(token)
        current = get_current_user()
        assert current is not None
        assert current.user_id == user.user_id

    def test_invalid_token_returns_false(self):
        assert validate_token("garbage-token") is False
        assert get_current_user() is None

    def test_tampered_token_fails(self):
        user = _make_user()
        token = create_token(user)
        tampered = token[:-5] + "XXXXX"
        assert validate_token(tampered) is False

    def test_revoke_token(self):
        user = _make_user()
        token = create_token(user)
        assert validate_token(token) is True
        clear_current_user()
        revoke_token(token)
        assert validate_token(token) is False

    def test_inactive_user_token_fails(self):
        user = _make_user()
        token = create_token(user)
        # Deactivate user
        db = get_db()
        db["users"][user.user_id]["is_active"] = False
        assert validate_token(token) is False

    def test_clear_current_user(self):
        user = _make_user()
        set_current_user(user)
        assert get_current_user() is not None
        clear_current_user()
        assert get_current_user() is None


class TestMiddleware:
    """Tests for auth middleware."""

    def test_authenticate_with_bearer_token(self):
        user = _make_user()
        token = create_token(user)
        request = {"headers": {"Authorization": f"Bearer {token}"}, "params": {}}
        error = authenticate_request(request)
        assert error is None
        assert get_current_user() is not None

    def test_authenticate_with_param_token(self):
        user = _make_user()
        token = create_token(user)
        request = {"headers": {}, "params": {"token": token}}
        error = authenticate_request(request)
        assert error is None

    def test_missing_token_returns_error(self):
        request = {"headers": {}, "params": {}}
        error = authenticate_request(request)
        assert error is not None

    def test_require_auth_decorator(self):
        user = _make_user()
        token = create_token(user)

        @require_auth
        def my_handler(request, **kwargs):
            return {"status": 200, "data": "ok"}

        # With valid auth
        response = my_handler({"headers": {"Authorization": f"Bearer {token}"}, "params": {}})
        assert response["status"] == 200

        # Without auth
        response = my_handler({"headers": {}, "params": {}})
        assert response["status"] == 401


class TestPermissions:
    """Tests for role-based permissions."""

    def test_user_has_basic_permission(self):
        user = _make_user(role="user")
        set_current_user(user)
        assert has_permission("view_own_profile") is True

    def test_user_lacks_admin_permission(self):
        user = _make_user(role="user")
        set_current_user(user)
        assert has_permission("delete_user") is False

    def test_admin_has_all_permissions(self):
        user = _make_user(username="admin_user", email="admin@example.com", role="admin")
        set_current_user(user)
        assert has_permission("delete_user") is True
        assert has_permission("view_own_profile") is True

    def test_support_has_mid_level(self):
        user = _make_user(username="support_user", email="support@example.com", role="support")
        set_current_user(user)
        assert has_permission("issue_refund") is True
        assert has_permission("delete_user") is False

    def test_no_user_returns_false(self):
        clear_current_user()
        assert has_permission("view_own_profile") is False

    def test_require_role_decorator(self):
        user = _make_user(role="user")
        set_current_user(user)

        @require_role("admin")
        def admin_only(request, **kwargs):
            return {"status": 200}

        response = admin_only({})
        assert response["status"] == 403
