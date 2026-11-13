import pytest

pytest.importorskip("grpc")
request_pb2 = pytest.importorskip("app.proto.request_pb2")

from app import cache
from app.clients import GrpcRequestClient


class FakeChannel:
    def __init__(self):
        self.calls = 0

    def stub(self, stub_cls):
        return type("Stub", (), {"GetDisease": "GetDisease", "GetRequestDetails": "GetRequestDetails"})()

    def call(self, method, request, idempotent=False):
        self.calls += 1
        return request_pb2.DiseaseResponse(id=request.disease_id, name="Мучнистая роса")


def test_disease_name_is_requested_over_grpc_only_once():
    channel = FakeChannel()
    client = GrpcRequestClient(channel=channel, cache=cache.MemoryCache())
    assert client.get_disease("d1") == {"id": "d1", "name": "Мучнистая роса"}
    assert client.get_disease("d1") == {"id": "d1", "name": "Мучнистая роса"}
    assert channel.calls == 1
    client.get_disease("d2")
    assert channel.calls == 2
