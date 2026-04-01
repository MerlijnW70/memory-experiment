"""API layer.

Routes, serializers, and decorators for the billing platform's HTTP API.
"""

from src.api.routes import handle_request

__all__ = ["handle_request"]
