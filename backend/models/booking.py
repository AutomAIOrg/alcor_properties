"""
Pydantic models for Booking entity.
Provides validation, serialization, and type safety.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import date
from typing import Optional
from decimal import Decimal


class BookingBase(BaseModel):
    """Base booking model with common fields."""
    
    booking_id: str = Field(..., description="Unique booking identifier")
    guest_name: str = Field(..., description="Guest full name", min_length=1)
    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")
    status: str = Field(default="Confirmed", description="Booking status")
    
    # Occupancy
    nights: int = Field(..., ge=1, description="Number of nights")
    persons: int = Field(default=1, ge=1, description="Total number of persons")
    adults: int = Field(default=1, ge=1, description="Number of adults")
    children: int = Field(default=0, ge=0, description="Number of children")
    
    # Financial
    price: Optional[float] = Field(None, ge=0, description="Total price")
    charges: Optional[float] = Field(None, ge=0, description="Commission and charges")
    
    # Contact
    email: Optional[str] = Field(None, description="Guest email")
    phone: Optional[str] = Field(None, description="Guest phone number")
    
    # Additional
    booking_number: Optional[str] = Field(None, description="Platform booking number")
    notes: Optional[str] = Field(None, description="Booking notes or comments")
    
    @field_validator('check_out')
    @classmethod
    def check_out_after_check_in(cls, v, info):
        """Validate that check-out is after check-in."""
        if 'check_in' in info.data and v <= info.data['check_in']:
            raise ValueError('Check-out must be after check-in')
        return v
    
    @field_validator('nights')
    @classmethod
    def validate_nights(cls, v, info):
        """Validate nights match date difference."""
        if 'check_in' in info.data and 'check_out' in info.data:
            expected_nights = (info.data['check_out'] - info.data['check_in']).days
            if v != expected_nights:
                # Auto-correct nights based on dates
                return expected_nights
        return v


class Booking(BookingBase):
    """Complete booking model with database ID."""
    
    record_id: int = Field(..., description="Database record ID")
    electric_allowance: Optional[float] = Field(None, description="Electric allowance if applicable")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "record_id": 1,
                "booking_id": "BK-2026-001",
                "guest_name": "John Doe",
                "check_in": "2026-01-20",
                "check_out": "2026-01-25",
                "nights": 5,
                "persons": 2,
                "adults": 2,
                "children": 0,
                "status": "Confirmed",
                "email": "john@example.com",
                "phone": "+34600000000",
                "price": 500.0,
                "charges": 50.0,
                "booking_number": "AIRBNB123",
                "electric_allowance": 20.0
            }
        }


class BookingCreate(BookingBase):
    """Model for creating a new booking."""
    pass


class BookingUpdate(BaseModel):
    """Model for updating an existing booking. All fields are optional."""
    
    booking_id: Optional[str] = None
    guest_name: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    status: Optional[str] = None
    nights: Optional[int] = None
    persons: Optional[int] = None
    adults: Optional[int] = None
    children: Optional[int] = None
    price: Optional[float] = None
    charges: Optional[float] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    booking_number: Optional[str] = None
    notes: Optional[str] = None


class BookingFilter(BaseModel):
    """Model for filtering bookings."""
    
    start_date: Optional[date] = Field(None, description="Filter bookings from this date")
    end_date: Optional[date] = Field(None, description="Filter bookings until this date")
    status: Optional[str] = Field(None, description="Filter by status")
    booking_id: Optional[str] = Field(None, description="Filter by booking ID")
