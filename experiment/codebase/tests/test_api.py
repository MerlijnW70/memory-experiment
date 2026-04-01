"""Tests for the API layer."""

import pytest

from src.api.decorators import rate_limit, clear_rate_limits
from src.api.routes import handle_request
from src.api.serializers import (
    serialize_payment,
    serialize_subscription,
    serialize_user,
)
from src.auth.tokens import create_token, set_current_user
from src.config import get_db
from src.models.payment import Payment
from src.models.subscription import Subscription
from src.models.user import User
from src.users.manager import create_user
from src.payments.processor import process_payment
from src.payments.subscriptions import create_subscription
from src.utils.feature_flags import get_rate_limit


def _auth_headers(user: User) -> dict[str, str]:
    """Create Authorization headers for a user."""
    token = create_token(user)
    return {"Authorization": f"Bearer {token}"}


class TestSerializers:
    """Tests for API serializers — especially cents-to-dollars conversion."""

    def test_serialize_payment_converts_cents_to_dollars(self):
        """The API must expose amounts as dollar floats, not integer cents."""
        payment = Payment(user_id="u1", amount_cents=4999, status="completed")
        data = serialize_payment(payment)
        # The key is 'amount' (dollars), not 'amount_cents'
        assert "amount" in data
        assert "amount_cents" not in data
        assert data["amount"] == 49.99
        assert isinstance(data["amount"], float)

    def test_serialize_subscription_converts_cents_to_dollars(self):
        sub = Subscription(user_id="u1", plan="pro")
        data = serialize_subscription(sub)
        assert "price" in data
        assert "price_cents" not in data
        assert data["price"] == 29.99

    def test_serialize_user(self):
        user = User(username="testuser", email="test@example.com")
        data = serialize_user(user)
        assert data["username"] == "testuser"
        assert "id" in data


class TestRateLimitDecorator:
    """Tests for the rate limit decorator."""

    def test_rate_limit_reads_from_feature_flags(self):
        """Rate limit config comes from feature_flags, NOT config.py."""
        config = get_rate_limit("auth")
        assert config["requests_per_minute"] == 20

    def test_rate_limit_allows_normal_requests(self):
        @rate_limit(category="default")
        def handler(request, **kwargs):
            return {"status": 200}

        request = {"headers": {"X-Client-ID": "test-client"}, "params": {}}
        response = handler(request)
        assert response["status"] == 200

    def test_rate_limit_blocks_burst(self):
        """Exceeding burst_size in 1 second should trigger rate limiting."""
        @rate_limit(category="auth")
        def handler(request, **kwargs):
            return {"status": 200}

        # auth burst_size is 5
        request = {"headers": {"X-Client-ID": "burst-test"}, "params": {}}
        for _ in range(5):
            response = handler(request)
            assert response["status"] == 200

        response = handler(request)
        assert response["status"] == 429
        assert "Rate limited" in response["error"]


