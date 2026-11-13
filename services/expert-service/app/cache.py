import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from . import config

log = logging.getLogger("cache")
_MISS = object()


class CachePaused(ConnectionError):
    pass


class Cache(ABC):
    def __init__(self):
        self.hits = self.misses = self.errors = 0
        self._lock = threading.Lock()

    @abstractmethod
    def _get(self, key: str) -> Any: ...

    @abstractmethod
    def _set(self, key: str, value: Any, ttl: int) -> None: ...

    @abstractmethod
    def _delete(self, keys: list) -> None: ...

    @abstractmethod
    def _delete_prefix(self, prefix: str) -> None: ...

    def get_or_load(self, key: str, ttl: int, loader: Callable[[], Any]) -> Any:
        value = self._safe(self._get, key, default=_MISS)
        if value is not _MISS and value is not None:
            self._count("hits")
            log.debug("кеш: попадание %s", key)
            return value
        self._count("misses")
        value = loader()
        if value is not None:
            self._safe(self._set, key, value, ttl)
            log.debug("кеш: промах %s, значение сохранено на %s с", key, ttl)
        return value

    def invalidate(self, *keys: str) -> None:
        self._safe(self._delete, list(keys))
        log.debug("кеш: удалено %s", ", ".join(keys))

    def invalidate_prefix(self, prefix: str) -> None:
        self._safe(self._delete_prefix, prefix)
        log.debug("кеш: удалены ключи с префиксом %s", prefix)

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses, "errors": self.errors,
                "hit_rate": round(self.hits / total, 3) if total else 0.0}

    def _count(self, what: str) -> None:
        with self._lock:
            setattr(self, what, getattr(self, what) + 1)
            total = self.hits + self.misses
        if what != "errors" and total % 50 == 0:
            log.info("кеш: %s", self.stats())

    def _safe(self, operation, *args, default=None):
        try:
            return operation(*args)
        except Exception as error:
            self._count("errors")
            if isinstance(error, CachePaused):
                log.debug("кеш: %s", error)
            else:
                log.warning("кеш: операция не выполнена, используется источник данных: %s", error)
            return default


class NullCache(Cache):

    def _get(self, key): return None
    def _set(self, key, value, ttl): pass
    def _delete(self, keys): pass
    def _delete_prefix(self, prefix): pass


class MemoryCache(Cache):

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        super().__init__()
        self._data: dict = {}
        self._clock = clock

    def _get(self, key):
        item = self._data.get(key)
        if item is None or item[1] <= self._clock():
            self._data.pop(key, None)
            return None
        return json.loads(item[0])

    def _set(self, key, value, ttl): self._data[key] = (json.dumps(value, ensure_ascii=False), self._clock() + ttl)
    def _delete(self, keys): [self._data.pop(k, None) for k in keys]
    def _delete_prefix(self, prefix): [self._data.pop(k) for k in [k for k in self._data if k.startswith(prefix)]]


class RedisCache(Cache):
    def __init__(self, client=None, namespace: Optional[str] = None, pause_seconds: float = 5.0,
                 clock: Callable[[], float] = time.monotonic):
        super().__init__()
        if client is None:
            import redis
            client = redis.Redis.from_url(config.REDIS_CACHE_URL, decode_responses=True,
                                          socket_timeout=config.REDIS_TIMEOUT_SECONDS,
                                          socket_connect_timeout=config.REDIS_TIMEOUT_SECONDS)
        self._client, self._ns = client, namespace or f"pd:{config.SERVICE_NAME}:"
        self._pause, self._clock, self._down_until = pause_seconds, clock, 0.0

    def _guard(self, operation):
        if self._clock() < self._down_until:
            raise CachePaused("Redis временно отключён предохранителем")
        try:
            return operation()
        except Exception:
            self._down_until = self._clock() + self._pause
            raise

    def _get(self, key):
        raw = self._guard(lambda: self._client.get(self._ns + key))
        return None if raw is None else json.loads(raw)

    def _set(self, key, value, ttl):
        self._guard(lambda: self._client.set(self._ns + key, json.dumps(value, ensure_ascii=False), ex=ttl))

    def _delete(self, keys):
        if keys:
            self._guard(lambda: self._client.delete(*[self._ns + k for k in keys]))

    def _delete_prefix(self, prefix):
        def run():
            keys = list(self._client.scan_iter(match=self._ns + prefix + "*", count=200))
            if keys:
                self._client.delete(*keys)
        self._guard(run)


_instance: Optional[Cache] = None


def get_cache() -> Cache:
    global _instance
    if _instance is None:
        _instance = RedisCache() if config.CACHE_ENABLED else NullCache()
    return _instance


def set_cache(cache: Optional[Cache]) -> None:
    global _instance
    _instance = cache
