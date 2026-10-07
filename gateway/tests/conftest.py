import pytest

from app import clients


@pytest.fixture(autouse=True)
def fresh_clients():
    clients.reset_clients()
