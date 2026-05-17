"""
Utilidades compartidas para todos los tests.
No contiene fixtures de pytest — solo funciones de fábrica puras.
"""

from datetime import date

from domain.bookings.entity import Booking


def make_booking(**overrides) -> Booking:
    """Devuelve una Booking válida con valores por defecto, aplicando los overrides dados."""
    defaults: dict = {
        "booking_id": "TEST-001",
        "guest_name": "Ana García",
        "check_in": date(2026, 6, 1),
        "check_out": date(2026, 6, 5),
        "nights": 4,
    }
    return Booking(**{**defaults, **overrides})
