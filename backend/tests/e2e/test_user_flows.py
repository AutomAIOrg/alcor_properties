"""
End-to-end tests — flujos reales de administración de usuarios.

Stack: TestClient → rutas users → use cases reales → SQLAlchemyUserRepository → SQLite.
"""

import pytest
from passlib.context import CryptContext

from config import settings
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


def _login_headers(client, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class TestAdminUserFlows:
    def test_admin_can_create_list_update_login_and_delete_user(self, e2e_client, sqlite_session):
        _insert_user(sqlite_session)
        headers = _login_headers(e2e_client, "admin", "admin-password")

        create_response = e2e_client.post(
            "/api/v1/users/",
            json={
                "username": "cleaner",
                "name": "Cleaner",
                "lastname": "User",
                "email": "cleaner@example.com",
                "role": Role.LIMPIADORA.value,
            },
            headers=headers,
        )
        assert create_response.status_code == 200

        list_response = e2e_client.get("/api/v1/users/", headers=headers)
        assert list_response.status_code == 200
        users = list_response.json()
        created_user = next(user for user in users if user["username"] == "cleaner")

        update_response = e2e_client.put(
            f"/api/v1/users/{created_user['id']}",
            json={
                "username": "cleaner",
                "name": "Cleaner Updated",
                "lastname": "User",
                "email": "cleaner@example.com",
                "role": Role.LIMPIADORA.value,
            },
            headers=headers,
        )
        assert update_response.status_code == 200

        # La actualización de datos administrativos no debe invalidar la contraseña inicial.
        login_response = e2e_client.post(
            "/api/v1/auth/login",
            json={"username": "cleaner", "password": settings.DEFAULT_PASSWORD},
        )
        assert login_response.status_code == 200

        delete_response = e2e_client.delete(f"/api/v1/users/{created_user['id']}", headers=headers)
        assert delete_response.status_code == 200

        final_users = e2e_client.get("/api/v1/users/", headers=headers).json()
        assert all(user["username"] != "cleaner" for user in final_users)

    def test_admin_cannot_delete_itself(self, e2e_client, sqlite_session):
        admin = _insert_user(sqlite_session)
        headers = _login_headers(e2e_client, "admin", "admin-password")

        response = e2e_client.delete(f"/api/v1/users/{admin.id}", headers=headers)

        assert response.status_code == 409
        assert response.json() == {"detail": "No puedes eliminar tu propio usuario."}

    def test_admin_cannot_downgrade_admin_role(self, e2e_client, sqlite_session):
        admin = _insert_user(sqlite_session)
        headers = _login_headers(e2e_client, "admin", "admin-password")

        response = e2e_client.put(
            f"/api/v1/users/{admin.id}",
            json={
                "username": "admin",
                "name": "Admin",
                "lastname": "User",
                "email": "admin@example.com",
                "role": Role.LIMPIADORA.value,
            },
            headers=headers,
        )

        assert response.status_code == 409
        assert response.json() == {
            "detail": "No se puede actualizar el rol de administrador a un rol diferente"
        }

    def test_cleaner_cannot_access_users_endpoint(self, e2e_client, sqlite_session):
        _insert_user(
            sqlite_session,
            username="cleaner",
            password=CryptContext(schemes=["bcrypt"], deprecated="auto").hash("cleaner-password"),
            name="Cleaner",
            email="cleaner@example.com",
            role=Role.LIMPIADORA.value,
        )
        headers = _login_headers(e2e_client, "cleaner", "cleaner-password")

        response = e2e_client.get("/api/v1/users/", headers=headers)

        assert response.status_code == 403
