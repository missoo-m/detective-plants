import dataclasses
import logging
import threading
import time
from typing import Any, Callable, Optional

import grpc

from . import config
from .errors import (AuthenticationError, BusinessRuleError, DomainError, NotFoundError, PermissionDeniedError,
                     ServiceUnavailableError, ValidationError)

log = logging.getLogger("grpc")

MAX_MESSAGE_BYTES = 8 * 1024 * 1024                  
CHANNEL_OPTIONS = [("grpc.max_send_message_length", MAX_MESSAGE_BYTES),
                   ("grpc.max_receive_message_length", MAX_MESSAGE_BYTES)]
API_KEY_HEADER = "x-internal-key"

CLIENT_ERRORS = {grpc.StatusCode.NOT_FOUND: NotFoundError, grpc.StatusCode.INVALID_ARGUMENT: ValidationError,
                 grpc.StatusCode.PERMISSION_DENIED: PermissionDeniedError,
                 grpc.StatusCode.FAILED_PRECONDITION: BusinessRuleError,
                 grpc.StatusCode.UNAUTHENTICATED: AuthenticationError,
                 grpc.StatusCode.UNAVAILABLE: ServiceUnavailableError,
                 grpc.StatusCode.DEADLINE_EXCEEDED: ServiceUnavailableError}
RETRYABLE = {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED}


# protobuf ↔ Python
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


# клиент
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


class ServiceChannel:

    def __init__(self, target: str, name: str, timeout: Optional[float] = None, api_key: Optional[str] = None,
                 retries: int = 2, breaker: Optional[CircuitBreaker] = None, sleep: Callable[[float], None] = time.sleep,
                 channel=None):
        self.name, self.target = name, target
        self._timeout = timeout or config.GRPC_TIMEOUT_SECONDS
        self._metadata = ((API_KEY_HEADER, api_key if api_key is not None else config.INTERNAL_API_KEY),)
        self._retries, self._sleep = retries, sleep
        self._breaker = breaker or CircuitBreaker()
        self._channel = channel or grpc.insecure_channel(target, options=CHANNEL_OPTIONS)

    def stub(self, stub_cls):
        return stub_cls(self._channel)

    def call(self, method: Callable, request, idempotent: bool = False):
        if not self._breaker.allow():
            raise ServiceUnavailableError(f"Сервис {self.name} временно недоступен (повторите попытку позже)")
        attempts = 1 + (self._retries if idempotent else 0)
        for attempt in range(1, attempts + 1):
            try:
                response = method(request, timeout=self._timeout, metadata=self._metadata)
                self._breaker.success()
                return response
            except grpc.RpcError as error:
                code = error.code() if hasattr(error, "code") else None
                if code in RETRYABLE:
                    self._breaker.failure()
                    if attempt < attempts:
                        log.warning("%s: %s, повтор %s/%s", self.name, code.name, attempt, attempts - 1)
                        self._sleep(0.2 * attempt)
                        continue
                else:
                    self._breaker.success()           
                raise to_service_error(error) from None
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
