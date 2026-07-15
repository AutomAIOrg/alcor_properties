"""
End-to-end tests — flujos reales de autenticación y autorización.

Stack: TestClient → LoginUseCase real → SQLAlchemyUserRepository → SQLite en memoria.
"""

import jwt
import pytest
from passlib.context import CryptContext

from config import settings
from domain.auth.user_entity import Role
from infrastructure.models.user import UserORM

pytestmark = pytest.mark.e2e


def _claims(token: str) -> dict:
    """Devuelve los claims de un token emitido por la aplicación."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def _insert_user(session, **overrides) -> UserORM:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    defaults = {
        "username": "admin",
        "password": pwd_context.hash("admin-password"),
        "name": "Admin",
        "lastname": "User",
        "email": "admin@example.com",
        "role": Role.ADMIN.value,
    }
    user = UserORM(**{**defaults, **overrides})
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


class TestAuthenticationFlows:
    def test_admin_can_login_and_access_protected_bookings(self, e2e_client, sqlite_session):
        _insert_user(sqlite_session)

        login_response = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-password"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["token_type"] == "bearer"

        token = login_response.json()["access_token"]
        assert login_response.json()["refresh_token"]
        response = e2e_client.get(
            "/api/v1/bookings/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_cleaner_can_login_but_cannot_access_admin_bookings(self, e2e_client, sqlite_session):
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        _insert_user(
            sqlite_session,
            username="cleaner",
            password=pwd_context.hash("cleaner-password"),
            name="Cleaner",
            email="cleaner@example.com",
            role=Role.LIMPIADORA.value,
        )

        login_response = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "cleaner", "password": "cleaner-password"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        response = e2e_client.get(
            "/api/v1/bookings/",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_refresh_token_renews_access_to_protected_bookings(self, e2e_client, sqlite_session):
        _insert_user(sqlite_session)
        login_response = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-password"},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        refresh_response = e2e_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200

        access_token = refresh_response.json()["access_token"]
        response = e2e_client.get(
            "/api/v1/bookings/",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_access_token_cannot_be_used_as_refresh_token(self, e2e_client, sqlite_session):
        _insert_user(sqlite_session)
        login_response = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-password"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        response = e2e_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401


class TestInitialPasswordFlows:
    """
    Flujo de contraseña inicial obligatoria: alta o restablecimiento por el
    administrador dejan al usuario con la contraseña inicial del sistema, y hasta
    que fija una propia sus tokens llevan la marca `mcp`.
    """

    def test_new_user_must_change_password_then_keeps_working_session(
        self, e2e_client, sqlite_session
    ):
        # El admin da de alta al usuario, que nace con la contraseña inicial.
        admin = _insert_user(sqlite_session)
        admin_login = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-password"},
        )
        admin_token = admin_login.json()["access_token"]
        assert admin.id

        create_response = e2e_client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "limpiadora",
                "name": "Nueva",
                "lastname": "Limpiadora",
                "email": "limpiadora@example.com",
                "role": "limpiadora",
            },
        )
        assert create_response.status_code == 200

        # Entra por primera vez con la contraseña inicial: el token pide el cambio.
        login_response = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "limpiadora", "password": settings.DEFAULT_PASSWORD},
        )
        assert login_response.status_code == 200
        first_token = login_response.json()["access_token"]
        assert _claims(first_token)["mcp"] is True

        # Fija su contraseña propia sin aportar la actual y sigue autenticado.
        change_response = e2e_client.post(
            "/api/v1/auth/change-initial-password",
            headers={"Authorization": f"Bearer {first_token}"},
            json={"new_password": "propia123"},
        )
        assert change_response.status_code == 200
        new_token = change_response.json()["access_token"]
        assert _claims(new_token)["mcp"] is False

        # Los tokens nuevos sirven para operar; los previos han quedado revocados.
        assert (
            e2e_client.get(
                "/api/v1/bookings/cleaning-opportunities",
                headers={"Authorization": f"Bearer {new_token}"},
            ).status_code
            == 200
        )
        assert (
            e2e_client.get(
                "/api/v1/bookings/cleaning-opportunities",
                headers={"Authorization": f"Bearer {first_token}"},
            ).status_code
            == 401
        )

        # La contraseña inicial ya no vale; la nueva sí, y sin pedir más cambios.
        assert (
            e2e_client.post(
                "/api/v1/auth/login",
                json={"username": "limpiadora", "password": settings.DEFAULT_PASSWORD},
            ).status_code
            == 401
        )
        relogin = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "limpiadora", "password": "propia123"},
        )
        assert relogin.status_code == 200
        assert _claims(relogin.json()["access_token"])["mcp"] is False

    def test_admin_reset_forces_the_user_to_change_password_again(self, e2e_client, sqlite_session):
        _insert_user(sqlite_session)
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        target = _insert_user(
            sqlite_session,
            username="cleaner",
            password=pwd_context.hash("propia123"),
            name="Cleaner",
            email="cleaner@example.com",
            role=Role.LIMPIADORA.value,
        )

        # Con su contraseña propia el usuario entra sin que se le pida nada.
        before = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "cleaner", "password": "propia123"},
        )
        assert _claims(before.json()["access_token"])["mcp"] is False

        admin_token = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-password"},
        ).json()["access_token"]
        reset_response = e2e_client.post(
            f"/api/v1/users/{target.id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert reset_response.status_code == 200

        # Tras el restablecimiento vuelve a la contraseña inicial y se le exige cambiarla.
        after = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "cleaner", "password": settings.DEFAULT_PASSWORD},
        )
        assert after.status_code == 200
        assert _claims(after.json()["access_token"])["mcp"] is True

    def test_user_without_pending_change_cannot_use_the_initial_password_endpoint(
        self, e2e_client, sqlite_session
    ):
        _insert_user(sqlite_session)
        token = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-password"},
        ).json()["access_token"]

        response = e2e_client.post(
            "/api/v1/auth/change-initial-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"new_password": "otra1234"},
        )

        assert response.status_code == 422