class TestRoutes:
    """Tests for API route handlers."""

    def test_create_user_via_api(self):
        response = handle_request(
            "POST", "/users",
            body={"username": "newuser", "email": "new@example.com"},
        )
        assert response["status"] == 201
        assert response["data"]["username"] == "newuser"

    def test_create_user_missing_fields(self):
        response = handle_request(
            "POST", "/users",
            body={"username": "onlyname"},
        )
        assert response["status"] == 400

    def test_get_me_requires_auth(self):
        response = handle_request("GET", "/me")
        assert response["status"] == 401

    def test_get_me_with_auth(self):
        user = create_user(username="meuser", email="me@example.com")
        headers = _auth_headers(user)
        response = handle_request("GET", "/me", headers=headers)
        assert response["status"] == 200
        assert response["data"]["username"] == "meuser"

    def test_create_payment_converts_dollars_to_cents(self):
        """API accepts dollars, but stores as cents internally."""
        user = create_user(username="payapi", email="payapi@example.com")
        headers = _auth_headers(user)
        response = handle_request(
            "POST", "/payments",
            headers=headers,
            body={"amount": 49.99, "description": "Test"},
        )
        assert response["status"] == 201
        # Response shows dollars
        assert response["data"]["amount"] == 49.99

        # But internally it's stored as cents
        db = get_db()
        payment_id = response["data"]["id"]
        stored = db["payments"][payment_id]
        assert stored["amount_cents"] == 4999

    def test_list_payments(self):
        user = create_user(username="listpay", email="lp@example.com")
        headers = _auth_headers(user)
        # Create a payment
        handle_request(
            "POST", "/payments",
            headers=headers,
            body={"amount": 10.00},
        )
        response = handle_request("GET", "/payments", headers=headers)
        assert response["status"] == 200
        assert len(response["data"]) == 1

    def test_create_subscription_via_api(self):
        user = create_user(username="subapi", email="subapi@example.com")
        headers = _auth_headers(user)
        response = handle_request(
            "POST", "/subscriptions",
            headers=headers,
            body={"plan": "basic"},
        )
        assert response["status"] == 201
        assert response["data"]["plan"] == "basic"
        assert response["data"]["price"] == 9.99

    def test_cancel_subscription_via_api(self):
        user = create_user(username="cansub", email="cansub@example.com")
        headers = _auth_headers(user)
        create_resp = handle_request(
            "POST", "/subscriptions",
            headers=headers,
            body={"plan": "pro"},
        )
        sub_id = create_resp["data"]["id"]
        response = handle_request(
            "DELETE", "/subscriptions",
            headers=headers,
            params={"subscription_id": sub_id},
        )
        assert response["status"] == 200
        assert response["data"]["status"] == "cancelled"

    def test_refund_requires_support_role(self):
        user = create_user(username="normaluser", email="norm@example.com")
        headers = _auth_headers(user)
        # Create a payment first
        set_current_user(user)
        payment = process_payment(amount_cents=1000)
        response = handle_request(
            "POST", "/refunds",
            headers=headers,
            body={"payment_id": payment.payment_id},
        )
        assert response["status"] == 403

    def test_refund_with_support_role(self):
        support = create_user(
            username="supportagent",
            email="support@example.com",
            role="support",
        )
        # Create a payment as a regular user
        regular = create_user(username="payer", email="payer@example.com")
        set_current_user(regular)
        payment = process_payment(amount_cents=3000)

        # Refund as support
        headers = _auth_headers(support)
        response = handle_request(
            "POST", "/refunds",
            headers=headers,
            body={"payment_id": payment.payment_id, "reason": "Duplicate"},
        )
        assert response["status"] == 201
        assert response["data"]["amount"] == 30.0

    def test_admin_list_users(self):
        admin = create_user(
            username="adminapi", email="admin@example.com", role="admin"
        )
        create_user(username="regularapi", email="reg@example.com")
        headers = _auth_headers(admin)
        response = handle_request("GET", "/admin/users", headers=headers)
        assert response["status"] == 200
        assert len(response["data"]) == 2

    def test_admin_list_users_forbidden_for_regular(self):
        user = create_user(username="notadmin", email="na@example.com")
        headers = _auth_headers(user)
        response = handle_request("GET", "/admin/users", headers=headers)
        assert response["status"] == 403

    def test_admin_delete_user(self):
        admin = create_user(
            username="deladmin", email="deladmin@example.com", role="admin"
        )
        target = create_user(
            username="target", email="target@example.com"
        )
        headers = _auth_headers(admin)
        response = handle_request(
            "DELETE", "/admin/users",
            headers=headers,
            params={"user_id": target.user_id},
        )
        assert response["status"] == 200
        assert response["data"]["deleted"] is True

    def test_unknown_route(self):
        response = handle_request("GET", "/nonexistent")
        assert response["status"] == 404
