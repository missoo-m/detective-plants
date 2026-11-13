import pytest

from app import cache


@pytest.fixture(autouse=True)
def isolated_cache():
    cache.set_cache(cache.MemoryCache())
    yield
    cache.set_cache(None)
