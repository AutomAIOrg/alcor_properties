"""
API routers for FastAPI endpoints.
"""

from .bookings import router as bookings_router

__all__ = ["bookings_router"]
