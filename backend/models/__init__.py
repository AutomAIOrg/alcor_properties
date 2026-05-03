"""
Data models for the application.
Contains Pydantic models for validation and serialization.
"""

from .booking import Booking, BookingCreate, BookingUpdate

__all__ = ["Booking", "BookingCreate", "BookingUpdate"]
