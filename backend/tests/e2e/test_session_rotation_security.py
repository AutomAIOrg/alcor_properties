from tests.e2e.test_auth_flows import _insert_user


def login(client):
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin-password"}
    )
    assert response.status_code == 200
    return response.json()


def refresh(client, token):
    return client.post("/api/v1/auth/refresh", json={"refresh_token": token})


def access(client, token):
    return client.get("/api/v1/bookings/", headers={"Authorization": "Bearer " + token})


def test_reuse_revokes_only_compromised_family(e2e_client, sqlite_session):
    _insert_user(sqlite_session)
    a, b = login(e2e_client), login(e2e_client)
    rotated = refresh(e2e_client, a["refresh_token"])
    assert rotated.status_code == 200
    pair = rotated.json()
    assert pair["refresh_token"] != a["refresh_token"]
    assert pair["access_token"] != a["access_token"]
    assert refresh(e2e_client, a["refresh_token"]).status_code == 401
    assert refresh(e2e_client, pair["refresh_token"]).status_code == 401
    assert access(e2e_client, pair["access_token"]).status_code == 401
    assert access(e2e_client, a["access_token"]).status_code == 401
    assert access(e2e_client, b["access_token"]).status_code == 200
    assert refresh(e2e_client, b["refresh_token"]).status_code == 200
