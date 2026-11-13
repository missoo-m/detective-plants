import dataclasses
import logging
import random
import threading
import time
from typing import Any, Callable, Optional

import grpc

from . import config
from .errors import (AuthenticationError, BusinessRuleError, DomainError, NotFoundError, PermissionDeniedError,
                     ServiceUnavailableError, ValidationError)
from .logging_setup import CORRELATION_HEADER, correlation_id, remaining_budget

log = logging.getLogger("rpc")

MAX_MESSAGE_BYTES = 8 * 1024 * 1024
CHANNEL_OPTIONS = [("grpc.max_send_message_length", MAX_MESSAGE_BYTES),
                   ("grpc.max_receive_message_length", MAX_MESSAGE_BYTES)]
API_KEY_HEADER = "x-internal-key"

CLIENT_ERRORS = {grpc.StatusCode.NOT_FOUND: NotFoundError, grpc.StatusCode.INVALID_ARGUMENT: ValidationError,
                 grpc.StatusCode.PERMISSION_DENIED: PermissionDeniedError,
                 grpc.StatusCode.FAILED_PRECONDITION: BusinessRuleError,
                 grpc.StatusCode.UNAUTHENTICATED: AuthenticationError,
                 grpc.StatusCode.UNAVAILABLE: ServiceUnavailableError,
                 grpc.StatusCode.DEADLINE_EXCEEDED: ServiceUnavailableError,
                 grpc.StatusCode.RESOURCE_EXHAUSTED: ServiceUnavailableError}
RETRYABLE = {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.RESOURCE_EXHAUSTED}
BUSINESS_CODES = {code.name for code in (grpc.StatusCode.NOT_FOUND, grpc.StatusCode.INVALID_ARGUMENT,
                                         grpc.StatusCode.PERMISSION_DENIED, grpc.StatusCode.FAILED_PRECONDITION,
                                         grpc.StatusCode.UNAUTHENTICATED)}


def _is_repeated(field) -> bool:
    flag = getattr(field, "is_repeated", None)
    return bool(flag) if flag is not None else field.label == field.LABEL_REPEATED


def _is_message(field) -> bool:
    return field.type == field.TYPE_MESSAGE


def _is_map(field) -> bool:
    return _is_message(field) and field.message_type.GetOptions().map_entry


def _has_value(msg, field) -> bool:
    try:
        return msg.HasField(field.name)
    except ValueError:
        return True


def message_to_dict(msg) -> dict:
    result: dict = {}
    for field in msg.DESCRIPTOR.fields:
        value = getattr(msg, field.name)
        if _is_map(field):
            value_field = field.message_type.fields_by_name["value"]
            result[field.name] = {k: message_to_dict(v) if _is_message(value_field) else v for k, v in value.items()}
        elif _is_repeated(field):
            result[field.name] = [message_to_dict(v) if _is_message(field) else v for v in value]
        elif _is_message(field):
            result[field.name] = message_to_dict(value) if msg.HasField(field.name) else None
        else:
            result[field.name] = value if _has_value(msg, field) else None
    return result


def _fill(msg, data: dict) -> None:
    fields = msg.DESCRIPTOR.fields_by_name
    for name, value in data.items():
        if value is None:
            continue
        field = fields.get(name)
        if field is None:
            raise ValueError(f"Поле «{name}» отсутствует в сообщении {msg.DESCRIPTOR.full_name}")
        target = getattr(msg, name)
        if _is_map(field):
            value_field = field.message_type.fields_by_name["value"]
            for key, item in value.items():
                if _is_message(value_field):
                    _fill(target[key], item)
                else:
                    target[key] = item
        elif _is_repeated(field):
            for item in value:
                if _is_message(field):
                    _fill(target.add(), item)
                else:
                    target.append(item)
        elif _is_message(field):
            _fill(target, value)
        else:
            setattr(msg, name, value)


def to_message(message_cls, data: Any):
    if dataclasses.is_dataclass(data) and not isinstance(data, type):
        data = dataclasses.asdict(data)
    msg = message_cls()
    _fill(msg, data or {})
    return msg


class CircuitBreaker:

    def __init__(self, threshold: int = 5, reset_seconds: float = 10.0, clock: Callable[[], float] = time.monotonic):
        self._threshold, self._reset, self._clock = threshold, reset_seconds, clock
        self._failures, self._opened_at = 0, None
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if self._clock() - self._opened_at >= self._reset:
                self._opened_at = None
                self._failures = self._threshold - 1
                return True
            return False

    def success(self) -> None:
        with self._lock:
            self._failures, self._opened_at = 0, None

    def failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self._threshold:
                self._opened_at = self._clock()


