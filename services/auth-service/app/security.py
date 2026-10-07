import base64
import hashlib
import hmac
import os
import time
from typing import Optional

from . import config


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 50_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        expected = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 50_000)
    except ValueError:
        return False
    return hmac.compare_digest(expected.hex(), digest_hex)


def _sign(payload: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_token(user_id: str, now: Optional[float] = None) -> str:
    expires = int((now if now is not None else time.time()) + config.TOKEN_TTL_SECONDS)
    payload = f"{user_id}.{expires}"
    return base64.urlsafe_b64encode(f"{payload}.{_sign(payload)}".encode()).decode()


def verify_token(token: str, now: Optional[float] = None) -> Optional[str]:
    try:
        user_id, expires, signature = base64.urlsafe_b64decode(token.encode()).decode().rsplit(".", 2)
        if not hmac.compare_digest(signature, _sign(f"{user_id}.{expires}")):
            return None
        if int(expires) < (now if now is not None else time.time()):
            return None
        return user_id
    except Exception:
        return None
