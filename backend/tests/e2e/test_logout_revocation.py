from datetime import UTC, datetime

import jwt
import pytest

from config import settings
from tests.e2e.test_auth_flows import _insert_user


def test_logout_revokes_access_and_refresh_even_when_password_pending(e2e_client, sqlite_session):
    _insert_user(sqlite_session, must_change_password=True)
    pair = e2e_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin-password"}
    ).json()
    headers = {"Authorization": "Bearer " + pair["access_token"]}
    assert e2e_client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert (
        e2e_client.post(
            "/api/v1/auth/change-initial-password",
            headers=headers,
            json={"new_password": "own-password"},
        ).status_code
        == 401
    )
    assert (
        e2e_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}
        ).status_code
        == 401
    )


@pytest.mark.parametrize("pending", [False, True])
def test_logout_with_expired_access_revokes_refresh(e2e_client, sqlite_session, pending):
    _insert_user(sqlite_session, must_change_password=pending)
    pair = e2e_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin-password"}
    ).json()
    claims = jwt.decode(
        pair["access_token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    claims["exp"] = int(datetime.now(UTC).timestamp()) - 1
    expired = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    response = e2e_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer " + expired},
        json={"refresh_token": pair["refresh_token"]},
    )
    assert response.status_code == 200
    assert (
        e2e_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}
        ).status_code
        == 401
    )
    assert (
        e2e_client.get(
            "/api/v1/bookings/", headers={"Authorization": "Bearer " + pair["access_token"]}
        ).status_code
        == 401
    )
    assert (
        e2e_client.post(
            "/api/v1/auth/logout", json={"refresh_token": pair["refresh_token"]}
        ).status_code
        == 401
    )


@pytest.mark.parametrize("invalid_kind", ["missing", "access", "tampered", "expired"])
def test_logout_rejects_invalid_credentials_without_revoking(
    e2e_client, sqlite_session, invalid_kind
):
    _insert_user(sqlite_session)
    pair = e2e_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin-password"}
    ).json()
    token = pair["refresh_token"]
    if invalid_kind == "access":
        token = pair["access_token"]
    elif invalid_kind == "tampered":
        token = "invalid." + token
    elif invalid_kind == "expired":
        claims = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        claims["exp"] = int(datetime.now(UTC).timestamp()) - 1
        token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    body = None if invalid_kind == "missing" else {"refresh_token": token}
    assert e2e_client.post("/api/v1/auth/logout", json=body).status_code == 401
    assert (
        e2e_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}
        ).status_code
        == 200
    )
