import base64
import hashlib
import hmac
import json
import time
from typing import Optional


class TokenError(Exception):
    pass


class InvalidTokenError(TokenError):
    pass


class ExpiredTokenError(TokenError):
    pass


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(part: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
    except Exception:
        raise InvalidTokenError("Некорректная кодировка токена")


def _json(data: dict) -> bytes:
    return json.dumps(data, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode()


def _sign(signing_input: str, secret: str) -> str:
    return _b64e(hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest())


def encode(payload: dict, secret: str) -> str:
    signing_input = f"{_b64e(_json({'alg': 'HS256', 'typ': 'JWT'}))}.{_b64e(_json(payload))}"
    return f"{signing_input}.{_sign(signing_input, secret)}"


def decode(token: str, secret: str, issuer: Optional[str] = None, now: Optional[float] = None) -> dict:
    parts = (token or "").split(".")
    if len(parts) != 3 or not all(parts):
        raise InvalidTokenError("Токен должен состоять из трёх частей")
    try:
        header = json.loads(_b64d(parts[0]))
        payload = json.loads(_b64d(parts[1]))
    except ValueError:
        raise InvalidTokenError("Некорректное содержимое токена")
    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise InvalidTokenError("Неподдерживаемый алгоритм подписи")
    if not hmac.compare_digest(_sign(f"{parts[0]}.{parts[1]}", secret), parts[2]):
        raise InvalidTokenError("Подпись токена неверна")
    if not isinstance(payload, dict) or "exp" not in payload:
        raise InvalidTokenError("В токене отсутствует срок действия")
    if payload["exp"] <= (now if now is not None else time.time()):
        raise ExpiredTokenError("Срок действия токена истёк")
    if issuer is not None and payload.get("iss") != issuer:
        raise InvalidTokenError("Токен выдан другим издателем")
    return payload
