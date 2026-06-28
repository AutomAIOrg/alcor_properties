"""
Integration tests — SQLAlchemyApartmentRepository contra SQLite en memoria.

Verifica filtros de texto, numéricos, disponibilidad y mapeo de entidades
sin conectar contra MySQL.
"""

from datetime import date

import pytest

from domain.apartments.entity import Apartment
from domain.apartments.filters import ApartmentSearchFilters
from infrastructure.models.apartment import ApartmentORM
from infrastructure.models.booking import BookingORM
from infrastructure.repositories.sqlalchemy_apartment_repository import (
    SQLAlchemyApartmentRepository,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers de inserción directa (bypass de la capa de dominio)
# ---------------------------------------------------------------------------


def _insert_apartment(session, **overrides) -> ApartmentORM:
    """Inserta un ApartmentORM con valores por defecto aplicando los overrides dados."""
    defaults = {
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
    orm = ApartmentORM(**{**defaults, **overrides})
    session.add(orm)
    session.commit()
    session.refresh(orm)
    return orm


def _insert_booking(session, **overrides) -> BookingORM:
    """Inserta un BookingORM con valores por defecto aplicando los overrides dados."""
    defaults = {
        "apartment_id": "R180",
        "guest_name": "Ana García",
        "check_in": date(2026, 6, 1),
        "check_out": date(2026, 6, 5),
        "nights": 4,
        "status": "Confirmed",
    }
    orm = BookingORM(**{**defaults, **overrides})
    session.add(orm)
    session.commit()
    session.refresh(orm)
    return orm


# ---------------------------------------------------------------------------
# get_by_apartment_id
# ---------------------------------------------------------------------------


class TestGetByApartmentId:
    def test_returns_entity_when_found(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180", community="Alta Entinas")

        result = SQLAlchemyApartmentRepository(sqlite_session).get_by_apartment_id("R180")

        assert isinstance(result, Apartment)
        assert result.apartment_id == "R180"
        assert result.community == "Alta Entinas"

    def test_returns_none_when_not_found(self, sqlite_session):
        result = SQLAlchemyApartmentRepository(sqlite_session).get_by_apartment_id("UNKNOWN")

        assert result is None

    def test_all_fields_are_mapped_to_domain_entity(self, sqlite_session):
        _insert_apartment(sqlite_session)

        result = SQLAlchemyApartmentRepository(sqlite_session).get_by_apartment_id("R180")

        assert result.rooms == 2
        assert result.bathrooms == 2
        assert result.parking == "63"
        assert result.total_occupants == 6
        assert result.owner_name == "Katarzyna Tokarska"
        assert result.email == "owner@example.com"
        assert result.phone == "+34 600 000 000"


# ---------------------------------------------------------------------------
# search_apartments — filtros de texto
# ---------------------------------------------------------------------------


class TestSearchTextFilters:
    def test_no_filters_returns_all_apartments(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180")
        _insert_apartment(sqlite_session, apartment_id="R221")

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters()
        )

        assert len(results) == 2

    def test_q_matches_community_case_insensitive(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180", community="Alta Entinas")
        _insert_apartment(sqlite_session, apartment_id="R221", community="Zenata")

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(q="entinas")
        )

        assert len(results) == 1
        assert results[0].apartment_id == "R180"

    def test_q_matches_apartment_id(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180")
        _insert_apartment(sqlite_session, apartment_id="R221")

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(q="R221")
        )

        assert len(results) == 1
        assert results[0].apartment_id == "R221"

    def test_q_matches_owner_name(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180", owner_name="Katarzyna Tokarska")
        _insert_apartment(sqlite_session, apartment_id="R221", owner_name="Juan Pérez")

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(q="tokarska")
        )

        assert len(results) == 1
        assert results[0].apartment_id == "R180"

    def test_q_returns_empty_when_no_match(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180")

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(q="NOMATCH-XYZ")
        )

        assert results == []

    def test_community_field_filter_is_case_insensitive(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180", community="Alta Entinas")
        _insert_apartment(sqlite_session, apartment_id="R221", community="Zenata")

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(community="ALTA")
        )

        assert len(results) == 1
        assert results[0].apartment_id == "R180"

    def test_address_field_filter_partial_match(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180", address="Calle Glaucio 15")
        _insert_apartment(sqlite_session, apartment_id="R221", address="Avenida del Mar 3")

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(address="glaucio")
        )

        assert len(results) == 1
        assert results[0].apartment_id == "R180"


# ---------------------------------------------------------------------------
# search_apartments — filtros numéricos
# ---------------------------------------------------------------------------


class TestSearchNumericFilters:
    def test_min_rooms_excludes_apartments_below_threshold(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="SMALL", rooms=1)
        _insert_apartment(sqlite_session, apartment_id="LARGE", rooms=4)

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(min_rooms=3)
        )

        assert len(results) == 1
        assert results[0].apartment_id == "LARGE"

    def test_min_max_occupants_combined(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="SMALL", total_occupants=2)
        _insert_apartment(sqlite_session, apartment_id="MEDIUM", total_occupants=6)
        _insert_apartment(sqlite_session, apartment_id="LARGE", total_occupants=10)

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(min_occupants=4, max_occupants=8)
        )

        assert len(results) == 1
        assert results[0].apartment_id == "MEDIUM"


# ---------------------------------------------------------------------------
# search_apartments — filtro de disponibilidad
# ---------------------------------------------------------------------------


class TestSearchAvailabilityFilter:
    def test_apartment_with_no_bookings_is_available(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180")

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(
                available_from=date(2026, 6, 1),
                available_to=date(2026, 6, 10),
            )
        )

        assert len(results) == 1
        assert results[0].apartment_id == "R180"

    def test_overlapping_confirmed_booking_blocks_availability(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180")
        _insert_booking(
            sqlite_session,
            apartment_id="R180",
            check_in=date(2026, 6, 3),
            check_out=date(2026, 6, 8),
            status="Confirmed",
        )

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(
                available_from=date(2026, 6, 1),
                available_to=date(2026, 6, 10),
            )
        )

        assert results == []

    def test_cancelled_booking_does_not_block_availability(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180")
        _insert_booking(
            sqlite_session,
            apartment_id="R180",
            check_in=date(2026, 6, 3),
            check_out=date(2026, 6, 8),
            status="Cancelled",
        )

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(
                available_from=date(2026, 6, 1),
                available_to=date(2026, 6, 10),
            )
        )

        assert len(results) == 1
        assert results[0].apartment_id == "R180"

    def test_non_overlapping_booking_does_not_block_availability(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R180")
        _insert_booking(
            sqlite_session,
            apartment_id="R180",
            check_in=date(2026, 7, 1),
            check_out=date(2026, 7, 5),
            status="Confirmed",
        )

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(
                available_from=date(2026, 6, 1),
                available_to=date(2026, 6, 10),
            )
        )

        assert len(results) == 1

    def test_available_apartment_returned_while_booked_one_excluded(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="BUSY")
        _insert_apartment(sqlite_session, apartment_id="FREE")
        _insert_booking(
            sqlite_session,
            apartment_id="BUSY",
            check_in=date(2026, 6, 3),
            check_out=date(2026, 6, 8),
            status="Confirmed",
        )

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters(
                available_from=date(2026, 6, 1),
                available_to=date(2026, 6, 10),
            )
        )

        assert len(results) == 1
        assert results[0].apartment_id == "FREE"


