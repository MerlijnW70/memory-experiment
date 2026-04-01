"""Tests for the payments module."""

import pytest

from src.auth.tokens import set_current_user, clear_current_user
from src.config import get_db
from src.models.payment import Payment
from src.models.user import User
from src.payments.processor import process_payment, get_user_payments
from src.payments.subscriptions import (
    create_subscription,
    cancel_subscription,
    get_user_subscriptions,
    cancel_all_user_subscriptions,
)
from src.payments.refunds import process_refund
from src.users.manager import create_user


def _setup_user(
    username: str = "payuser",
    email: str = "pay@example.com",
    role: str = "user",
) -> User:
    """Create a user and set as current authenticated user."""
    user = create_user(username=username, email=email, role=role)
    set_current_user(user)
    return user


class TestPaymentProcessor:
    """Tests for payment processing."""

    def test_process_payment_requires_auth(self):
        """Payment fails if no current_user is set (the implicit contract)."""
        clear_current_user()
        with pytest.raises(RuntimeError, match="No authenticated user"):
            process_payment(amount_cents=1000)

    def test_process_payment_success(self):
        user = _setup_user()
        payment = process_payment(
            amount_cents=2500,
            description="Test charge",
        )
        assert payment.amount_cents == 2500
        assert payment.user_id == user.user_id
        assert payment.status == "completed"

    def test_process_payment_stored_in_db(self):
        user = _setup_user()
        payment = process_payment(amount_cents=1000)
        db = get_db()
        assert payment.payment_id in db["payments"]

    def test_process_payment_invalid_amount(self):
        _setup_user()
        with pytest.raises(ValueError):
            process_payment(amount_cents=0)

    def test_get_user_payments(self):
        user = _setup_user()
        process_payment(amount_cents=500, description="First")
        process_payment(amount_cents=1500, description="Second")
        payments = get_user_payments(user.user_id)
        assert len(payments) == 2

    def test_get_user_payments_default_current_user(self):
        user = _setup_user()
        process_payment(amount_cents=999)
        # Don't pass user_id, should use current_user
        payments = get_user_payments()
        assert len(payments) == 1
        assert payments[0].user_id == user.user_id


class TestSubscriptions:
    """Tests for subscription management."""

    def test_create_subscription(self):
        user = _setup_user()
        sub = create_subscription(plan="pro")
        assert sub.plan == "pro"
        assert sub.price_cents == 2999
        assert sub.user_id == user.user_id
        assert sub.status == "active"

    def test_create_subscription_requires_auth(self):
        clear_current_user()
        with pytest.raises(RuntimeError):
            create_subscription(plan="basic")

    def test_create_subscription_explicit_user_id(self):
        user = _setup_user()
        clear_current_user()
        # Should work with explicit user_id even without auth
        sub = create_subscription(plan="basic", user_id=user.user_id)
        assert sub.user_id == user.user_id

    def test_no_duplicate_active_subscription(self):
        _setup_user()
        create_subscription(plan="basic")
        with pytest.raises(ValueError, match="already has an active"):
            create_subscription(plan="pro")

    def test_cancel_subscription(self):
        _setup_user()
        sub = create_subscription(plan="basic")
        result = cancel_subscription(sub.subscription_id)
        assert result is not None
        assert result.status == "cancelled"
        assert result.cancelled_at is not None

    def test_cancel_nonexistent(self):
        result = cancel_subscription("fake-id")
        assert result is None

    def test_cancel_all_user_subscriptions(self):
        user = _setup_user()
        sub1 = create_subscription(plan="basic")
        # Cancel first so we can create second
        cancel_subscription(sub1.subscription_id)
        create_subscription(plan="pro")

        cancelled = cancel_all_user_subscriptions(user.user_id)
        # Only the active 'pro' should be cancelled (basic was already cancelled)
        assert cancelled == 1

        subs = get_user_subscriptions(user.user_id)
        active = [s for s in subs if s.status == "active"]
        assert len(active) == 0

    def test_get_user_subscriptions(self):
        user = _setup_user()
        create_subscription(plan="enterprise")
        subs = get_user_subscriptions(user.user_id)
        assert len(subs) == 1
        assert subs[0].plan == "enterprise"


class TestRefunds:
    """Tests for refund processing."""

    def test_process_full_refund(self):
        _setup_user()
        payment = process_payment(amount_cents=5000, description="Charge")
        refund = process_refund(payment.payment_id, reason="Customer request")
        assert refund is not None
        assert refund.amount_cents == 5000
        assert refund.status == "refunded"
        assert refund.refund_reason == "Customer request"

    def test_process_partial_refund(self):
        _setup_user()
        payment = process_payment(amount_cents=5000)
        refund = process_refund(payment.payment_id, amount_cents=2000)
        assert refund.amount_cents == 2000

    def test_refund_exceeds_original(self):
        _setup_user()
        payment = process_payment(amount_cents=1000)
        with pytest.raises(ValueError, match="exceeds original"):
            process_refund(payment.payment_id, amount_cents=2000)

    def test_refund_nonexistent_payment(self):
        result = process_refund("fake-id")
        assert result is None

    def test_refund_already_refunded(self):
        _setup_user()
        payment = process_payment(amount_cents=1000)
        process_refund(payment.payment_id)
        # Original is now 'refunded', second refund should fail
        result = process_refund(payment.payment_id)
        assert result is None
