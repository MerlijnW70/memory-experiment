"""API route handlers.

Simulates a simple HTTP routing system. Each handler receives a request dict
and returns a response dict. Routes are dispatched via handle_request().
"""

from typing import Any, Callable, Optional

from src.api.decorators import rate_limit
from src.api.serializers import (
    serialize_error,
    serialize_list,
    serialize_payment,
    serialize_subscription,
    serialize_user,
)
from src.auth.middleware import require_auth
from src.auth.permissions import has_permission
from src.auth.tokens import get_current_user
from src.payments.processor import get_user_payments, process_payment
from src.payments.subscriptions import (
    cancel_subscription,
    create_subscription,
    get_user_subscriptions,
)
from src.payments.refunds import process_refund
from src.users.manager import (
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)
from src.users.profile import get_profile, update_profile
from src.utils.logging import log_event
from src.utils.money import dollars_to_cents
from src.utils.validation import validate_required_fields


# --- Route Registry ---

_routes: dict[str, Callable] = {}


def _register(method_path: str) -> Callable:
    """Register a handler for a method+path combination."""
    def decorator(handler: Callable) -> Callable:
        _routes[method_path] = handler
        return handler
    return decorator


# --- Public Endpoints ---

@_register("POST /users")
@rate_limit(category="default")
def create_user_handler(request: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Create a new user account."""
    body = request.get("body", {})
    error = validate_required_fields(body, ["username", "email"])
    if error:
        return serialize_error(400, error)

    try:
        user = create_user(
            username=body["username"],
            email=body["email"],
            role=body.get("role", "user"),
            display_name=body.get("display_name"),
        )
        return {"status": 201, "data": serialize_user(user)}
    except ValueError as e:
        return serialize_error(400, str(e))


# --- Authenticated Endpoints ---

@_register("GET /me")
@require_auth
@rate_limit(category="default")
def get_me_handler(request: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Get the current user's profile."""
    user = get_current_user()
    profile = get_profile(user.user_id)
    return {"status": 200, "data": profile}


@_register("PUT /me")
@require_auth
@rate_limit(category="default")
def update_me_handler(request: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Update the current user's profile."""
    user = get_current_user()
    body = request.get("body", {})
    try:
        profile = update_profile(
            user_id=user.user_id,
            display_name=body.get("display_name"),
            email=body.get("email"),
            metadata=body.get("metadata"),
        )
        return {"status": 200, "data": profile}
    except ValueError as e:
        return serialize_error(400, str(e))


@_register("POST /payments")
@require_auth
@rate_limit(category="payments")
def create_payment_handler(request: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Process a payment for the current user.

    The request body 'amount' is in dollars (float). It is converted to
    cents before processing.
    """
    body = request.get("body", {})
    error = validate_required_fields(body, ["amount"])
    if error:
        return serialize_error(400, error)

    try:
        # Convert dollar amount from API to cents for internal use
        amount_cents = dollars_to_cents(body["amount"])
        if amount_cents <= 0:
            return serialize_error(400, "Amount must be positive")

        payment = process_payment(
            amount_cents=amount_cents,
            description=body.get("description", ""),
            currency=body.get("currency", "USD"),
        )
        return {"status": 201, "data": serialize_payment(payment)}
    except (ValueError, RuntimeError) as e:
        return serialize_error(400, str(e))


@_register("GET /payments")
@require_auth
@rate_limit(category="payments")
def list_payments_handler(request: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """List the current user's payments."""
    user = get_current_user()
    payments = get_user_payments(user.user_id)
    return {
        "status": 200,
        "data": serialize_list(payments, serialize_payment),
    }


@_register("POST /subscriptions")
@require_auth
@rate_limit(category="payments")
def create_subscription_handler(
    request: dict[str, Any], **kwargs: Any
) -> dict[str, Any]:
    """Create a subscription for the current user."""
    body = request.get("body", {})
    error = validate_required_fields(body, ["plan"])
    if error:
        return serialize_error(400, error)

    try:
        subscription = create_subscription(plan=body["plan"])
        return {"status": 201, "data": serialize_subscription(subscription)}
    except (ValueError, RuntimeError) as e:
        return serialize_error(400, str(e))


@_register("GET /subscriptions")
@require_auth
@rate_limit(category="default")
def list_subscriptions_handler(
    request: dict[str, Any], **kwargs: Any
) -> dict[str, Any]:
    """List the current user's subscriptions."""
    user = get_current_user()
    subs = get_user_subscriptions(user.user_id)
    return {
        "status": 200,
        "data": serialize_list(subs, serialize_subscription),
    }


@_register("DELETE /subscriptions")
@require_auth
@rate_limit(category="default")
def cancel_subscription_handler(
    request: dict[str, Any], **kwargs: Any
) -> dict[str, Any]:
    """Cancel a subscription by ID."""
    params = request.get("params", {})
    sub_id = params.get("subscription_id")
    if not sub_id:
        return serialize_error(400, "Missing subscription_id parameter")

    result = cancel_subscription(sub_id)
    if result is None:
        return serialize_error(404, "Subscription not found")
    return {"status": 200, "data": serialize_subscription(result)}


@_register("POST /refunds")
@require_auth
@rate_limit(category="payments")
def create_refund_handler(request: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Issue a refund for a payment. Requires support or admin role."""
    if not has_permission("issue_refund"):
        return serialize_error(403, "Insufficient permissions")

    body = request.get("body", {})
    error = validate_required_fields(body, ["payment_id"])
    if error:
        return serialize_error(400, error)

    try:
        amount_cents = None
        if "amount" in body:
            amount_cents = dollars_to_cents(body["amount"])

        refund = process_refund(
            payment_id=body["payment_id"],
            reason=body.get("reason", ""),
            amount_cents=amount_cents,
        )
        if refund is None:
            return serialize_error(404, "Payment not found or not refundable")
        return {"status": 201, "data": serialize_payment(refund)}
    except ValueError as e:
        return serialize_error(400, str(e))


# --- Admin Endpoints ---

@_register("GET /admin/users")
@require_auth
@rate_limit(category="admin")
def admin_list_users_handler(
    request: dict[str, Any], **kwargs: Any
) -> dict[str, Any]:
    """List all users. Requires admin or support role."""
    if not has_permission("view_all_users"):
        return serialize_error(403, "Insufficient permissions")

    users = list_users(include_inactive=True)
    return {
        "status": 200,
        "data": serialize_list(users, serialize_user),
    }


@_register("DELETE /admin/users")
@require_auth
@rate_limit(category="admin")
def admin_delete_user_handler(
    request: dict[str, Any], **kwargs: Any
) -> dict[str, Any]:
    """Delete a user. Requires admin role."""
    if not has_permission("delete_user"):
        return serialize_error(403, "Insufficient permissions")

    params = request.get("params", {})
    target_user_id = params.get("user_id")
    if not target_user_id:
        return serialize_error(400, "Missing user_id parameter")

    if delete_user(target_user_id):
        return {"status": 200, "data": {"deleted": True}}
    return serialize_error(404, "User not found")


# --- Request Dispatcher ---

def handle_request(
    method: str,
    path: str,
    headers: Optional[dict[str, str]] = None,
    body: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Dispatch an incoming request to the appropriate handler.

    Simulates HTTP routing by matching method + path to registered handlers.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE).
        path: URL path (e.g. '/payments').
        headers: Request headers dict.
        body: Request body dict (for POST/PUT).
        params: Query parameters dict.

    Returns:
        Response dict with 'status' and either 'data' or 'error'.
    """
    route_key = f"{method.upper()} {path}"
    handler = _routes.get(route_key)

    if handler is None:
        log_event("route_not_found", level="warning", route=route_key)
        return serialize_error(404, f"No route for {route_key}")

    request = {
        "method": method.upper(),
        "path": path,
        "headers": headers or {},
        "body": body or {},
        "params": params or {},
    }

    log_event("request_received", method=method.upper(), path=path)

    try:
        response = handler(request)
        log_event(
            "request_completed",
            method=method.upper(),
            path=path,
            status=response.get("status"),
        )
        return response
    except Exception as e:
        log_event(
            "request_error",
            level="error",
            method=method.upper(),
            path=path,
            error=str(e),
        )
        return serialize_error(500, f"Internal server error: {str(e)}")
