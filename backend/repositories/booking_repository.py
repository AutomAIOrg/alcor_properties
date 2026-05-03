"""
Repository for booking data access.
Handles all database operations for bookings.
"""

from typing import List, Optional, Tuple
from datetime import date, datetime
from decimal import Decimal
import mysql.connector
from database.connection import get_connection
from models.booking import Booking, BookingCreate, BookingUpdate


class BookingRepository:
    """Repository for managing booking data in MySQL database."""
    
    def __init__(self):
        """Initialize the repository."""
        self.connection = None
    
    def _get_connection(self) -> mysql.connector.MySQLConnection:
        """Get database connection."""
        if self.connection is None or not self.connection.is_connected():
            self.connection = get_connection()
        return self.connection
    
    @staticmethod
    def _safe_convert_value(value):
        """Convert problematic values for serialization."""
        if isinstance(value, Decimal):
            return float(value)
        elif hasattr(value, 'date'):  # datetime objects
            return value.date().isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        elif value is None:
            return None
        else:
            return value
    
    def get_all(self, limit: Optional[int] = None) -> List[Booking]:
        """
        Get all bookings from database.
        
        Args:
            limit: Optional limit for number of results
            
        Returns:
            List of Booking objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            query = "SELECT * FROM bookings"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            bookings = []
            for row in rows:
                booking_dict = self._row_to_dict(columns, row)
                if booking_dict:
                    bookings.append(Booking(**booking_dict))
            
            return bookings
            
        finally:
            cursor.close()
    
    def get_by_id(self, record_id: int) -> Optional[Booking]:
        """
        Get a booking by its record ID.
        
        Args:
            record_id: Database record ID
            
        Returns:
            Booking object or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            query = "SELECT * FROM bookings WHERE ID = %s"
            cursor.execute(query, (record_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            columns = [desc[0] for desc in cursor.description]
            booking_dict = self._row_to_dict(columns, row)
            
            return Booking(**booking_dict) if booking_dict else None
            
        finally:
            cursor.close()
    
    def get_by_date_range(self, start_date: date, end_date: date) -> List[Booking]:
        """
        Get bookings within a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of Booking objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT * FROM bookings 
                WHERE (`Check-In` <= %s AND `Check-Out` >= %s)
                ORDER BY `Check-In`
            """
            cursor.execute(query, (end_date, start_date))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            bookings = []
            for row in rows:
                booking_dict = self._row_to_dict(columns, row)
                if booking_dict:
                    bookings.append(Booking(**booking_dict))
            
            return bookings
            
        finally:
            cursor.close()
    
    def create(self, booking: BookingCreate) -> Booking:
        """
        Create a new booking.
        
        Args:
            booking: BookingCreate object with booking data
            
        Returns:
            Created Booking object with record_id
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
                INSERT INTO bookings 
                (`Booking ID`, `Nombre,Apellidos`, `Check-In`, `Check-Out`, 
                 `Nº Noches`, `Nº Personas`, `Nº Adultos`, `Nº Niños`, 
                 `Status`, `Email`, `Movil`, `Precio`, `Comm y Cargos`, `Nº Booking`, `Notes`)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                booking.booking_id,
                booking.guest_name,
                booking.check_in,
                booking.check_out,
                booking.nights,
                booking.persons,
                booking.adults,
                booking.children,
                booking.status,
                booking.email,
                booking.phone,
                booking.price,
                booking.charges,
                booking.booking_number,
                booking.notes
            )
            
            cursor.execute(query, values)
            conn.commit()
            
            # Get the created booking
            record_id = cursor.lastrowid
            return self.get_by_id(record_id)
            
        finally:
            cursor.close()
    
    def update(self, record_id: int, booking: BookingUpdate) -> Optional[Booking]:
        """
        Update an existing booking.
        
        Args:
            record_id: Database record ID
            booking: BookingUpdate object with fields to update
            
        Returns:
            Updated Booking object or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Build dynamic update query
            update_fields = []
            values = []
            
            field_mapping = {
                'booking_id': '`Booking ID`',
                'guest_name': '`Nombre,Apellidos`',
                'check_in': '`Check-In`',
                'check_out': '`Check-Out`',
                'nights': '`Nº Noches`',
                'persons': '`Nº Personas`',
                'adults': '`Nº Adultos`',
                'children': '`Nº Niños`',
                'status': '`Status`',
                'email': '`Email`',
                'phone': '`Movil`',
                'price': '`Precio`',
                'charges': '`Comm y Cargos`',
                'booking_number': '`Nº Booking`',
                'notes': '`Notes`'
            }
            
            for field, db_column in field_mapping.items():
                value = getattr(booking, field)
                if value is not None:
                    update_fields.append(f"{db_column} = %s")
                    values.append(value)
            
            if not update_fields:
                return self.get_by_id(record_id)
            
            values.append(record_id)
            query = f"UPDATE bookings SET {', '.join(update_fields)} WHERE ID = %s"
            
            cursor.execute(query, values)
            conn.commit()
            
            return self.get_by_id(record_id)
            
        finally:
            cursor.close()
    
    def delete(self, record_id: int) -> bool:
        """
        Delete a booking.
        
        Args:
            record_id: Database record ID
            
        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            query = "DELETE FROM bookings WHERE ID = %s"
            cursor.execute(query, (record_id,))
            conn.commit()
            
            return cursor.rowcount > 0
            
        finally:
            cursor.close()
    
    def _row_to_dict(self, columns: List[str], row: Tuple) -> Optional[dict]:
        """
        Convert database row to dictionary for Booking model.
        
        Args:
            columns: List of column names
            row: Database row tuple
            
        Returns:
            Dictionary matching Booking model fields or None if conversion fails
        """
        try:
            col_map = {col: idx for idx, col in enumerate(columns)}
            
            # Extract and convert values
            check_in_raw = row[col_map.get('Check-In')]
            check_out_raw = row[col_map.get('Check-Out')]
            
            # Convert dates
            if isinstance(check_in_raw, str):
                check_in = date.fromisoformat(check_in_raw)
            elif isinstance(check_in_raw, datetime):
                check_in = check_in_raw.date()
            else:
                check_in = check_in_raw
            
            if isinstance(check_out_raw, str):
                check_out = date.fromisoformat(check_out_raw)
            elif isinstance(check_out_raw, datetime):
                check_out = check_out_raw.date()
            else:
                check_out = check_out_raw
            
            return {
                "record_id": self._safe_convert_value(row[col_map.get('ID')]),
                "booking_id": self._safe_convert_value(row[col_map.get('Booking ID')]),
                "guest_name": self._safe_convert_value(row[col_map.get('Nombre,Apellidos')]) or "Unknown",
                "check_in": check_in,
                "check_out": check_out,
                "nights": self._safe_convert_value(row[col_map.get('Nº Noches')]),
                "persons": self._safe_convert_value(row[col_map.get('Nº Personas')]) or 1,
                "adults": self._safe_convert_value(row[col_map.get('Nº Adultos')]) or 1,
                "children": self._safe_convert_value(row[col_map.get('Nº Niños')]) or 0,
                "booking_number": self._safe_convert_value(row[col_map.get('Nº Booking')]),
                "status": self._safe_convert_value(row[col_map.get('Status')]) or "Confirmed",
                "email": self._safe_convert_value(row[col_map.get('Email')]),
                "phone": self._safe_convert_value(row[col_map.get('Movil')]),
                "price": self._safe_convert_value(row[col_map.get('Precio')]),
                "charges": self._safe_convert_value(row[col_map.get('Comm y Cargos')]),
                "notes": self._safe_convert_value(row[col_map['Notes']]) if 'Notes' in col_map else None,
            }
            
        except Exception as e:
            print(f"⚠️ Error converting row to dict: {e}")
            return None
