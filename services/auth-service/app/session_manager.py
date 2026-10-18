import time
import uuid
from dataclasses import asdict, is_dataclass
from typing import Callable, Optional

from . import jwt_utils
from .errors import AuthenticationError, NotFoundError
from .sessions import SessionStore


def _as_dict(user) -> dict:
    return asdict(user) if is_dataclass(user) else dict(user)


class SessionManager:
    def __init__(self, directory, store: SessionStore, secret: str, issuer: str = "plant-detective-auth",
                 jwt_ttl: int = 3600, session_ttl: int = 1800, sliding: bool = True,
                 clock: Callable[[], float] = time.time):
        self._directory, self._store = directory, store
        self._secret, self._issuer = secret, issuer
        self._jwt_ttl, self._session_ttl, self._sliding, self._clock = jwt_ttl, session_ttl, sliding, clock

    def register(self, email: str, password: str, name: str) -> dict:
        return _as_dict(self._directory.register(email, password, name))

    def login(self, email: str, password: str) -> dict:
        user = self._directory.authenticate(email, password)          
        session = self._store.create(user.id, user.role, self._session_ttl)
        now = int(self._clock())
        token = jwt_utils.encode({"sub": user.id, "role": user.role, "sid": session.session_id,
                                  "iss": self._issuer, "iat": now, "exp": now + self._jwt_ttl,
                                  "jti": uuid.uuid4().hex}, self._secret)
        return {"access_token": token, "token_type": "Bearer",
                "expires_in": min(self._jwt_ttl, self._session_ttl),
                "session_id": session.session_id, "user": _as_dict(user)}

    def _claims(self, token: str) -> dict:
        try:
            return jwt_utils.decode(token, self._secret, self._issuer, self._clock())
        except jwt_utils.ExpiredTokenError:
            raise AuthenticationError("Срок действия токена истёк, выполните вход заново")
        except jwt_utils.TokenError:
            raise AuthenticationError("Недействительный токен")

    def verify(self, token: str) -> dict:
        claims = self._claims(token)
        session = self._store.get(claims.get("sid", ""))
        if session is None or session.user_id != claims.get("sub"):
            raise AuthenticationError("Сессия отсутствует или истекла, выполните вход заново")
        try:
            user = self._directory.get_user(session.user_id)
        except NotFoundError:
            self._store.delete(session.session_id)
            raise AuthenticationError("Пользователь не найден")
        if user.status != "ACTIVE":
            self._store.delete_all_for_user(user.id)
            raise AuthenticationError("Учётная запись заблокирована")
        if self._sliding:
            self._store.touch(session.session_id, self._session_ttl)
        return {"user_id": user.id, "role": user.role, "status": user.status, "session_id": session.session_id}

    def logout(self, token: str) -> bool:
        identity = self.verify(token)
        return self._store.delete(identity["session_id"])

    def logout_all(self, token: str) -> int:
        identity = self.verify(token)
        return self._store.delete_all_for_user(identity["user_id"])

    def revoke_user_sessions(self, user_id: str) -> int:
        return self._store.delete_all_for_user(user_id)
