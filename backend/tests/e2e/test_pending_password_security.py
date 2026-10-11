import pytest

from tests.e2e.test_auth_flows import _insert_user


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/bookings/",
        "/api/v1/apartments/",
        "/api/v1/users/",
        "/api/v1/bills/",
        "/api/v1/cleaning-types/",
    ],
)
def test_pending_password_blocks_direct_api_requests(e2e_client, sqlite_session, path):
    _insert_user(sqlite_session, must_change_password=True)
    pair = e2e_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin-password"}
    ).json()
    response = e2e_client.get(path, headers={"Authorization": "Bearer " + pair["access_token"]})
    assert response.status_code == 403


def test_pending_refresh_denied_and_old_pair_revoked_after_change(e2e_client, sqlite_session):
    _insert_user(sqlite_session, must_change_password=True)
    pair = e2e_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin-password"}
    ).json()
    assert (
        e2e_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}
        ).status_code
        == 403
    )
    changed = e2e_client.post(
        "/api/v1/auth/change-initial-password",
        headers={"Authorization": "Bearer " + pair["access_token"]},
        json={"new_password": "different-password"},
    )
    assert changed.status_code == 200
    assert (
        e2e_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}
        ).status_code
        == 401
    )
    assert (
        e2e_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": changed.json()["refresh_token"]}
        ).status_code
        == 200
    )
