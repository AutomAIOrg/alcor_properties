"""
Business logic service for bookings.
Handles use cases and business rules.
"""

from typing import List, Optional
from datetime import date, timedelta
from repositories.booking_repository import BookingRepository
from models.booking import Booking, BookingCreate, BookingUpdate
import os
from dotenv import load_dotenv

load_dotenv()


class BookingService:
    """Service for managing booking business logic."""
    
    def __init__(self, repository: Optional[BookingRepository] = None):
        """
        Initialize the service.
        
        Args:
            repository: BookingRepository instance (optional, creates one if not provided)
        """
        self.repository = repository or BookingRepository()
        
        # Get electric booking IDs from environment
        electric_str = os.getenv('ELECTRIC', '')
        self.electric_bookings = set(b.strip() for b in electric_str.split(',') if b.strip())
    
    def get_all_bookings(self, limit: Optional[int] = None) -> List[Booking]:
        """
        Get all bookings.
        
        Args:
            limit: Optional limit for results
            
        Returns:
            List of bookings
        """
        bookings = self.repository.get_all(limit=limit)
        return self._add_electric_allowance(bookings)
    
    def get_booking_by_id(self, record_id: int) -> Optional[Booking]:
        """
        Get a booking by ID.
        
        Args:
            record_id: Database record ID
            
        Returns:
            Booking or None
        """
        booking = self.repository.get_by_id(record_id)
        if booking:
            booking = self._calculate_electric_allowance(booking)
        return booking
    
    def get_bookings_for_period(
        self, 
        start_date: Optional[date] = None, 
        days: int = 14
    ) -> List[Booking]:
        """
        Get bookings for a specific period.
        
        Args:
            start_date: Start date (defaults to today)
            days: Number of days from start_date (default 14)
            
        Returns:
            List of bookings in the period
        """
        if start_date is None:
            start_date = date.today()
        
        end_date = start_date + timedelta(days=days)
        
        bookings = self.repository.get_by_date_range(start_date, end_date)
        return self._add_electric_allowance(bookings)
    
    def get_bookings_for_date_range(
        self, 
        start_date: date, 
        end_date: date
    ) -> List[Booking]:
        """
        Get bookings for a custom date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of bookings in the range
        """
        bookings = self.repository.get_by_date_range(start_date, end_date)
        return self._add_electric_allowance(bookings)
    
    def get_active_bookings(self) -> List[Booking]:
        """
        Get currently active bookings (guests currently staying).
        
        Returns:
            List of active bookings
        """
        today = date.today()
        all_bookings = self.repository.get_by_date_range(today, today)
        
        # Filter for active bookings (check-in <= today <= check-out)
        active = [
            b for b in all_bookings 
            if b.check_in <= today <= b.check_out
        ]
        
        return self._add_electric_allowance(active)
    
    def get_upcoming_checkins(self, days: int = 7) -> List[Booking]:
        """
        Get bookings with upcoming check-ins.
        
        Args:
            days: Number of days to look ahead (default 7)
            
        Returns:
            List of bookings with upcoming check-ins
        """
        today = date.today()
        end_date = today + timedelta(days=days)
        
        all_bookings = self.repository.get_by_date_range(today, end_date)
        
        # Filter for upcoming check-ins
        upcoming = [
            b for b in all_bookings 
            if today <= b.check_in <= end_date
        ]
        
        # Sort by check-in date
        upcoming.sort(key=lambda b: b.check_in)
        
        return self._add_electric_allowance(upcoming)
    
    def get_upcoming_checkouts(self, days: int = 7) -> List[Booking]:
        """
        Get bookings with upcoming check-outs.
        
        Args:
            days: Number of days to look ahead (default 7)
            
        Returns:
            List of bookings with upcoming check-outs
        """
        today = date.today()
        end_date = today + timedelta(days=days)
        
        all_bookings = self.repository.get_by_date_range(today, end_date)
        
        # Filter for upcoming check-outs
        upcoming = [
            b for b in all_bookings 
            if today <= b.check_out <= end_date
        ]
        
        # Sort by check-out date
        upcoming.sort(key=lambda b: b.check_out)
        
        return self._add_electric_allowance(upcoming)
    
    def create_booking(self, booking_data: BookingCreate) -> Booking:
        """
        Create a new booking.
        
        Args:
            booking_data: Booking data to create
            
        Returns:
            Created booking
            
        Raises:
            ValueError: If validation fails
        """
        # Additional business validations
        if booking_data.check_out <= booking_data.check_in:
            raise ValueError("Check-out must be after check-in")
        
        # Auto-calculate nights if not provided
        if not booking_data.nights:
            booking_data.nights = (booking_data.check_out - booking_data.check_in).days
        
        # Check for overlapping bookings (optional business rule)
        # overlapping = self._check_overlapping_bookings(
        #     booking_data.check_in, 
        #     booking_data.check_out
        # )
        # if overlapping:
        #     raise ValueError("Booking overlaps with existing booking")
        
        booking = self.repository.create(booking_data)
        return self._calculate_electric_allowance(booking)
    
    def update_booking(self, record_id: int, booking_data: BookingUpdate) -> Optional[Booking]:
        """
        Update an existing booking.
        
        Args:
            record_id: Database record ID
            booking_data: Fields to update
            
        Returns:
            Updated booking or None if not found
        """
        # Auto-calculate nights if dates are being updated
        if booking_data.check_in and booking_data.check_out:
            booking_data.nights = (booking_data.check_out - booking_data.check_in).days
        
        booking = self.repository.update(record_id, booking_data)
        if booking:
            booking = self._calculate_electric_allowance(booking)
        return booking
    
    def delete_booking(self, record_id: int) -> bool:
        """
        Delete a booking.
        
        Args:
            record_id: Database record ID
            
        Returns:
            True if deleted, False if not found
        """
        return self.repository.delete(record_id)
    
    def get_calendar_events(
        self, 
        start_date: Optional[date] = None, 
        days: int = 90
    ) -> List[dict]:
        """
        Get bookings formatted as calendar events.
        
        Args:
            start_date: Start date (defaults to today)
            days: Number of days to include (default 90)
            
        Returns:
            List of calendar event dictionaries
        """
        bookings = self.get_bookings_for_period(start_date, days)
        
        events = []
        for booking in bookings:
            # Skip cancelled bookings close to check-in
            if booking.status and booking.status.lower() == 'cancelled':
                if (booking.check_in - date.today()).days < 3:
                    continue
            
            event = {
                "id": f"booking-{booking.record_id}",
                "title": f"{booking.booking_id} - {booking.guest_name}",
                "start": booking.check_in.isoformat(),
                "end": booking.check_out.isoformat(),
                "allDay": True,
                "classNames": ["reserva"] + (["cancelled"] if booking.status and booking.status.lower() == 'cancelled' else []),
                "extendedProps": {
                    "record_id": booking.record_id,
                    "booking_id": booking.booking_id,
                    "booking_number": booking.booking_number,
                    "guest_name": booking.guest_name,
                    "check_in": booking.check_in.isoformat(),
                    "check_out": booking.check_out.isoformat(),
                    "status": booking.status,
                    "nights": booking.nights,
                    "persons": booking.persons,
                    "adults": booking.adults,
                    "children": booking.children,
                    "email": booking.email,
                    "phone": booking.phone,
                    "price": booking.price,
                    "charges": booking.charges,
                    "electric_allowance": booking.electric_allowance,
                    "source": "database"
                }
            }
            events.append(event)
        
        return events
    
    def _calculate_electric_allowance(self, booking: Booking) -> Booking:
        """Calculate electric allowance for a single booking."""
        if str(booking.booking_id).strip() in self.electric_bookings:
            booking.electric_allowance = booking.nights * 4
        else:
            booking.electric_allowance = None
        return booking
    
    def _add_electric_allowance(self, bookings: List[Booking]) -> List[Booking]:
        """Add electric allowance to a list of bookings."""
        return [self._calculate_electric_allowance(b) for b in bookings]
    
    def _check_overlapping_bookings(
        self, 
        check_in: date, 
        check_out: date, 
        exclude_id: Optional[int] = None
    ) -> List[Booking]:
        """Check for overlapping bookings (helper for validation)."""
        all_bookings = self.repository.get_by_date_range(check_in, check_out)
        
        overlapping = [
            b for b in all_bookings 
            if (exclude_id is None or b.record_id != exclude_id) and
               not (b.check_out <= check_in or b.check_in >= check_out)
        ]
        
        return overlapping
