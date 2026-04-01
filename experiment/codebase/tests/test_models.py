"""Tests for data models."""

import pytest

from src.models.user import User
from src.models.payment import Payment
from src.models.subscription import Subscription


class TestUserModel:
    """Tests for the User model."""

    def test_create_user(self):
        user = User(username="alice", email="alice@example.com")
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.role == "user"
        assert user.is_active is True
        assert user.user_id  # auto-generated

    def test_user_to_dict_roundtrip(self):
        user = User(username="bob", email="bob@example.com", role="admin")
        data = user.to_dict()
        restored = User.from_dict(data)
        assert restored.username == user.username
        assert restored.email == user.email
        assert restored.role == user.role
        assert restored.user_id == user.user_id

    def test_user_default_metadata(self):
        user = User(username="charlie", email="c@example.com")
        assert user.metadata == {}


class TestPaymentModel:
    """Tests for the Payment model."""

    def test_create_payment_cents(self):
        """Payment amounts are stored as integer cents."""
        payment = Payment(user_id="u1", amount_cents=4999)
        assert payment.amount_cents == 4999
        assert isinstance(payment.amount_cents, int)

    def test_payment_rejects_float_amount(self):
        """Payment must reject non-integer amounts."""
        with pytest.raises(TypeError, match="amount_cents must be int"):
            Payment(user_id="u1", amount_cents=49.99)

    def test_payment_rejects_negative(self):
        with pytest.raises(ValueError, match="non-negative"):
            Payment(user_id="u1", amount_cents=-100)

    def test_payment_to_dict_roundtrip(self):
        payment = Payment(
            user_id="u1",
            amount_cents=2500,
            description="Monthly charge",
            status="completed",
        )
        data = payment.to_dict()
        restored = Payment.from_dict(data)
        assert restored.amount_cents == 2500
        assert restored.description == "Monthly charge"
        assert restored.payment_id == payment.payment_id

    def test_payment_default_status(self):
        payment = Payment(user_id="u1", amount_cents=100)
        assert payment.status == "pending"


class TestSubscriptionModel:
    """Tests for the Subscription model."""

    def test_create_subscription_auto_price(self):
        """Plan price should be auto-set from PLAN_PRICES_CENTS."""
        sub = Subscription(user_id="u1", plan="pro")
        assert sub.price_cents == 2999
        assert sub.status == "active"

    def test_subscription_invalid_plan(self):
        with pytest.raises(ValueError, match="Invalid plan"):
            Subscription(user_id="u1", plan="unlimited")

    def test_subscription_to_dict_roundtrip(self):
        sub = Subscription(user_id="u1", plan="basic")
        data = sub.to_dict()
        restored = Subscription.from_dict(data)
        assert restored.plan == "basic"
        assert restored.price_cents == 999
        assert restored.subscription_id == sub.subscription_id

    def test_subscription_enterprise_price(self):
        sub = Subscription(user_id="u1", plan="enterprise")
        assert sub.price_cents == 9999