# ---------------------------------------------------------------------------
# search_apartments — ordenación
# ---------------------------------------------------------------------------


class TestSearchOrdering:
    def test_results_are_ordered_by_apartment_id_ascending(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R500")
        _insert_apartment(sqlite_session, apartment_id="R100")
        _insert_apartment(sqlite_session, apartment_id="R300")

        results = SQLAlchemyApartmentRepository(sqlite_session).search_apartments(
            ApartmentSearchFilters()
        )

        assert [r.apartment_id for r in results] == ["R100", "R300", "R500"]


# ---------------------------------------------------------------------------
# CRUD — create, get_all, update, delete
# ---------------------------------------------------------------------------


class TestCreateApartment:
    def test_persists_all_fields(self, sqlite_session):
        from tests.helpers import make_apartment

        repo = SQLAlchemyApartmentRepository(sqlite_session)
        apartment = make_apartment(
            apartment_id="R999",
            community="Nueva Comunidad",
            apartment_description="Descripción test",
            address="Calle Test 99",
            rooms=3,
            bathrooms=2,
            parking="P-99",
            total_occupants=5,
            owner_name="Owner Test",
            email="owner@test.com",
            phone="+34 611 222 333",
        )

        repo.create_apartment(apartment)
        stored = repo.get_by_apartment_id("R999")

        assert stored is not None
        assert stored.community == "Nueva Comunidad"
        assert stored.apartment_description == "Descripción test"
        assert stored.address == "Calle Test 99"
        assert stored.rooms == 3
        assert stored.bathrooms == 2
        assert stored.parking == "P-99"
        assert stored.total_occupants == 5
        assert stored.owner_name == "Owner Test"
        assert stored.email == "owner@test.com"
        assert stored.phone == "+34 611 222 333"


class TestGetAll:
    def test_returns_apartments_ordered_by_apartment_id(self, sqlite_session):
        _insert_apartment(sqlite_session, apartment_id="R300")
        _insert_apartment(sqlite_session, apartment_id="R100")
        _insert_apartment(sqlite_session, apartment_id="R200")

        results = SQLAlchemyApartmentRepository(sqlite_session).get_all()

        assert [r.apartment_id for r in results] == ["R100", "R200", "R300"]


class TestUpdateApartment:
    def test_persists_changes_and_keeps_primary_key(self, sqlite_session):
        from tests.helpers import make_apartment

        repo = SQLAlchemyApartmentRepository(sqlite_session)
        _insert_apartment(sqlite_session, apartment_id="R180", community="Original")

        updated = make_apartment(
            apartment_id="R180",
            community="Actualizada",
            apartment_description="Nueva descripción",
            address="Nueva dirección",
            rooms=4,
            bathrooms=3,
            parking="P-NEW",
            total_occupants=8,
            owner_name="Nuevo Owner",
            email="nuevo@test.com",
            phone="+34 699 888 777",
        )
        repo.update_apartment(updated)

        stored = repo.get_by_apartment_id("R180")
        assert stored is not None
        assert stored.apartment_id == "R180"
        assert stored.community == "Actualizada"
        assert stored.apartment_description == "Nueva descripción"
        assert stored.rooms == 4
        assert stored.parking == "P-NEW"

    def test_raises_not_found_for_missing_apartment(self, sqlite_session):
        from domain.exceptions import ApartmentNotFoundError
        from tests.helpers import make_apartment

        with pytest.raises(ApartmentNotFoundError):
            SQLAlchemyApartmentRepository(sqlite_session).update_apartment(
                make_apartment(apartment_id="MISSING")
            )


class TestDeleteApartment:
    def test_removes_apartment_from_database(self, sqlite_session):

        repo = SQLAlchemyApartmentRepository(sqlite_session)
        _insert_apartment(sqlite_session, apartment_id="R180")
        apartment = repo.get_by_apartment_id("R180")
        assert apartment is not None

        repo.delete_apartment(apartment)

        assert repo.get_by_apartment_id("R180") is None

    def test_raises_not_found_for_missing_apartment(self, sqlite_session):
        from domain.exceptions import ApartmentNotFoundError
        from tests.helpers import make_apartment

        with pytest.raises(ApartmentNotFoundError):
            SQLAlchemyApartmentRepository(sqlite_session).delete_apartment(
                make_apartment(apartment_id="MISSING")
            )
