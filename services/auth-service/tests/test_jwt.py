import base64
import json

import pytest

from app import jwt_utils
from app.jwt_utils import ExpiredTokenError, InvalidTokenError

SECRET = "test-secret"


def make(payload=None, now=1000, ttl=60):
    return jwt_utils.encode(payload or {"sub": "u-1", "iss": "auth", "exp": now + ttl}, SECRET)


def test_roundtrip():
    claims = jwt_utils.decode(make(), SECRET, "auth", now=1000)
    assert claims["sub"] == "u-1" and make().count(".") == 2


def test_expired_token():
    with pytest.raises(ExpiredTokenError):
        jwt_utils.decode(make(), SECRET, "auth", now=1061)


def test_wrong_secret_and_tampering():
    token = make()
    with pytest.raises(InvalidTokenError):
        jwt_utils.decode(token, "other-secret", "auth", now=1000)
    header, payload, signature = token.split(".")
    forged = base64.urlsafe_b64encode(json.dumps({"sub": "admin", "iss": "auth", "exp": 9999}).encode()).rstrip(b"=").decode()
    with pytest.raises(InvalidTokenError):
        jwt_utils.decode(f"{header}.{forged}.{signature}", SECRET, "auth", now=1000)


def test_alg_none_is_rejected():
    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "u-1", "exp": 9999}).encode()).rstrip(b"=").decode()
    with pytest.raises(InvalidTokenError):
        jwt_utils.decode(f"{header}.{payload}.x", SECRET, now=1000)


def test_malformed_and_issuer():
    for bad in ("", "abc", "a.b", "a.b.c.d", "...", "###.###.###"):
        with pytest.raises(InvalidTokenError):
            jwt_utils.decode(bad, SECRET)
    with pytest.raises(InvalidTokenError):
        jwt_utils.decode(make(), SECRET, "another-issuer", now=1000)
    with pytest.raises(InvalidTokenError):
        jwt_utils.decode(jwt_utils.encode({"sub": "u-1"}, SECRET), SECRET, now=1000)      # нет exp
