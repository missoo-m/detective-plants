import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Callable, Optional


@dataclass
class Session:
    session_id: str
    user_id: str
    role: str
    created_at: float
    expires_at: float

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(raw: str) -> "Session":
        return Session(**json.loads(raw))


class SessionStore(ABC):
    @abstractmethod
    def create(self, user_id: str, role: str, ttl: int) -> Session: ...

    @abstractmethod
    def get(self, session_id: str) -> Optional[Session]: ...

    @abstractmethod
    def touch(self, session_id: str, ttl: int) -> bool:
        pass

    @abstractmethod
    def delete(self, session_id: str) -> bool: ...

    @abstractmethod
    def delete_all_for_user(self, user_id: str) -> int: ...

    @abstractmethod
    def list_for_user(self, user_id: str) -> list[Session]: ...


class InMemorySessionStore(SessionStore):
    def __init__(self, clock: Callable[[], float] = time.time):
        self._clock = clock
        self._items: dict[str, Session] = {}

    def _alive(self, session: Optional[Session]) -> bool:
        return session is not None and session.expires_at > self._clock()

    def create(self, user_id: str, role: str, ttl: int) -> Session:
        now = self._clock()
        session = Session(uuid.uuid4().hex, user_id, role, now, now + ttl)
        self._items[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        session = self._items.get(session_id)
        if not self._alive(session):
            self._items.pop(session_id, None)
            return None
        return session

    def touch(self, session_id: str, ttl: int) -> bool:
        session = self.get(session_id)
        if session is None:
            return False
        session.expires_at = self._clock() + ttl
        return True

    def delete(self, session_id: str) -> bool:
        return self._items.pop(session_id, None) is not None

    def delete_all_for_user(self, user_id: str) -> int:
        ids = [s.session_id for s in self.list_for_user(user_id)]
        for sid in ids:
            self._items.pop(sid, None)
        return len(ids)

    def list_for_user(self, user_id: str) -> list[Session]:
        return [s for s in list(self._items.values()) if s.user_id == user_id and self.get(s.session_id)]


class RedisSessionStore(SessionStore):

    def __init__(self, client, prefix: str = "pd", clock: Callable[[], float] = time.time):
        self._r, self._prefix, self._clock = client, prefix, clock

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}:session:{session_id}"

    def _user_key(self, user_id: str) -> str:
        return f"{self._prefix}:user_sessions:{user_id}"

    def create(self, user_id: str, role: str, ttl: int) -> Session:
        now = self._clock()
        session = Session(uuid.uuid4().hex, user_id, role, now, now + ttl)
        self._r.setex(self._key(session.session_id), ttl, session.to_json())
        self._r.sadd(self._user_key(user_id), session.session_id)
        return session

    def get(self, session_id: str) -> Optional[Session]:
        raw = self._r.get(self._key(session_id))     
        return Session.from_json(raw) if raw else None

    def touch(self, session_id: str, ttl: int) -> bool:
        session = self.get(session_id)
        if session is None:
            return False
        session.expires_at = self._clock() + ttl
        self._r.setex(self._key(session_id), ttl, session.to_json())
        return True

    def delete(self, session_id: str) -> bool:
        session = self.get(session_id)
        removed = bool(self._r.delete(self._key(session_id)))
        if session:
            self._r.srem(self._user_key(session.user_id), session_id)
        return removed

    def delete_all_for_user(self, user_id: str) -> int:
        removed = 0
        for session_id in self._r.smembers(self._user_key(user_id)):
            removed += int(self._r.delete(self._key(session_id)))
        self._r.delete(self._user_key(user_id))
        return removed

    def list_for_user(self, user_id: str) -> list[Session]:
        result = []
        for session_id in self._r.smembers(self._user_key(user_id)):
            session = self.get(session_id)
            if session is None:
                self._r.srem(self._user_key(user_id), session_id)     
            else:
                result.append(session)
        return sorted(result, key=lambda s: s.created_at)
