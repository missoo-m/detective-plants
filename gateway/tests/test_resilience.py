import logging

import pytest

grpc = pytest.importorskip("grpc")

from app import cache, logging_setup
from app.errors import ServiceUnavailableError
from app.grpc_support import CircuitBreaker, RetryPolicy, ServiceChannel


class Failure(grpc.RpcError):
    def __init__(self, code):
        self._code = code

    def code(self):
        return self._code

    def details(self):
        return "сбой"


def test_backoff_grows_exponentially_with_cap_and_jitter():
    policy = RetryPolicy(max_retries=5, base_delay=0.2, max_delay=1.0, rng=lambda low, high: 1.0)
    assert [policy.delay(n) for n in (1, 2, 3, 4, 5)] == [0.2, 0.4, 0.8, 1.0, 1.0]
    half = RetryPolicy(base_delay=1.0, max_delay=8.0, rng=lambda low, high: low)
    assert half.delay(1) == 0.5


def test_retries_sleep_with_backoff_and_send_correlation_id():
    sleeps, seen = [], []

    def flaky(request, timeout, metadata):
        seen.append(dict(metadata))
        if len(seen) < 4:
            raise Failure(grpc.StatusCode.UNAVAILABLE)
        return "ответ"
    channel = ServiceChannel("x", "svc", channel=object(), sleep=sleeps.append,
                             policy=RetryPolicy(3, 0.2, 2.0, rng=lambda a, b: 1.0), breaker=CircuitBreaker(threshold=99))
    token = logging_setup.correlation_id.set("corr-42")
    try:
        assert channel.call(flaky, object(), idempotent=True) == "ответ"
    finally:
        logging_setup.correlation_id.reset(token)
    assert sleeps == [0.2, 0.4, 0.8]
    assert all(call["x-correlation-id"] == "corr-42" for call in seen)


def test_operation_budget_limits_attempt_timeout_and_stops_retries():
    import time
    seen, sleeps = [], []

    def down(request, timeout, metadata):
        seen.append(timeout)
        raise Failure(grpc.StatusCode.UNAVAILABLE)
    channel = ServiceChannel("x", "svc", timeout=5.0, channel=object(), sleep=sleeps.append,
                             policy=RetryPolicy(3, 0.6, 2.0, rng=lambda a, b: 1.0), breaker=CircuitBreaker(threshold=99))
    token = logging_setup.deadline_at.set(time.monotonic() + 0.5)
    try:
        with pytest.raises(ServiceUnavailableError):
            channel.call(down, object(), idempotent=True)
    finally:
        logging_setup.deadline_at.reset(token)
    assert seen[0] <= 0.5 and len(seen) == 1 and sleeps == []


def test_exhausted_budget_means_no_call_at_all():
    import time
    calls = []
    channel = ServiceChannel("x", "svc", channel=object(), sleep=lambda s: None)
    token = logging_setup.deadline_at.set(time.monotonic() - 1)
    try:
        with pytest.raises(ServiceUnavailableError, match="исчерпано"):
            channel.call(lambda *a, **k: calls.append(1), object())
    finally:
        logging_setup.deadline_at.reset(token)
    assert calls == []


def test_every_log_line_carries_correlation_id(caplog):
    logging_setup.configure_logging("gateway")
    handler = logging.getLogger().handlers[0]
    records = []
    handler.emit = records.append
    token = logging_setup.correlation_id.set("scenario-1")
    try:
        logging.getLogger("rpc").warning("проверка")
    finally:
        logging_setup.correlation_id.reset(token)
    assert records[0].correlation_id == "scenario-1" and records[0].service == "gateway"


def test_cache_aside_hit_invalidate_and_ttl():
    now = [0.0]
    memory = cache.MemoryCache(clock=lambda: now[0])
    loads = []
    load = lambda: loads.append(1) or {"name": "Мучнистая роса"}
    assert memory.get_or_load("disease:1", 10, load) == memory.get_or_load("disease:1", 10, load)
    assert len(loads) == 1 and memory.stats()["hits"] == 1
    now[0] = 11
    memory.get_or_load("disease:1", 10, load)
    assert len(loads) == 2
    memory.invalidate("disease:1")
    memory.get_or_load("disease:1", 10, load)
    assert len(loads) == 3


def test_redis_outage_falls_back_to_source_and_pauses_redis():
    class Down:
        calls = 0

        def get(self, key):
            Down.calls += 1
            raise ConnectionError("Redis недоступен")

        set = delete = get

    now = [0.0]
    redis_cache = cache.RedisCache(client=Down(), namespace="t:", pause_seconds=5, clock=lambda: now[0])
    assert redis_cache.get_or_load("k", 60, lambda: {"v": 1}) == {"v": 1}
    assert redis_cache.get_or_load("k", 60, lambda: {"v": 2}) == {"v": 2}
    assert Down.calls == 1 and redis_cache.errors >= 2
    now[0] = 6.0
    redis_cache.get_or_load("k", 60, lambda: {"v": 3})
    assert Down.calls == 2
