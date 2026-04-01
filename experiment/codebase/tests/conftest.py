"""Shared test fixtures."""

import pytest

from src.config import reset_db
from src.auth.tokens import clear_current_user
from src.api.decorators import clear_rate_limits
from src.users.notifications import clear_notifications
from src.utils.logging import clear_log_buffer


@pytest.fixture(autouse=True)
def clean_state():
    """Reset all global state before each test."""
    reset_db()
    clear_current_user()
    clear_rate_limits()
    clear_notifications()
    clear_log_buffer()
    yield
    reset_db()
    clear_current_user()
    clear_rate_limits()
    clear_notifications()
    clear_log_buffer()
