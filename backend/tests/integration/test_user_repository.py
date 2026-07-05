"""
Integration tests — SQLAlchemyUserRepository contra SQLite en memoria.

No se conecta a MySQL. El mismo Base.metadata crea la tabla users en SQLite.
"""

import pytest

from domain.auth.user_entity import NewUser, Role, User
from domain.exceptions import UserNotFound
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


class TestGetByEmail:
    def test_get_by_email_returns_user_entity_for_existing_email(self, sqlite_session):
        orm = _insert_user_orm(sqlite_session, email="cleaner@example.com")

        result = SQLAlchemyUserRepository(sqlite_session).get_by_email("cleaner@example.com")

        assert result is not None
        assert result.id == orm.id
        assert result.username == "admin"
        assert result.email == "cleaner@example.com"
        assert result.role == Role.ADMIN

    def test_get_by_email_returns_none_for_missing_email(self, sqlite_session):
        result = SQLAlchemyUserRepository(sqlite_session).get_by_email("missing@example.com")

        assert result is None


class TestCreateUser:
    def test_create_user_persists_user_entity(self, sqlite_session):
        repository = SQLAlchemyUserRepository(sqlite_session)

        repository.create_user(
            NewUser(
                username="cleaner",
                password="$2b$12$newhash",
                name="Cleaner",
                lastname="User",
                email="cleaner@example.com",
                role=Role.LIMPIADORA,
            )
        )

        stored = repository.get_by_username("cleaner")
        assert stored is not None
        assert stored.id is not None
        assert stored.password == "$2b$12$newhash"
        assert stored.email == "cleaner@example.com"
        assert stored.role == Role.LIMPIADORA


class TestUpdateUser:
    def test_update_user_persists_changed_fields(self, sqlite_session):
        orm = _insert_user_orm(sqlite_session)
        repository = SQLAlchemyUserRepository(sqlite_session)

        repository.update_user(
            User(
                id=orm.id,
                username="admin-updated",
                password="$2b$12$updatedhash",
                name="Admin Updated",
                lastname="Updated",
                email="admin-updated@example.com",
                role=Role.ADMIN,
            )
        )

        stored = repository.get_by_id(orm.id)
        assert stored is not None
        assert stored.username == "admin-updated"
        assert stored.password == "$2b$12$updatedhash"
        assert stored.name == "Admin Updated"
        assert stored.lastname == "Updated"
        assert stored.email == "admin-updated@example.com"

    def test_update_user_raises_user_not_found_for_missing_id(self, sqlite_session):
        repository = SQLAlchemyUserRepository(sqlite_session)

        with pytest.raises(UserNotFound):
            repository.update_user(
                User(
                    id=9999,
                    username="missing",
                    password="$2b$12$hash",
                    name="Missing",
                    role=Role.LIMPIADORA,
                )
            )


class TestDeleteUser:
    def test_delete_user_removes_existing_user(self, sqlite_session):
        orm = _insert_user_orm(sqlite_session)
        repository = SQLAlchemyUserRepository(sqlite_session)

        repository.delete_user(orm.id)

        assert repository.get_by_id(orm.id) is None

    def test_delete_user_raises_user_not_found_for_missing_id(self, sqlite_session):
        repository = SQLAlchemyUserRepository(sqlite_session)

        with pytest.raises(UserNotFound):
            repository.delete_user(9999)


class TestPasswordResetJti:
    def test_set_and_consume_password_reset_jti(self, sqlite_session):
        orm = _insert_user_orm(sqlite_session)
        repository = SQLAlchemyUserRepository(sqlite_session)

        repository.set_password_reset_jti(orm.id, "jti-abc")

        assert repository.consume_password_reset_jti(orm.id, "jti-abc") is True
        assert repository.consume_password_reset_jti(orm.id, "jti-abc") is False

    def test_consume_password_reset_jti_returns_false_for_wrong_jti(self, sqlite_session):
        orm = _insert_user_orm(sqlite_session)
        repository = SQLAlchemyUserRepository(sqlite_session)

        repository.set_password_reset_jti(orm.id, "jti-abc")

        assert repository.consume_password_reset_jti(orm.id, "jti-other") is False

    def test_set_password_reset_jti_raises_user_not_found_for_missing_id(self, sqlite_session):
        repository = SQLAlchemyUserRepository(sqlite_session)

        with pytest.raises(UserNotFound):
            repository.set_password_reset_jti(9999, "jti-abc")
