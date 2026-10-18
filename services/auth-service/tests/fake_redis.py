class FakeRedis:
    def __init__(self, clock):
        self._clock = clock
        self._data = {}          # ключ -> (значение, момент истечения)
        self._sets = {}

    def _alive(self, key):
        item = self._data.get(key)
        if item is None:
            return False
        if item[1] is not None and item[1] <= self._clock():
            del self._data[key]
            return False
        return True

    def setex(self, key, ttl, value):
        self._data[key] = (value, self._clock() + ttl)
        return True

    def get(self, key):
        return self._data[key][0] if self._alive(key) else None

    def expire(self, key, ttl):
        if not self._alive(key):
            return False
        self._data[key] = (self._data[key][0], self._clock() + ttl)
        return True

    def ttl(self, key):
        return int(self._data[key][1] - self._clock()) if self._alive(key) else -2

    def delete(self, *keys):
        removed = 0
        for key in keys:
            alive = self._alive(key)
            self._data.pop(key, None)
            removed += 1 if alive else 0
            self._sets.pop(key, None)
        return removed

    def sadd(self, key, *values):
        self._sets.setdefault(key, set()).update(values)
        return len(values)

    def srem(self, key, *values):
        self._sets.get(key, set()).difference_update(values)

    def smembers(self, key):
        return set(self._sets.get(key, set()))
