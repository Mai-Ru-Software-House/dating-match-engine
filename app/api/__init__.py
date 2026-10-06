"""
API: exports route definitions for internal endpoints.
"""

from app.api.internal import (
    internal_router,
    internal_versioned_router,
    router,
    versioned_router,
)

__all__ = [
    "internal_router",
    "internal_versioned_router",
    "router",
    "versioned_router",
]
