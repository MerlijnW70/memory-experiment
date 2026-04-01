"""Feature flags and operational toggles.

This module centralizes runtime feature configuration including A/B test
flags, gradual rollout percentages, and operational knobs like rate limiting.
Keeping these separate from config.py allows product and ops changes without
touching infrastructure configuration.
"""

from typing import Any


# --- Feature Flags ---

FEATURES: dict[str, bool] = {
    "new_checkout_flow": False,
    "enhanced_fraud_detection": True,
    "email_verification_required": True,
    "allow_guest_checkout": False,
    "subscription_pause_enabled": True,
}


def is_enabled(flag_name: str) -> bool:
    """Check whether a feature flag is enabled.

    Args:
        flag_name: The name of the feature flag.

    Returns:
        True if the flag exists and is enabled, False otherwise.
    """
    return FEATURES.get(flag_name, False)


def set_flag(flag_name: str, enabled: bool) -> None:
    """Set a feature flag value. Primarily used in tests.

    Args:
        flag_name: The name of the feature flag.
        enabled: Whether the flag should be enabled.
    """
    FEATURES[flag_name] = enabled


# --- Rate Limiting Configuration ---
# Rate limiting config lives here (not in config.py) because it is
# considered an operational toggle that product/ops teams adjust
# independently of infrastructure settings.

RATE_LIMITS: dict[str, dict[str, Any]] = {
    "default": {
        "requests_per_minute": 60,
        "burst_size": 10,
    },
    "auth": {
        "requests_per_minute": 20,
        "burst_size": 5,
    },
    "payments": {
        "requests_per_minute": 30,
        "burst_size": 5,
    },
    "admin": {
        "requests_per_minute": 120,
        "burst_size": 20,
    },
}


def get_rate_limit(category: str = "default") -> dict[str, Any]:
    """Return rate limit configuration for a given category.

    Falls back to the 'default' category if the requested one is not found.

    Args:
        category: The rate limit category (e.g. 'auth', 'payments').

    Returns:
        Dict with 'requests_per_minute' and 'burst_size' keys.
    """
    return RATE_LIMITS.get(category, RATE_LIMITS["default"]).copy()