def to_service_error(error: "grpc.RpcError") -> DomainError:
    code = error.code() if hasattr(error, "code") else grpc.StatusCode.UNKNOWN
    details = error.details() if hasattr(error, "details") else str(error)
    kind = CLIENT_ERRORS.get(code, DomainError)
    if kind is ServiceUnavailableError:
        return ServiceUnavailableError(f"Сервис недоступен или не ответил вовремя ({code.name}): {details}")
    return kind(details or code.name)


class RetryPolicy:

    def __init__(self, max_retries: Optional[int] = None, base_delay: Optional[float] = None,
                 max_delay: Optional[float] = None, rng: Callable[[float, float], float] = random.uniform):
        self.max_retries = config.GRPC_RETRIES if max_retries is None else max_retries
        self.base_delay = config.GRPC_BACKOFF_BASE if base_delay is None else base_delay
        self.max_delay = config.GRPC_BACKOFF_MAX if max_delay is None else max_delay
        self._rng = rng

    def delay(self, attempt: int) -> float:
        return min(self.max_delay, self.base_delay * 2 ** (attempt - 1)) * self._rng(0.5, 1.0)


def rpc_name(method) -> str:
    raw = getattr(method, "_method", None)
    return raw.decode() if isinstance(raw, bytes) else str(raw or getattr(method, "__name__", "?"))


class ServiceChannel:

    def __init__(self, target: str, name: str, timeout: Optional[float] = None, api_key: Optional[str] = None,
                 retries: Optional[int] = None, breaker: Optional[CircuitBreaker] = None,
                 sleep: Callable[[float], None] = time.sleep, channel=None, policy: Optional[RetryPolicy] = None):
        self.name, self.target = name, target
        self._timeout = timeout or config.GRPC_TIMEOUT_SECONDS
        self._key = api_key if api_key is not None else config.INTERNAL_API_KEY
        self._policy = policy or RetryPolicy(max_retries=retries)
        self._sleep = sleep
        self._breaker = breaker or CircuitBreaker()
        self._channel = channel or grpc.insecure_channel(target, options=CHANNEL_OPTIONS)

    def stub(self, stub_cls):
        return stub_cls(self._channel)

    def _metadata(self) -> tuple:
        return ((API_KEY_HEADER, self._key), (CORRELATION_HEADER, correlation_id.get()))

    def _attempt_timeout(self) -> float:
        left = remaining_budget()
        if left is None:
            return self._timeout
        if left <= 0.05:
            raise ServiceUnavailableError("Время выполнения операции исчерпано, вызов не выполнялся")
        return min(self._timeout, left - 0.02)

    def call(self, method: Callable, request, idempotent: bool = False):
        label = f"{self.name}.{rpc_name(method).rsplit('/', 1)[-1]}"
        if not self._breaker.allow():
            log.warning("→ %s отклонён предохранителем (сервис недоступен)", label)
            raise ServiceUnavailableError(f"Сервис {self.name} временно недоступен (повторите попытку позже)")
        attempts = 1 + (self._policy.max_retries if idempotent else 0)
        started = time.monotonic()
        for attempt in range(1, attempts + 1):
            try:
                response = method(request, timeout=self._attempt_timeout(), metadata=self._metadata())
                self._breaker.success()
                log.info("gRPC → %s OK %.0f мс%s", label, (time.monotonic() - started) * 1000,
                         f" (попытка {attempt})" if attempt > 1 else "")
                return response
            except grpc.RpcError as error:
                code = error.code() if hasattr(error, "code") else None
                if code in RETRYABLE:
                    self._breaker.failure()
                    if attempt < attempts:
                        pause = self._policy.delay(attempt)
                        left = remaining_budget()
                        if left is None or left > pause + 0.1:
                            log.warning("gRPC → %s: %s, повтор %s/%s через %.2f с", label, code.name, attempt,
                                        attempts - 1, pause)
                            self._sleep(pause)
                            continue
                        log.warning("gRPC → %s: %s, повтор невозможен — исчерпан бюджет времени операции", label,
                                    code.name)
                else:
                    self._breaker.success()
                failure = to_service_error(error)
                log.log(logging.ERROR if isinstance(failure, ServiceUnavailableError) else logging.WARNING,
                        "gRPC → %s %s за %.0f мс: %s", label, code.name if code else "ERROR",
                        (time.monotonic() - started) * 1000, failure)
                raise failure from None
        raise ServiceUnavailableError(f"Сервис {self.name} не ответил")

    def close(self) -> None:
        self._channel.close()


def build(message_cls, **fields):
    return to_message(message_cls, fields)


def probe_services(addresses: dict, timeout: float = 1.0) -> dict:
    result = {}
    for name, address in addresses.items():
        channel = grpc.insecure_channel(address)
        try:
            grpc.channel_ready_future(channel).result(timeout=timeout)
            result[name] = "up"
        except grpc.FutureTimeoutError:
            result[name] = "down"
        finally:
            channel.close()
    return result
