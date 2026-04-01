"""Tests for utility modules."""

import pytest

from src.utils.money import cents_to_dollars, dollars_to_cents, format_dollars
from src.utils.validation import (
    validate_email,
    validate_username,
    validate_amount,
    validate_required_fields,
    sanitize_string,
)
from src.utils.feature_flags import is_enabled, set_flag, get_rate_limit
from src.utils.logging import log_event, get_log_buffer


class TestMoney:
    """Tests for cents/dollars conversion."""

    def test_cents_to_dollars_basic(self):
        assert cents_to_dollars(1000) == 10.0

    def test_cents_to_dollars_with_remainder(self):
        assert cents_to_dollars(1299) == 12.99

    def test_cents_to_dollars_zero(self):
        assert cents_to_dollars(0) == 0.0

    def test_cents_to_dollars_one_cent(self):
        assert cents_to_dollars(1) == 0.01

    def test_cents_to_dollars_rejects_negative(self):
        with pytest.raises(ValueError):
            cents_to_dollars(-100)

    def test_cents_to_dollars_rejects_float(self):
        with pytest.raises(TypeError):
            cents_to_dollars(10.5)

    def test_dollars_to_cents_basic(self):
        assert dollars_to_cents(10.0) == 1000

    def test_dollars_to_cents_with_remainder(self):
        assert dollars_to_cents(12.99) == 1299

    def test_dollars_to_cents_from_string(self):
        assert dollars_to_cents("49.99") == 4999

    def test_dollars_to_cents_from_int(self):
        assert dollars_to_cents(5) == 500

    def test_dollars_to_cents_rejects_negative(self):
        with pytest.raises(ValueError):
            dollars_to_cents(-10.0)

    def test_dollars_to_cents_rejects_garbage(self):
        with pytest.raises(ValueError):
            dollars_to_cents("not-a-number")

    def test_format_dollars(self):
        assert format_dollars(4999) == "$49.99"

    def test_format_dollars_round(self):
        assert format_dollars(1000) == "$10.00"


class TestValidation:
    """Tests for input validation."""

    def test_valid_email(self):
        assert validate_email("user@example.com") is True

    def test_invalid_email_no_at(self):
        assert validate_email("userexample.com") is False

    def test_invalid_email_type(self):
        assert validate_email(123) is False

    def test_valid_username(self):
        assert validate_username("alice_42") is True

    def test_invalid_username_short(self):
        assert validate_username("ab") is False

    def test_invalid_username_special(self):
        assert validate_username("user@name") is False

    def test_validate_amount_int(self):
        assert validate_amount(100) is True

    def test_validate_amount_float(self):
        assert validate_amount(9.99) is True

    def test_validate_amount_negative(self):
        assert validate_amount(-1) is False

    def test_validate_amount_bool(self):
        assert validate_amount(True) is False

    def test_validate_required_fields_ok(self):
        data = {"name": "Alice", "email": "alice@example.com"}
        assert validate_required_fields(data, ["name", "email"]) is None

    def test_validate_required_fields_missing(self):
        data = {"name": "Alice"}
        result = validate_required_fields(data, ["name", "email"])
        assert result is not None
        assert "email" in result

    def test_sanitize_string(self):
        assert sanitize_string("  hello  ") == "hello"

    def test_sanitize_string_truncate(self):
        assert len(sanitize_string("a" * 300, max_length=10)) == 10


class TestFeatureFlags:
    """Tests for feature flag system."""

    def test_is_enabled_default(self):
        assert is_enabled("enhanced_fraud_detection") is True

    def test_is_enabled_missing_flag(self):
        assert is_enabled("nonexistent_flag") is False

    def test_set_flag(self):
        set_flag("test_flag", True)
        assert is_enabled("test_flag") is True
        set_flag("test_flag", False)
        assert is_enabled("test_flag") is False

    def test_get_rate_limit_default(self):
        config = get_rate_limit("default")
        assert "requests_per_minute" in config
        assert "burst_size" in config

    def test_get_rate_limit_specific(self):
        config = get_rate_limit("auth")
        assert config["requests_per_minute"] == 20

    def test_get_rate_limit_fallback(self):
        config = get_rate_limit("nonexistent")
        assert config == get_rate_limit("default")


class TestLogging:
    """Tests for structured logging."""

    def test_log_event_records(self):
        log_event("test_event", user_id="u123")
        buffer = get_log_buffer()
        assert len(buffer) == 1
        assert buffer[0]["event"] == "test_event"
        assert buffer[0]["user_id"] == "u123"

    def test_log_event_has_timestamp(self):
        entry = log_event("something")
        assert "timestamp" in entry
