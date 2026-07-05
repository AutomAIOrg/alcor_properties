"""
Integration tests — SQLAlchemyCleaningTypeRepository contra SQLite en memoria.
"""

from decimal import Decimal

import pytest

from domain.exceptions import CleaningTypeAlreadyExistsError, CleaningTypeNotFoundError
from infrastructure.repositories.sqlalchemy_cleaning_type_repository import (
    SQLAlchemyCleaningTypeRepository,
)
from tests.helpers import make_cleaning_type

pytestmark = pytest.mark.integration


class TestCreate:
    def test_persists_and_assigns_id(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)

        result = repo.create(make_cleaning_type(cleaning_type_id=None))

        assert result.cleaning_type_id is not None
        assert result.name == "Limpieza normal"
        assert result.hourly_rate == Decimal("15.00")
        assert result.active is True

    def test_duplicate_name_raises_already_exists(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)
        repo.create(make_cleaning_type(cleaning_type_id=None, name="Limpieza normal"))

        with pytest.raises(CleaningTypeAlreadyExistsError):
            repo.create(make_cleaning_type(cleaning_type_id=None, name="Limpieza normal"))


class TestGetByIdAndName:
    def test_get_by_id_returns_entity(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)
        created = repo.create(make_cleaning_type(cleaning_type_id=None))

        assert repo.get_by_id(created.cleaning_type_id).name == "Limpieza normal"

    def test_get_by_id_returns_none_when_missing(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)

        assert repo.get_by_id(999) is None

    def test_get_by_name_is_trimmed(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)
        repo.create(make_cleaning_type(cleaning_type_id=None, name="Fin de semana"))

        assert repo.get_by_name("  Fin de semana  ").name == "Fin de semana"


class TestUpdate:
    def test_updates_fields(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)
        created = repo.create(make_cleaning_type(cleaning_type_id=None))

        updated = repo.update(
            make_cleaning_type(
                cleaning_type_id=created.cleaning_type_id,
                name="Renombrada",
                hourly_rate=Decimal("22.00"),
                active=False,
            )
        )

        assert updated.name == "Renombrada"
        assert updated.hourly_rate == Decimal("22.00")
        assert updated.active is False

    def test_raises_when_missing(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)

        with pytest.raises(CleaningTypeNotFoundError):
            repo.update(make_cleaning_type(cleaning_type_id=999))

    def test_rename_to_existing_name_raises_already_exists(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)
        repo.create(make_cleaning_type(cleaning_type_id=None, name="Normal"))
        other = repo.create(make_cleaning_type(cleaning_type_id=None, name="Fin de semana"))

        with pytest.raises(CleaningTypeAlreadyExistsError):
            repo.update(make_cleaning_type(cleaning_type_id=other.cleaning_type_id, name="Normal"))


class TestDelete:
    def test_removes_type(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)
        created = repo.create(make_cleaning_type(cleaning_type_id=None))

        repo.delete(created.cleaning_type_id)

        assert repo.get_by_id(created.cleaning_type_id) is None

    def test_raises_when_missing(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)

        with pytest.raises(CleaningTypeNotFoundError):
            repo.delete(999)


class TestList:
    def test_active_only_filters_inactive(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)
        repo.create(make_cleaning_type(cleaning_type_id=None, name="Activa", active=True))
        repo.create(make_cleaning_type(cleaning_type_id=None, name="Inactiva", active=False))

        assert {ct.name for ct in repo.list()} == {"Activa", "Inactiva"}
        assert [ct.name for ct in repo.list(active_only=True)] == ["Activa"]

    def test_ordered_by_name(self, sqlite_session):
        repo = SQLAlchemyCleaningTypeRepository(sqlite_session)
        repo.create(make_cleaning_type(cleaning_type_id=None, name="Zeta"))
        repo.create(make_cleaning_type(cleaning_type_id=None, name="Alfa"))

        assert [ct.name for ct in repo.list()] == ["Alfa", "Zeta"]
