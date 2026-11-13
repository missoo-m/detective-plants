import pytest
from fastapi.testclient import TestClient

from app import config
from app.api import create_app
from app.session_manager import SessionManager
from app.sessions import InMemorySessionStore
from tests.test_session_manager import Directory


@pytest.fixture
def directory():
    return Directory()


@pytest.fixture
def client(directory):
    manager = SessionManager(directory, InMemorySessionStore(), "test-secret", "auth", session_ttl=600)
    return TestClient(create_app(manager))


def login(client, email="anna@example.com", password="password123"):
    return client.post("/auth/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_register_and_login(client):
    created = client.post("/auth/register", json={"email": "new@example.com", "password": "strongpass1", "name": "Новая"})
    assert created.status_code == 201 and created.json()["role"] == "CLIENT"
    response = login(client, "new@example.com", "strongpass1")
    assert response.status_code == 200 and response.json()["token_type"] == "Bearer"


def test_login_with_bad_password_is_403(client):
    response = login(client, password="wrong")
    assert response.status_code == 403 and response.json()["code"] == "FORBIDDEN"


def test_verify_requires_valid_token(client):
    token = login(client).json()["access_token"]
    ok = client.post("/auth/verify", headers=bearer(token))
    assert ok.status_code == 200 and ok.json()["user_id"] == "u-1" and ok.json()["role"] == "CLIENT"
    missing = client.post("/auth/verify")
    assert missing.status_code == 401 and missing.json()["code"] == "UNAUTHENTICATED"
    assert client.post("/auth/verify", headers=bearer("garbage")).status_code == 401


def test_logout_invalidates_token(client):
    token = login(client).json()["access_token"]
    assert client.post("/auth/logout", headers=bearer(token)).json() == {"revoked": True}
    again = client.post("/auth/verify", headers=bearer(token))
    assert again.status_code == 401 and "Сессия" in again.json()["detail"]


def test_logout_all(client):
    first, second = (login(client).json()["access_token"] for _ in range(2))
    assert client.post("/auth/logout-all", headers=bearer(first)).json() == {"revoked": 2}
    assert client.post("/auth/verify", headers=bearer(second)).status_code == 401


def test_internal_api_requires_key(client, directory):
    directory.set_status = lambda user_id, status: setattr(directory.users[user_id], "status", status) or directory.users[user_id]
    denied = client.put("/internal/users/u-1/status", json={"value": "BLOCKED"})
    assert denied.status_code == 403
    token = login(client).json()["access_token"]
    done = client.put("/internal/users/u-1/status", json={"value": "BLOCKED"},
                      headers={"X-Internal-Key": config.INTERNAL_API_KEY})
    assert done.status_code == 200 and done.json()["revoked_sessions"] == 1
    assert client.post("/auth/verify", headers=bearer(token)).status_code == 401
