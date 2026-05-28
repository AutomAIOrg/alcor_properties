"""
Integration tests — SQLAlchemyUserRepository contra SQLite en memoria.

No se conecta a MySQL. El mismo Base.metadata crea la tabla users en SQLite.
"""

import pytest

from domain.auth.user_entity import Role
from infrastructure.models.user import UserORM
from infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository

pytestmark = pytest.mark.integration


def _insert_user_orm(session, **overrides) -> UserORM:
    """Inserta un UserORM con valores por defecto aplicando los overrides dados."""
    defaults = {
        "username": "admin",
        "password": "$2b$12$storedhash",
        "name": "Admin",
        "lastname": "User",
        "email": "admin@example.com",
        "role": Role.ADMIN.value,
    }
    orm = UserORM(**{**defaults, **overrides})
    session.add(orm)
    session.commit()
    session.refresh(orm)
    return orm


class TestGetByUsername:
    def test_get_by_username_returns_user_entity_for_existing_username(self, sqlite_session):
        orm = _insert_user_orm(sqlite_session)

        result = SQLAlchemyUserRepository(sqlite_session).get_by_username("admin")

        assert result is not None
        assert result.id == orm.id
        assert result.username == "admin"
        assert result.password == "$2b$12$storedhash"
        assert result.email == "admin@example.com"
        assert result.role == Role.ADMIN

    def test_get_by_username_returns_none_for_missing_username(self, sqlite_session):
        result = SQLAlchemyUserRepository(sqlite_session).get_by_username("missing")

        assert result is None


class TestGetById:
    def test_get_by_id_returns_user_entity_for_existing_id(self, sqlite_session):
        orm = _insert_user_orm(sqlite_session)

        result = SQLAlchemyUserRepository(sqlite_session).get_by_id(orm.id)

        assert result is not None
        assert result.id == orm.id
        assert result.username == "admin"
        assert result.role == Role.ADMIN

    def test_get_by_id_returns_none_for_missing_id(self, sqlite_session):
        result = SQLAlchemyUserRepository(sqlite_session).get_by_id(9999)

        assert result is None
