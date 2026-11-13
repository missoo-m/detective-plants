import pytest

pytest.importorskip("grpc")
pb = pytest.importorskip("app.proto.analytics_pb2")
pb_grpc = pytest.importorskip("app.proto.analytics_pb2_grpc")

from app.seed import sid
from tests.helpers import make_factory, serve
from app.service import AnalyticsService

@pytest.fixture
def api():
    service = AnalyticsService(make_factory())
    with serve(service, "AnalyticsServiceStub", pb_grpc) as (stub, channel):
        yield stub, channel, service


U2 = str(sid("user-2"))


def test_read_models_over_grpc(api):
    stub, channel, _ = api
    stats = channel.call(stub.GetExpertStats, pb.GetExpertStatsRequest(expert_id=U2), idempotent=True)
    assert stats.expert_id == U2 and stats.total_requests >= stats.completed_requests
    top = channel.call(stub.GetTopExperts, pb.TopExpertsRequest(limit=1))
    assert len(top.experts) == 1
    summary = channel.call(stub.GetPlatformSummary, pb.EmptyRequest())
    assert summary.experts >= 2 and summary.completion_rate >= 0


def test_event_counters_empty_until_events(api):
    stub, channel, _ = api
    assert list(channel.call(stub.GetEventCounters, pb.EventCountersRequest()).counters) == []
