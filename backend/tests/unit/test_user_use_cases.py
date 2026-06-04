"""
Unit tests — casos de uso de usuarios.

El repositorio y el gestor de contraseñas se sustituyen por mocks para aislar
las reglas de negocio de creación, actualización y borrado.
"""

from unittest.mock import MagicMock

import pytest

from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from application.users.create_user_use_case import CreateUserUseCase
from application.users.delete_user_use_case import DeleteUserUseCase
from application.users.update_user_use_case import UpdateUserUseCase
from domain.auth.user_entity import Role
from domain.exceptions import IntegrityError, UserAlreadyExists, UserNotFound
from tests.helpers import make_user

pytestmark = pytest.mark.unit


@pytest.fixture
def user_repository() -> MagicMock:
    return MagicMock(spec=IUserRepository)


@pytest.fixture
def password_manager() -> MagicMock:
    return MagicMock(spec=IPasswordManager)


# ---------------------------------------------------------------------------
# CreateUserUseCase
# ---------------------------------------------------------------------------


class TestCreateUserUseCase:
    def test_hashes_password_and_persists_new_user(self, user_repository, password_manager):
        user = make_user(id=None, username="cleaner", password="initial-password")
        user_repository.get_by_username.return_value = None
        user_repository.get_by_email.return_value = None
        password_manager.hash.return_value = "hashed-password"

        CreateUserUseCase(user_repository, password_manager).execute(user)

        user_repository.get_by_username.assert_called_once_with("cleaner")
        user_repository.get_by_email.assert_called_once_with("admin@example.com")
        password_manager.hash.assert_called_once_with("initial-password")
        user_repository.create_user.assert_called_once()
        persisted_user = user_repository.create_user.call_args.args[0]
        assert persisted_user.password == "hashed-password"

    def test_duplicate_username_raises_user_already_exists(self, user_repository, password_manager):
        user_repository.get_by_username.return_value = make_user(username="cleaner")

        with pytest.raises(UserAlreadyExists):
            CreateUserUseCase(user_repository, password_manager).execute(
                make_user(username="cleaner", password="initial-password")
            )

        user_repository.get_by_email.assert_not_called()
        password_manager.hash.assert_not_called()
        user_repository.create_user.assert_not_called()

    def test_duplicate_email_raises_integrity_error(self, user_repository, password_manager):
        user_repository.get_by_username.return_value = None
        user_repository.get_by_email.return_value = make_user(id=99, email="used@example.com")

        with pytest.raises(IntegrityError):
            CreateUserUseCase(user_repository, password_manager).execute(
                make_user(id=None, email="used@example.com", password="initial-password")
            )

        password_manager.hash.assert_not_called()
        user_repository.create_user.assert_not_called()

    def test_email_lookup_is_skipped_when_email_is_none(self, user_repository, password_manager):
        user_repository.get_by_username.return_value = None
        password_manager.hash.return_value = "hashed-password"

        CreateUserUseCase(user_repository, password_manager).execute(
            make_user(id=None, email=None, password="initial-password")
        )

        user_repository.get_by_email.assert_not_called()
        user_repository.create_user.assert_called_once()


# ---------------------------------------------------------------------------
# UpdateUserUseCase
# ---------------------------------------------------------------------------


class TestUpdateUserUseCase:
    def test_updates_user_data_and_preserves_existing_password(self, user_repository):
        existing = make_user(
            id=1,
            username="admin",
            password="stored-hash",
            name="Admin",
            lastname="Old",
            email="admin@example.com",
            role=Role.ADMIN,
        )
        user_repository.get_by_id.return_value = existing
        user_repository.get_by_username.return_value = existing
        user_repository.get_by_email.return_value = existing

        UpdateUserUseCase(user_repository).execute(
            make_user(
                id=1,
                username="admin",
                password=None,
                name="Admin Updated",
                lastname="New",
                email="admin@example.com",
                role=Role.ADMIN,
            )
        )

        user_repository.update_user.assert_called_once()
        updated_user = user_repository.update_user.call_args.args[0]
        assert updated_user.name == "Admin Updated"
        assert updated_user.lastname == "New"
        assert updated_user.password == "stored-hash"

    def test_missing_user_raises_user_not_found(self, user_repository):
        user_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFound):
            UpdateUserUseCase(user_repository).execute(make_user(id=404))

        user_repository.update_user.assert_not_called()

    def test_username_used_by_another_user_raises_integrity_error(self, user_repository):
        user_repository.get_by_id.return_value = make_user(id=1, username="admin")
        user_repository.get_by_username.return_value = make_user(id=2, username="other")

        with pytest.raises(IntegrityError):
            UpdateUserUseCase(user_repository).execute(make_user(id=1, username="other"))

        user_repository.update_user.assert_not_called()

    def test_email_used_by_another_user_raises_integrity_error(self, user_repository):
        user_repository.get_by_id.return_value = make_user(id=1, email="admin@example.com")
        user_repository.get_by_username.return_value = make_user(id=1, username="admin")
        user_repository.get_by_email.return_value = make_user(id=2, email="used@example.com")

        with pytest.raises(IntegrityError):
            UpdateUserUseCase(user_repository).execute(make_user(id=1, email="used@example.com"))

        user_repository.update_user.assert_not_called()

    def test_email_lookup_is_skipped_when_email_is_none(self, user_repository):
        existing = make_user(id=1, email="admin@example.com", role=Role.ADMIN)
        user_repository.get_by_id.return_value = existing
        user_repository.get_by_username.return_value = existing

        UpdateUserUseCase(user_repository).execute(make_user(id=1, email=None, role=Role.ADMIN))

        user_repository.get_by_email.assert_not_called()
        user_repository.update_user.assert_called_once()

    def test_admin_cannot_be_downgraded_to_cleaner(self, user_repository):
        user_repository.get_by_id.return_value = make_user(id=1, role=Role.ADMIN)
        user_repository.get_by_username.return_value = make_user(id=1, username="admin")
        user_repository.get_by_email.return_value = make_user(id=1, email="admin@example.com")

        with pytest.raises(IntegrityError):
            UpdateUserUseCase(user_repository).execute(make_user(id=1, role=Role.LIMPIADORA))

        user_repository.update_user.assert_not_called()


# ---------------------------------------------------------------------------
# DeleteUserUseCase
# ---------------------------------------------------------------------------


class TestDeleteUserUseCase:
    def test_deletes_existing_user_when_it_is_not_current_user(self, user_repository):
        user_repository.get_by_id.return_value = make_user(id=2, username="cleaner")

        DeleteUserUseCase(user_repository).execute(user_id=2, current_user=make_user(id=1))

        user_repository.delete_user.assert_called_once_with(2)

    def test_missing_user_raises_user_not_found(self, user_repository):
        user_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFound):
            DeleteUserUseCase(user_repository).execute(user_id=404, current_user=make_user(id=1))

        user_repository.delete_user.assert_not_called()

    def test_current_user_cannot_delete_itself(self, user_repository):
        user_repository.get_by_id.return_value = make_user(id=1)

        with pytest.raises(IntegrityError):
            DeleteUserUseCase(user_repository).execute(user_id=1, current_user=make_user(id=1))

        user_repository.delete_user.assert_not_called()
