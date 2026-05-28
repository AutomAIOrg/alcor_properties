"""
End-to-end tests — flujos reales de autenticación y autorización.

Stack: TestClient → LoginUseCase real → SQLAlchemyUserRepository → SQLite en memoria.
"""

import pytest
from passlib.context import CryptContext

from domain.auth.user_entity import Role
from infrastructure.models.user import UserORM

pytestmark = pytest.mark.e2e


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
