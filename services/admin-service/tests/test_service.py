from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from app.models import Base
from app.seed import seed, sid
from app.service import AdminService
from tests.fakes import FakeAuthClient, outbox

U1, U2, U3, U4, U5 = (str(sid(f"user-{i}")) for i in range(1, 6))
APP1, APP2 = str(sid("app-1")), str(sid("app-2"))


@pytest.fixture
def auth():
    return FakeAuthClient()


@pytest.fixture
def service(auth):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    assert seed(factory) is True
    assert seed(factory) is False
    return AdminService(factory, auth=auth)


def test_filters_sort_summary(service):
    assert [a.status for a in service.list_applications()] == ["PENDING", "APPROVED"]
    assert [a.status for a in service.list_applications(descending=False)] == ["APPROVED", "PENDING"]
    assert len(service.list_applications(status="PENDING")) == 1
    assert len(service.list_applications(submitted_from=datetime(2026, 1, 10))) == 1
    s = service.applications_summary()
    assert s.total == 2 and s.by_status == {"PENDING": 1, "APPROVED": 1}
    with pytest.raises(InvalidValueError):
        service.list_applications(status="BAD")
    with pytest.raises(NotFoundError):
        service.get_application(str(sid("app-999")))


def test_submit_application(service):
    app = service.submit_application(U1, "https://minio/docs/user-1.pdf")
    assert app.status == "PENDING" and app.user_id == U1
    with pytest.raises(BusinessRuleError):
        service.submit_application(U1, "https://minio/docs/again.pdf")
    with pytest.raises(BusinessRuleError):
        service.submit_application(U2, "https://minio/docs/user-2.pdf")
    with pytest.raises(PermissionDeniedError):
        service.submit_application(U5, "https://minio/docs/user-5.pdf")
    with pytest.raises(InvalidValueError):
        service.submit_application(U4, "ftp://nope")


def test_verify_expert_approve(service, auth):
    result = service.verify_expert(APP1, U3, approve=True)
    assert result.status == "APPROVED" and result.verified_at is not None
    assert auth.users[U4][0] == "EXPERT"
    assert outbox(service._session_factory, "ExpertVerified")[0]["payload"]["user_id"] == U4
    with pytest.raises(BusinessRuleError):
        service.verify_expert(APP1, U3, approve=True)


def test_verify_expert_reject_and_resubmit(service, auth):
    assert service.verify_expert(APP1, U3, approve=False).status == "REJECTED"
    assert auth.users[U4][0] == "CLIENT" and outbox(service._session_factory, "ExpertVerified") == []
    again = service.submit_application(U4, "https://minio/docs/user-4-v2.pdf")
    assert again.status == "PENDING" and again.id == APP1


def test_verify_requires_admin(service):
    with pytest.raises(PermissionDeniedError):
        service.verify_expert(APP1, U1, approve=True)
    with pytest.raises(NotFoundError):
        service.verify_expert(str(sid("app-999")), U3, approve=True)


def test_block_user(service, auth):
    assert service.block_user(U3, U1)["status"] == "BLOCKED" and auth.users[U1][1] == "BLOCKED"
    assert outbox(service._session_factory, "UserBlocked")[0]["payload"]["user_id"] == U1
    with pytest.raises(BusinessRuleError):
        service.block_user(U3, U1)
    with pytest.raises(BusinessRuleError):
        service.block_user(U3, U3)
    with pytest.raises(PermissionDeniedError):
        service.block_user(U2, U4)


def test_role_passed_by_gateway_is_enforced(service):
    with pytest.raises(PermissionDeniedError):
        service.verify_expert(APP1, U3, approve=True, actor_role="CLIENT")
    with pytest.raises(PermissionDeniedError):
        service.block_user(U3, U1, actor_role="EXPERT")
    with pytest.raises(BusinessRuleError):
        service.submit_application(U2, "https://minio/docs/u2.pdf", actor_role="EXPERT")
    assert service.submit_application(U1, "https://minio/docs/u1.pdf", actor_role="CLIENT").status == "PENDING"
    assert service.verify_expert(APP1, U3, approve=True, actor_role="ADMIN").status == "APPROVED"


def test_auth_unavailable_keeps_decision_and_event(service, auth):
    from app.errors import ServiceUnavailableError

    def broken(user_id, role):
        raise ServiceUnavailableError("auth-service недоступен")
    auth.assign_role = broken
    assert service.verify_expert(APP1, U3, approve=True).status == "APPROVED"
    assert len(outbox(service._session_factory, "ExpertVerified")) == 1


def test_block_fails_when_auth_unavailable(service, auth):
    from app.errors import ServiceUnavailableError

    def broken(user_id, status):
        raise ServiceUnavailableError("auth-service недоступен")
    auth.set_status = broken
    with pytest.raises(ServiceUnavailableError):
        service.block_user(U3, U1)
    assert outbox(service._session_factory, "UserBlocked") == []
