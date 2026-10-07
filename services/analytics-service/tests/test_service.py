import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.errors import InvalidValueError, NotFoundError
from app.models import Base
from app.seed import seed, sid
from app.service import AnalyticsService

U1, U2, U6 = str(sid("user-1")), str(sid("user-2")), str(sid("user-6"))


@pytest.fixture
def service():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    assert seed(factory) is True
    assert seed(factory) is False
    return AnalyticsService(factory)


def test_expert_stats(service):
    s = service.get_expert_stats(U2)
    assert s.total_requests == 2 and s.completed_requests == 1 and s.avg_rating == 4.8
    with pytest.raises(NotFoundError):
        service.get_expert_stats(U1)


def test_top_experts_sorting(service):
    assert [e.expert_id for e in service.top_experts()] == [U6, U2]                         
    assert [e.expert_id for e in service.top_experts(sort_by="avg_rating")] == [U2, U6]
    assert [e.expert_id for e in service.top_experts(descending=False, limit=1)] == [U2]
    with pytest.raises(InvalidValueError):
        service.top_experts(sort_by="expert_id")
    with pytest.raises(InvalidValueError):
        service.top_experts(limit=0)


def test_disease_stats(service):
    assert [d.count for d in service.list_disease_stats("2026-01")] == [3, 1]
    assert [d.count for d in service.list_disease_stats("2026-01", descending=False)] == [1, 3]
    assert len(service.list_disease_stats("2026-01", limit=1)) == 1
    assert service.list_disease_stats("1999-01") == []


def test_platform_summary(service):
    s = service.platform_summary()
    assert s.experts == 2 and s.total_requests == 12 and s.completed_requests == 9
    assert s.completion_rate == 75.0
    assert s.avg_rating == round((4.8 * 1 + 4.2 * 8) / 9, 2)
