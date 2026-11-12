import pytest

grpc = pytest.importorskip("grpc")

from app.errors import (AuthenticationError, BusinessRuleError, NotFoundError, PermissionDeniedError,  # noqa: E402
                        ServiceUnavailableError, ValidationError)
from app.grpc_support import CircuitBreaker, ServiceChannel  # noqa: E402


class RpcFailure(grpc.RpcError):
    def __init__(self, code, details="ошибка"):
        self._code, self._details = code, details

    def code(self):
        return self._code

    def details(self):
        return self._details


def channel(**kwargs):
    return ServiceChannel("localhost:1", "test-service", sleep=lambda s: None, channel=object(), **kwargs)


@pytest.mark.parametrize("code, error", [
    (grpc.StatusCode.NOT_FOUND, NotFoundError), (grpc.StatusCode.INVALID_ARGUMENT, ValidationError),
    (grpc.StatusCode.PERMISSION_DENIED, PermissionDeniedError), (grpc.StatusCode.FAILED_PRECONDITION, BusinessRuleError),
    (grpc.StatusCode.UNAUTHENTICATED, AuthenticationError), (grpc.StatusCode.UNAVAILABLE, ServiceUnavailableError),
    (grpc.StatusCode.DEADLINE_EXCEEDED, ServiceUnavailableError)])
def test_status_codes_map_to_domain_errors(code, error):
    def failing(request, timeout, metadata):
        raise RpcFailure(code, "текст ошибки сервиса")
    with pytest.raises(error) as info:
        channel(retries=0).call(failing, object())
    assert "текст ошибки" in str(info.value) or code in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED)


def test_read_calls_are_retried_but_commands_are_not():
    calls = []

    def flaky(request, timeout, metadata):
        calls.append(1)
        if len(calls) < 3:
            raise RpcFailure(grpc.StatusCode.UNAVAILABLE)
        return "ответ"
    assert channel(retries=2).call(flaky, object(), idempotent=True) == "ответ" and len(calls) == 3
    calls.clear()
    with pytest.raises(ServiceUnavailableError):                     
        channel(retries=2).call(flaky, object(), idempotent=False)
    assert len(calls) == 1


def test_deadline_and_key_are_sent():
    seen = {}

    def ok(request, timeout, metadata):
        seen.update(timeout=timeout, metadata=metadata)
        return "ok"
    ServiceChannel("x", "svc", timeout=2.5, api_key="secret", channel=object()).call(ok, object())
    assert seen["timeout"] == 2.5 and ("x-internal-key", "secret") in seen["metadata"]


def test_circuit_breaker_opens_and_recovers():
    now = [0.0]
    ch = ServiceChannel("x", "svc", retries=0, sleep=lambda s: None, channel=object(),
                        breaker=CircuitBreaker(threshold=2, reset_seconds=10, clock=lambda: now[0]))

    def down(request, timeout, metadata):
        raise RpcFailure(grpc.StatusCode.UNAVAILABLE)
    for _ in range(2):
        with pytest.raises(ServiceUnavailableError):
            ch.call(down, object())
    with pytest.raises(ServiceUnavailableError) as info:             
        ch.call(lambda *a, **k: "ok", object())
    assert "временно недоступен" in str(info.value)
    now[0] = 11.0
    assert ch.call(lambda *a, **k: "ok", object()) == "ok"         
