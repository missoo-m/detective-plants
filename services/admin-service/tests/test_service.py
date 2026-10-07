from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients import MockAuthClient
from app.errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from app.models import Base
from app.seed import seed, sid
from app.service import AdminService

U1, U2, U3, U4, U5 = (str(sid(f"user-{i}")) for i in range(1, 6))
APP1, APP2 = str(sid("app-1")), str(sid("app-2"))


@pytest.fixture
def auth():
    return MockAuthClient()


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
    with pytest.raises(BusinessRuleError):
        service.verify_expert(APP1, U3, approve=True)                      


def test_verify_expert_reject_and_resubmit(service, auth):
    assert service.verify_expert(APP1, U3, approve=False).status == "REJECTED"
    assert auth.users[U4][0] == "CLIENT"
    again = service.submit_application(U4, "https://minio/docs/user-4-v2.pdf")   # повторная подача после отказа
    assert again.status == "PENDING" and again.id == APP1


def test_verify_requires_admin(service):
    with pytest.raises(PermissionDeniedError):
        service.verify_expert(APP1, U1, approve=True)
    with pytest.raises(NotFoundError):
        service.verify_expert(str(sid("app-999")), U3, approve=True)


def test_block_user(service, auth):
    assert service.block_user(U3, U1)["status"] == "BLOCKED" and auth.users[U1][1] == "BLOCKED"
    with pytest.raises(BusinessRuleError):
        service.block_user(U3, U1)                                          
    with pytest.raises(BusinessRuleError):
        service.block_user(U3, U3)                                          # админа блокировать нельзя
    with pytest.raises(PermissionDeniedError):
        service.block_user(U2, U4)
