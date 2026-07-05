"""
Unit tests — entidad de dominio Apartment y filtros ApartmentSearchFilters.

Sin I/O, sin mocks, sin dependencias externas.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from domain.apartments.entity import Apartment
from domain.apartments.filters import ApartmentSearchFilters
from tests.helpers import make_apartment

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Apartment — creación y validación
# ---------------------------------------------------------------------------


class TestApartmentCreation:
    def test_valid_apartment_is_created(self):
        apt = make_apartment()
        assert apt.apartment_id == "R180"
        assert apt.rooms == 2
        assert apt.bathrooms == 2

    def test_empty_apartment_id_raises_value_error(self):
        with pytest.raises(ValueError, match="apartment_id no puede estar vacío"):
            make_apartment(apartment_id="")

    def test_whitespace_apartment_id_raises_value_error(self):
        with pytest.raises(ValueError, match="apartment_id no puede estar vacío"):
            make_apartment(apartment_id="   ")

    def test_apartment_id_is_stripped(self):
        apt = make_apartment(apartment_id="  R180  ")
        assert apt.apartment_id == "R180"

    def test_negative_rooms_raises_value_error(self):
        with pytest.raises(ValueError):
            make_apartment(rooms=-1)

    def test_negative_bathrooms_raises_value_error(self):
        with pytest.raises(ValueError):
            make_apartment(bathrooms=-1)

    def test_negative_total_occupants_raises_value_error(self):
        with pytest.raises(ValueError):
            make_apartment(total_occupants=-1)

    def test_optional_fields_default_to_none(self):
        apt = Apartment(apartment_id="R999")
        assert apt.community is None
        assert apt.apartment_description is None
        assert apt.owner_name is None
        assert apt.email is None
        assert apt.phone is None

    def test_apartment_is_immutable(self):
        apt = make_apartment()

        with pytest.raises(ValidationError):
            apt.rooms = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Apartment — color personalizado del calendario
# ---------------------------------------------------------------------------


class TestApartmentColor:
    def test_color_defaults_to_none(self):
        assert Apartment(apartment_id="R999").color is None

    def test_valid_hex_color_is_accepted(self):
        assert make_apartment(color="#aabbcc").color == "#aabbcc"

    def test_uppercase_hex_color_is_accepted(self):
        assert make_apartment(color="#AABBCC").color == "#AABBCC"

    def test_blank_color_becomes_none(self):
        assert make_apartment(color="   ").color is None

    @pytest.mark.parametrize("invalid", ["red", "#abc", "#1234", "aabbcc", "#gggggg"])
    def test_invalid_color_raises_value_error(self, invalid):
        with pytest.raises(ValueError, match="hexadecimal"):
            make_apartment(color=invalid)


# ---------------------------------------------------------------------------
# ApartmentSearchFilters — validaciones de rango y fechas
# ---------------------------------------------------------------------------


class TestApartmentSearchFiltersRanges:
    def test_no_filters_is_valid(self):
        filters = ApartmentSearchFilters()
        assert filters.min_rooms is None
        assert filters.available_from is None

    def test_min_occupants_greater_than_max_occupants_raises(self):
        with pytest.raises(ValueError, match="min_occupants no puede ser mayor"):
            ApartmentSearchFilters(min_occupants=10, max_occupants=4)


class TestApartmentSearchFiltersDateRange:
    def test_available_from_without_available_to_raises(self):
        with pytest.raises(ValueError, match="deben informarse juntas"):
            ApartmentSearchFilters(available_from=date(2026, 6, 1))

    def test_available_to_without_available_from_raises(self):
        with pytest.raises(ValueError, match="deben informarse juntas"):
            ApartmentSearchFilters(available_to=date(2026, 6, 10))

    def test_available_from_equal_to_available_to_raises(self):
        with pytest.raises(ValueError, match="available_to debe ser posterior"):
            ApartmentSearchFilters(
                available_from=date(2026, 6, 5),
                available_to=date(2026, 6, 5),
            )

    def test_available_from_after_available_to_raises(self):
        with pytest.raises(ValueError, match="available_to debe ser posterior"):
            ApartmentSearchFilters(
                available_from=date(2026, 6, 10),
                available_to=date(2026, 6, 5),
            )

    def test_valid_date_range_is_accepted(self):
        filters = ApartmentSearchFilters(
            available_from=date(2026, 6, 1),
            available_to=date(2026, 6, 30),
        )
        assert filters.available_from == date(2026, 6, 1)
        assert filters.available_to == date(2026, 6, 30)
