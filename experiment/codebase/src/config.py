"""Application configuration.

Central configuration for database, logging, and application settings.
Note: Feature-specific configuration (A/B tests, feature flags, operational
toggles) lives in utils/feature_flags.py to keep this file focused on
infrastructure concerns.
"""

from typing import Any


# --- Database Configuration ---

DATABASE: dict[str, dict[str, Any]] = {
    "users": {},
    "payments": {},
    "subscriptions": {},
    "tokens": {},
}


def get_db() -> dict[str, dict[str, Any]]:
    """Return the in-memory database reference."""
    return DATABASE


def reset_db() -> None:
    """Clear all tables. Used in tests."""
    for table in DATABASE.values():
        table.clear()


# --- Application Settings ---

APP_NAME = "billing-platform"
APP_VERSION = "2.4.1"
DEBUG = False

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "json"

# Token settings
TOKEN_SECRET = "super-secret-key-change-in-production"
TOKEN_EXPIRY_SECONDS = 3600

# Payment processor
PAYMENT_GATEWAY_URL = "https://payments.internal.example.com/v2"
PAYMENT_RETRY_ATTEMPTS = 3
PAYMENT_TIMEOUT_SECONDS = 30

# Notification settings
NOTIFICATION_EMAIL_FROM = "billing@example.com"
SMTP_HOST = "smtp.internal.example.com"
SMTP_PORT = 587
