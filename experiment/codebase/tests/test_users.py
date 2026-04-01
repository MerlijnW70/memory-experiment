"""Tests for the users module."""

import pytest

from src.auth.tokens import set_current_user
from src.config import get_db
from src.users.manager import (
    create_user,
    get_user,
    get_user_by_username,
    update_user,
    delete_user,
    list_users,
)
from src.users.profile import get_profile, update_profile
from src.users.notifications import get_sent_notifications
from src.payments.subscriptions import (
    create_subscription,
    get_user_subscriptions,
)


class TestUserManager:
    """Tests for user CRUD operations."""

    def test_create_user(self):
        user = create_user(
            username="alice",
            email="alice@example.com",
            display_name="Alice Smith",
        )
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.display_name == "Alice Smith"
        assert user.is_active is True

    def test_create_user_sends_welcome(self):
        user = create_user(username="bob", email="bob@example.com")
        notifs = get_sent_notifications(user.user_id, "welcome")
        assert len(notifs) == 1

    def test_create_user_invalid_username(self):
        with pytest.raises(ValueError, match="Invalid username"):
            create_user(username="ab", email="ab@example.com")

    def test_create_user_invalid_email(self):
        with pytest.raises(ValueError, match="Invalid email"):
            create_user(username="validuser", email="not-an-email")

    def test_create_user_duplicate_username(self):
        create_user(username="unique", email="a@example.com")
        with pytest.raises(ValueError, match="already taken"):
            create_user(username="unique", email="b@example.com")

    def test_create_user_duplicate_email(self):
        create_user(username="user_one", email="same@example.com")
        with pytest.raises(ValueError, match="already registered"):
            create_user(username="user_two", email="same@example.com")

    def test_get_user(self):
        user = create_user(username="charlie", email="c@example.com")
        found = get_user(user.user_id)
        assert found is not None
        assert found.username == "charlie"

    def test_get_user_not_found(self):
        assert get_user("nonexistent-id") is None

    def test_get_user_by_username(self):
        create_user(username="findme", email="findme@example.com")
        found = get_user_by_username("findme")
        assert found is not None
        assert found.email == "findme@example.com"

    def test_update_user(self):
        user = create_user(username="updatable", email="up@example.com")
        updated = update_user(user.user_id, display_name="New Name")
        assert updated is not None
        assert updated.display_name == "New Name"

    def test_update_user_invalid_field(self):
        user = create_user(username="badfield", email="bf@example.com")
        with pytest.raises(ValueError, match="Cannot update"):
            update_user(user.user_id, username="newname")

    def test_update_user_not_found(self):
        assert update_user("fake-id", display_name="X") is None

    def test_delete_user(self):
        user = create_user(username="deleteme", email="del@example.com")
        assert delete_user(user.user_id) is True
        assert get_user(user.user_id) is None

    def test_delete_user_not_found(self):
        assert delete_user("fake-id") is False

    def test_delete_user_cancels_subscriptions(self):
        """CRITICAL: delete_user must clean up active subscriptions."""
        user = create_user(username="subuser", email="sub@example.com")
        set_current_user(user)
        create_subscription(plan="pro")

        # Verify subscription exists
        subs = get_user_subscriptions(user.user_id)
        assert len(subs) == 1
        assert subs[0].status == "active"

        # Delete user
        delete_user(user.user_id)

        # Subscription should now be cancelled
        subs = get_user_subscriptions(user.user_id)
        assert all(s.status == "cancelled" for s in subs)

    def test_delete_user_revokes_tokens(self):
        user = create_user(username="tokenuser", email="tok@example.com")
        from src.auth.tokens import create_token
        token = create_token(user)

        delete_user(user.user_id)

        db = get_db()
        token_record = db["tokens"].get(token)
        assert token_record is not None
        assert token_record["revoked"] is True

    def test_list_users(self):
        create_user(username="user_a", email="a@example.com")
        create_user(username="user_b", email="b@example.com")
        users = list_users()
        assert len(users) == 2

    def test_list_users_excludes_inactive(self):
        user = create_user(username="inactive_user", email="i@example.com")
        update_user(user.user_id, is_active=False)
        active = list_users(include_inactive=False)
        all_users = list_users(include_inactive=True)
        assert len(active) == 0
        assert len(all_users) == 1


class TestProfile:
    """Tests for profile management."""

    def test_get_profile(self):
        user = create_user(
            username="profuser",
            email="prof@example.com",
            display_name="Profile User",
        )
        profile = get_profile(user.user_id)
        assert profile is not None
        assert profile["display_name"] == "Profile User"
        assert profile["email"] == "prof@example.com"

    def test_get_profile_not_found(self):
        assert get_profile("fake-id") is None

    def test_get_profile_fallback_display_name(self):
        """If no display_name, username is used."""
        user = create_user(username="noname", email="nn@example.com")
        profile = get_profile(user.user_id)
        assert profile["display_name"] == "noname"

    def test_update_profile(self):
        user = create_user(username="editable", email="ed@example.com")
        profile = update_profile(
            user.user_id,
            display_name="New Display",
            metadata={"theme": "dark"},
        )
        assert profile is not None
        assert profile["display_name"] == "New Display"
        assert profile["metadata"]["theme"] == "dark"

    def test_update_profile_invalid_email(self):
        user = create_user(username="bademail", email="be@example.com")
        with pytest.raises(ValueError, match="Invalid email"):
            update_profile(user.user_id, email="not-valid")

    def test_update_profile_not_found(self):
        assert update_profile("fake-id", display_name="X") is None
