import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Callable, Optional

from .. import config
from ..errors import AuthenticationError
from .client import AuthSecurityClient
from .identity import Identity


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


class MockAuthSecurityClient(AuthSecurityClient):
    def __init__(self, directory_provider: Callable[[], object], secret: Optional[str] = None,
                 session_ttl: Optional[int] = None, jwt_ttl: int = 3600, clock: Callable[[], float] = time.time):
        self._directory = directory_provider          # возвращает mock-клиент пользователей (ленивая привязка)
        self._secret = (secret or config.MOCK_JWT_SECRET).encode()
        self._session_ttl = session_ttl or config.MOCK_SESSION_TTL
        self._jwt_ttl, self._clock = jwt_ttl, clock
        self.sessions: dict[str, dict] = {}

    # ---- JWT
    def _sign(self, signing_input: str) -> str:
        return _b64(hmac.new(self._secret, signing_input.encode(), hashlib.sha256).digest())

    def _encode(self, claims: dict) -> str:
        head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        body = _b64(json.dumps(claims, sort_keys=True).encode())
        return f"{head}.{body}.{self._sign(f'{head}.{body}')}"

    def _decode(self, token: str) -> dict:
        parts = (token or "").split(".")
        if len(parts) != 3:
            raise AuthenticationError("Недействительный токен")
        try:
            header, claims = json.loads(_unb64(parts[0])), json.loads(_unb64(parts[1]))
        except ValueError:
            raise AuthenticationError("Недействительный токен")
        if header.get("alg") != "HS256" or not hmac.compare_digest(self._sign(f"{parts[0]}.{parts[1]}"), parts[2]):
            raise AuthenticationError("Недействительный токен")
        if claims.get("exp", 0) <= self._clock():
            raise AuthenticationError("Срок действия токена истёк, выполните вход заново")
        return claims

    def register(self, email: str, password: str, name: str) -> dict:
        return self._directory().register(email, password, name)

    def login(self, email: str, password: str) -> dict:
        user = self._directory().login(email, password)["user"]            
        session_id, now = uuid.uuid4().hex, int(self._clock())
        self.sessions[session_id] = {"user_id": user["id"], "expires_at": self._clock() + self._session_ttl}
        token = self._encode({"sub": user["id"], "role": user["role"], "sid": session_id, "iat": now,
                              "exp": now + self._jwt_ttl, "iss": "mock-auth"})
        return {"access_token": token, "token_type": "Bearer", "expires_in": min(self._jwt_ttl, self._session_ttl),
                "session_id": session_id, "user": user}

    def verify(self, token: str) -> Identity:
        claims = self._decode(token)
        session = self.sessions.get(claims.get("sid", ""))
        if session is None or session["expires_at"] <= self._clock() or session["user_id"] != claims.get("sub"):
            self.sessions.pop(claims.get("sid", ""), None)
            raise AuthenticationError("Сессия отсутствует или истекла, выполните вход заново")
        try:
            user = self._directory().get_user(session["user_id"])
        except Exception:
            raise AuthenticationError("Пользователь не найден")
        if user["status"] != "ACTIVE":
            self.revoke_user_sessions(user["id"])
            raise AuthenticationError("Учётная запись заблокирована")
        session["expires_at"] = self._clock() + self._session_ttl          
        return Identity(user_id=user["id"], role=user["role"], session_id=claims["sid"])

    def logout(self, token: str) -> bool:
        identity = self.verify(token)
        return self.sessions.pop(identity.session_id, None) is not None

    def revoke_user_sessions(self, user_id: str) -> int:
        ids = [sid for sid, s in self.sessions.items() if s["user_id"] == user_id]
        for sid in ids:
            del self.sessions[sid]
        return len(ids)
