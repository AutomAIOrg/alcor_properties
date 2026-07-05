"""
Utilidades compartidas para todos los tests.
No contiene fixtures de pytest — solo funciones de fábrica puras.
"""

from datetime import date
from decimal import Decimal

from domain.apartments.entity import Apartment
from domain.auth.user_entity import Role, User
from domain.bills.entity import Bill
from domain.bookings.entity import Booking


def make_booking(**overrides) -> Booking:
    """Devuelve una Booking válida con valores por defecto, aplicando los overrides dados."""
    defaults: dict = {
        "apartment_id": "TEST-001",
        "guest_name": "Ana García",
        "check_in": date(2026, 6, 1),
        "check_out": date(2026, 6, 5),
        "nights": 4,
    }
    return Booking(**{**defaults, **overrides})


def make_user(**overrides) -> User:
    """Devuelve un User válido con valores por defecto, aplicando los overrides dados."""
    defaults: dict = {
        "id": 1,
        "username": "admin",
        "password": "$2b$12$dummyhashforunitandintegrationtests",
        "name": "Admin",
        "lastname": "User",
        "email": "admin@example.com",
        "role": Role.ADMIN,
    }
    return User(**{**defaults, **overrides})


def make_bill(**overrides) -> Bill:
    """Devuelve una Bill válida con valores por defecto, aplicando los overrides dados."""
    defaults: dict = {
        "apartment_id": "TEST-001",
        "record_id": 1,
        "cleaning_date": date(2026, 6, 1),
        "clean_hours": Decimal("2.00"),
        "cost": Decimal("30.00"),
        "state": "Creada",
    }
    return Bill(**{**defaults, **overrides})


def make_apartment(**overrides) -> Apartment:
    """Devuelve un Apartment válido con valores por defecto, aplicando los overrides dados."""
    defaults: dict = {
        "apartment_id": "R180",
        "community": "Alta Entinas",
        "apartment_description": "Apartamento familiar",
        "address": "Calle Glaucio 15",
        "rooms": 2,
        "bathrooms": 2,
        "parking": "63",
        "total_occupants": 6,
        "owner_name": "Katarzyna Tokarska",
        "email": "owner@example.com",
        "phone": "+34 600 000 000",
    }
    return Apartment(**{**defaults, **overrides})
