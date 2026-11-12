import pytest

from tests.fakes import install_fakes


@pytest.fixture(autouse=True)
def fresh_clients():
    install_fakes()
