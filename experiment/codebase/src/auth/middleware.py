"""Authentication middleware.

Simulates HTTP middleware that extracts a token from the request,
validates it, and populates the thread-local current_user.
"""

from typing import Any, Callable, Optional

from src.auth.tokens import validate_token, clear_current_user
from src.utils.logging import log_event


def authenticate_request(request: dict[str, Any]) -> Optional[str]:
    """Extract and validate the auth token from a request dict.

    Looks for the token in the 'Authorization' header (Bearer scheme) or
    in the 'token' query parameter as a fallback.

    Args:
        request: A dict simulating an HTTP request with 'headers' and
                 optionally 'params' keys.

    Returns:
        None on success (current_user is set on the thread-local),
        or an error message string on failure.
    """
    headers = request.get("headers", {})
    params = request.get("params", {})

    token = None

    # Try Authorization header first
    auth_header = headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif "token" in params:
        token = params["token"]

    if not token:
        log_event("auth_missing_token", level="warning")
        return "Authentication required"

    if not validate_token(token):
        return "Invalid or expired token"

    return None


def require_auth(handler: Callable) -> Callable:
    """Decorator that enforces authentication on a request handler.

    The handler receives (request, **kwargs). If authentication fails,
    an error response dict is returned instead of calling the handler.

    Args:
        handler: The request handler function.

    Returns:
        Wrapped handler that checks auth first.
    """
    def wrapper(request: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        error = authenticate_request(request)
        if error:
            return {"status": 401, "error": error}
        try:
            return handler(request, **kwargs)
        finally:
            clear_current_user()

    wrapper.__name__ = handler.__name__
    wrapper.__doc__ = handler.__doc__
    return wrapper
