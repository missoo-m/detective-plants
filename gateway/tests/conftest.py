import pytest

from app import cache
from tests.fakes import install_fakes


@pytest.fixture(autouse=True)
def fresh_clients():
    install_fakes()
    cache.set_cache(cache.NullCache())
    yield
    cache.set_cache(None)
