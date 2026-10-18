from app.sessions import InMemorySessionStore, RedisSessionStore
from tests.fake_redis import FakeRedis


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def stores():
    result = []
    for kind in ("memory", "redis"):
        clock = Clock()
        store = InMemorySessionStore(clock) if kind == "memory" else RedisSessionStore(FakeRedis(clock), clock=clock)
        result.append((kind, store, clock))
    return result


def test_create_and_get():
    for kind, store, clock in stores():
        s = store.create("u-1", "CLIENT", 60)
        got = store.get(s.session_id)
        assert got.user_id == "u-1" and got.role == "CLIENT" and got.expires_at == 1060, kind
        assert store.get("unknown") is None


def test_session_expires_by_ttl():
    for kind, store, clock in stores():
        s = store.create("u-1", "CLIENT", 60)
        clock.now += 59
        assert store.get(s.session_id) is not None, kind
        clock.now += 2
        assert store.get(s.session_id) is None, kind
        assert store.list_for_user("u-1") == [], kind


def test_touch_extends_session():
    for kind, store, clock in stores():
        s = store.create("u-1", "CLIENT", 60)
        clock.now += 50
        assert store.touch(s.session_id, 60) is True
        clock.now += 50                                   # без продления сессия истекла бы
        assert store.get(s.session_id) is not None, kind
        clock.now += 20
        assert store.touch(s.session_id, 60) is False, kind


def test_delete_and_delete_all():
    for kind, store, clock in stores():
        a, b = store.create("u-1", "CLIENT", 60), store.create("u-1", "CLIENT", 60)
        other = store.create("u-2", "EXPERT", 60)
        assert store.delete(a.session_id) is True and store.delete(a.session_id) is False, kind
        assert [s.session_id for s in store.list_for_user("u-1")] == [b.session_id], kind
        assert store.delete_all_for_user("u-1") == 1, kind
        assert store.get(b.session_id) is None and store.get(other.session_id) is not None, kind


def test_list_for_user_sorted():
    for kind, store, clock in stores():
        first = store.create("u-1", "CLIENT", 600)
        clock.now += 5
        second = store.create("u-1", "CLIENT", 600)
        assert [s.session_id for s in store.list_for_user("u-1")] == [first.session_id, second.session_id], kind
