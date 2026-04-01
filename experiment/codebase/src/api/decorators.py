"""API decorators.

ATYPICAL PATTERN: The @rate_limit decorator reads its configuration from
utils.feature_flags (NOT from config.py). This is because rate limits are
treated as operational toggles managed by the product/ops team, not as
infrastructure configuration. If you're looking for rate limit settings,
check utils/feature_flags.py, not config.py.
"""

import time
from collections import defaultdict
from typing import Any, Callable, Optional

from src.utils.feature_flags import get_rate_limit
from src.utils.logging import log_event


# In-memory rate limit tracking: {category: {client_key: [timestamps]}}
_rate_limit_buckets: dict[str, dict[str, list[float]]] = defaultdict(
    lambda: defaultdict(list)
)


def _get_client_key(request: dict[str, Any]) -> str:
    """Extract a client identifier from a request for rate limiting."""
    headers = request.get("headers", {})
    return headers.get("X-Client-ID", headers.get("Authorization", "anonymous"))


def _check_rate_limit(client_key: str, category: str) -> Optional[str]:
    """Check if the client has exceeded the rate limit.

    Args:
        client_key: Identifier for the client.
        category: Rate limit category (looked up in feature_flags).

    Returns:
        None if within limits, or an error message if rate limited.
    """
    config = get_rate_limit(category)
    max_requests = config["requests_per_minute"]
    burst_size = config["burst_size"]

    now = time.time()
    window_start = now - 60  # 1-minute sliding window

    bucket = _rate_limit_buckets[category][client_key]

    # Prune old entries
    _rate_limit_buckets[category][client_key] = [
        ts for ts in bucket if ts > window_start
    ]
    bucket = _rate_limit_buckets[category][client_key]

    # Check burst (requests in the last second)
    recent = [ts for ts in bucket if ts > now - 1]
    if len(recent) >= burst_size:
        return f"Rate limited: burst limit ({burst_size}/s) exceeded"

    # Check sustained rate
    if len(bucket) >= max_requests:
        return f"Rate limited: {max_requests} requests/minute exceeded"

    # Record this request
    bucket.append(now)
    return None


def rate_limit(category: str = "default") -> Callable:
    """Decorator that enforces rate limiting on an API handler.

    Rate limit configuration is read from utils.feature_flags.get_rate_limit(),
    NOT from config.py.

    Args:
        category: The rate limit category to apply. Must match a key in
                  feature_flags.RATE_LIMITS.

    Returns:
        Decorator function.
    """
    def decorator(handler: Callable) -> Callable:
        def wrapper(request: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            client_key = _get_client_key(request)
            error = _check_rate_limit(client_key, category)
            if error:
                log_event(
                    "rate_limited",
                    level="warning",
                    client_key=client_key,
                    category=category,
                )
                return {"status": 429, "error": error}
            return handler(request, **kwargs)

        wrapper.__name__ = handler.__name__
        wrapper.__doc__ = handler.__doc__
        return wrapper

    return decorator


def clear_rate_limits() -> None:
    """Reset all rate limit buckets. Used in tests."""
    _rate_limit_buckets.clear()
