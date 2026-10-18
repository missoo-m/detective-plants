from dataclasses import dataclass

import pytest

from app import jwt_utils
from app.errors import AuthenticationError, PermissionDeniedError, NotFoundError
from app.session_manager import SessionManager
from app.sessions import InMemorySessionStore

SECRET = "test-secret"


@dataclass
class User:
    id: str
    email: str
    name: str
    role: str
    status: str


class Directory:

    def __init__(self):
        self.users = {"u-1": User("u-1", "anna@example.com", "Анна", "CLIENT", "ACTIVE"),
                      "u-2": User("u-2", "ivan@example.com", "Иван", "EXPERT", "ACTIVE")}
        self.passwords = {"anna@example.com": "password123", "ivan@example.com": "password123"}

    def authenticate(self, email, password):
        user = next((u for u in self.users.values() if u.email == email), None)
        if user is None or self.passwords.get(email) != password:
            raise PermissionDeniedError("Неверный email или пароль")
        if user.status != "ACTIVE":
            raise PermissionDeniedError("Учётная запись заблокирована")
        return user

    def get_user(self, user_id):
        if user_id not in self.users:
            raise NotFoundError("нет такого пользователя")
        return self.users[user_id]

    def register(self, email, password, name):
        user = User(f"u-{len(self.users) + 1}", email, name, "CLIENT", "ACTIVE")
        self.users[user.id] = user
        self.passwords[email] = password
        return user


class Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def directory():
    return Directory()


@pytest.fixture
def store(clock):
    return InMemorySessionStore(clock)


@pytest.fixture
def manager(directory, store, clock):
    return SessionManager(directory, store, SECRET, "auth", jwt_ttl=3600, session_ttl=600, sliding=True, clock=clock)


def test_login_issues_jwt_and_creates_session(manager, store):
    result = manager.login("anna@example.com", "password123")
    claims = jwt_utils.decode(result["access_token"], SECRET, "auth", now=1_000_000)
    assert claims["sub"] == "u-1" and claims["role"] == "CLIENT" and claims["sid"] == result["session_id"]
    assert store.get(result["session_id"]) is not None and result["expires_in"] == 600
    assert result["token_type"] == "Bearer" and result["user"]["email"] == "anna@example.com"


def test_login_rejects_bad_credentials(manager, directory):
    with pytest.raises(PermissionDeniedError):
        manager.login("anna@example.com", "wrong")
    directory.users["u-1"].status = "BLOCKED"
    with pytest.raises(PermissionDeniedError):
        manager.login("anna@example.com", "password123")


def test_verify_returns_identity(manager):
    token = manager.login("ivan@example.com", "password123")["access_token"]
    identity = manager.verify(token)
    assert identity["user_id"] == "u-2" and identity["role"] == "EXPERT" and identity["status"] == "ACTIVE"


def test_valid_jwt_without_session_is_rejected(manager, store):
    result = manager.login("anna@example.com", "password123")
    store.delete(result["session_id"])                                   #
    with pytest.raises(AuthenticationError, match="Сессия"):
        manager.verify(result["access_token"])


def test_session_expires_after_ttl_even_if_jwt_is_valid(manager, clock):
    token = manager.login("anna@example.com", "password123")["access_token"]
    clock.now += 601                                                     # TTL сессии 600 с, JWT ещё жив (3600 с)
    with pytest.raises(AuthenticationError, match="Сессия"):
        manager.verify(token)


def test_sliding_session_extends_on_activity(manager, clock):
    token = manager.login("anna@example.com", "password123")["access_token"]
    for _ in range(3):
        clock.now += 400                                                 # каждое обращение продлевает сессию
        assert manager.verify(token)["user_id"] == "u-1"
    clock.now += 700
    with pytest.raises(AuthenticationError):
        manager.verify(token)


def test_expired_jwt(manager, clock, store):
    manager2 = SessionManager(manager._directory, store, SECRET, "auth", jwt_ttl=100, session_ttl=600, clock=clock)
    token = manager2.login("anna@example.com", "password123")["access_token"]
    clock.now += 101
    with pytest.raises(AuthenticationError, match="истёк"):
        manager2.verify(token)


def test_tampered_and_foreign_tokens(manager):
    token = manager.login("anna@example.com", "password123")["access_token"]
    with pytest.raises(AuthenticationError, match="Недействительный"):
        manager.verify(token[:-3] + "abc")
    foreign = jwt_utils.encode({"sub": "u-1", "sid": "x", "iss": "auth", "exp": 2_000_000}, "other-secret")
    with pytest.raises(AuthenticationError):
        manager.verify(foreign)
    with pytest.raises(AuthenticationError):
        manager.verify("")


def test_session_of_another_user_is_not_accepted(manager, store):
    result = manager.login("anna@example.com", "password123")
    other = store.create("u-2", "EXPERT", 600)
    forged = jwt_utils.encode({"sub": "u-1", "sid": other.session_id, "iss": "auth", "exp": 2_000_000}, SECRET)
    with pytest.raises(AuthenticationError):
        manager.verify(forged)


def test_blocked_user_loses_access(manager, directory, store):
    token = manager.login("anna@example.com", "password123")["access_token"]
    directory.users["u-1"].status = "BLOCKED"
    with pytest.raises(AuthenticationError, match="заблокирована"):
        manager.verify(token)
    assert store.list_for_user("u-1") == []


def test_role_change_applies_immediately(manager, directory):
    token = manager.login("anna@example.com", "password123")["access_token"]
    directory.users["u-1"].role = "EXPERT"
    assert manager.verify(token)["role"] == "EXPERT"


def test_logout_and_logout_all(manager, store):
    t1 = manager.login("anna@example.com", "password123")["access_token"]
    t2 = manager.login("anna@example.com", "password123")["access_token"]
    assert manager.logout(t1) is True
    with pytest.raises(AuthenticationError):
        manager.verify(t1)
    assert manager.verify(t2)["user_id"] == "u-1"
    assert manager.logout_all(t2) == 1
    with pytest.raises(AuthenticationError):
        manager.verify(t2)


def test_revoke_user_sessions(manager):
    t = manager.login("ivan@example.com", "password123")["access_token"]
    assert manager.revoke_user_sessions("u-2") == 1
    with pytest.raises(AuthenticationError):
        manager.verify(t)


def test_register(manager):
    user = manager.register("new@example.com", "strongpass1", "Новая")
    assert user["role"] == "CLIENT" and manager.login("new@example.com", "strongpass1")["user"]["id"] == user["id"]
