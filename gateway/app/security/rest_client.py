import json
import urllib.error
import urllib.request
from typing import Optional

from .. import config
from ..errors import (AuthenticationError, BusinessRuleError, NotFoundError, PermissionDeniedError, ValidationError)
from .client import AuthSecurityClient
from .identity import Identity

ERRORS = {"UNAUTHENTICATED": AuthenticationError, "FORBIDDEN": PermissionDeniedError, "NOT_FOUND": NotFoundError,
          "BAD_USER_INPUT": ValidationError, "BUSINESS_RULE_VIOLATION": BusinessRuleError}


class RestAuthSecurityClient(AuthSecurityClient):
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self._base = (base_url or config.AUTH_SERVICE_URL).rstrip("/")
        self._timeout = timeout or config.AUTH_TIMEOUT_SECONDS

    def _call(self, method: str, path: str, body: Optional[dict] = None, token: Optional[str] = None) -> dict:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self._base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            try:
                payload = json.loads(error.read())
            except ValueError:
                payload = {}
            raise ERRORS.get(payload.get("code"), AuthenticationError if error.code == 401 else ValidationError)(
                payload.get("detail", f"Auth Service вернул статус {error.code}"))
        except (urllib.error.URLError, TimeoutError):
            raise AuthenticationError("Сервис аутентификации недоступен, повторите попытку позже")

    def register(self, email: str, password: str, name: str) -> dict:
        return self._call("POST", "/auth/register", {"email": email, "password": password, "name": name})

    def login(self, email: str, password: str) -> dict:
        return self._call("POST", "/auth/login", {"email": email, "password": password})

    def verify(self, token: str) -> Identity:
        data = self._call("POST", "/auth/verify", token=token)
        return Identity(user_id=data["user_id"], role=data["role"], session_id=data["session_id"])

    def logout(self, token: str) -> bool:
        return bool(self._call("POST", "/auth/logout", token=token).get("revoked"))
