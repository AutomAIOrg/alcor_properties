"""
API router for booking endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import date
from models.booking import Booking, BookingCreate, BookingUpdate
from services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])

# Service instance
booking_service = BookingService()


@router.get("/", response_model=List[Booking])
async def get_bookings(
    limit: Optional[int] = Query(None, description="Limit number of results"),
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter until this date"),
    days: Optional[int] = Query(None, description="Get bookings for next N days from start_date")
):
    """
    Get all bookings or filter by date range.
    
    - **limit**: Maximum number of bookings to return
    - **start_date**: Start date for filtering (defaults to today if days is provided)
    - **end_date**: End date for filtering
    - **days**: Number of days from start_date (alternative to end_date)
    """
    try:
        # Custom date range
        if start_date and end_date:
            return booking_service.get_bookings_for_date_range(start_date, end_date)
        
        # Period from start_date for N days
        if days:
            return booking_service.get_bookings_for_period(start_date, days)
        
        # Default: all bookings
        return booking_service.get_all_bookings(limit=limit)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bookings: {str(e)}")


@router.get("/active", response_model=List[Booking])
async def get_active_bookings():
    """Get currently active bookings (guests currently staying)."""
    try:
        return booking_service.get_active_bookings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching active bookings: {str(e)}")


@router.get("/upcoming-checkins", response_model=List[Booking])
async def get_upcoming_checkins(
    days: int = Query(7, description="Number of days to look ahead")
):
    """Get bookings with upcoming check-ins."""
    try:
        return booking_service.get_upcoming_checkins(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching upcoming check-ins: {str(e)}")


@router.get("/upcoming-checkouts", response_model=List[Booking])
async def get_upcoming_checkouts(
    days: int = Query(7, description="Number of days to look ahead")
):
    """Get bookings with upcoming check-outs."""
    try:
        return booking_service.get_upcoming_checkouts(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching upcoming check-outs: {str(e)}")


@router.get("/calendar-events")
async def get_calendar_events(
    start_date: Optional[date] = Query(None, description="Start date (defaults to today)"),
    days: int = Query(90, description="Number of days to include")
):
    """Get bookings formatted as calendar events."""
    try:
        return booking_service.get_calendar_events(start_date, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching calendar events: {str(e)}")


@router.get("/{record_id}", response_model=Booking)
async def get_booking(record_id: int):
    """Get a specific booking by ID."""
    try:
        booking = booking_service.get_booking_by_id(record_id)
        if not booking:
            raise HTTPException(status_code=404, detail=f"Booking with ID {record_id} not found")
        return booking
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching booking: {str(e)}")


@router.post("/", response_model=Booking, status_code=201)
async def create_booking(booking: BookingCreate):
    """Create a new booking."""
    try:
        return booking_service.create_booking(booking)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating booking: {str(e)}")


@router.put("/{record_id}", response_model=Booking)
async def update_booking(record_id: int, booking: BookingUpdate):
    """Update an existing booking."""
    try:
        updated_booking = booking_service.update_booking(record_id, booking)
        if not updated_booking:
            raise HTTPException(status_code=404, detail=f"Booking with ID {record_id} not found")
        return updated_booking
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating booking: {str(e)}")


@router.delete("/{record_id}", status_code=204)
async def delete_booking(record_id: int):
    """Delete a booking."""
    try:
        deleted = booking_service.delete_booking(record_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Booking with ID {record_id} not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting booking: {str(e)}")
