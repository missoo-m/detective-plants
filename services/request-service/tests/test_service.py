from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients import MockExpertClient
from app.errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from app.models import Base
from app.seed import seed, sid
from app.service import RequestService

U1, U2, U4, U5 = (str(sid(f"user-{i}")) for i in (1, 2, 4, 5))
R1, R2, R3 = (str(sid(f"req-{i}")) for i in (1, 2, 3))


@pytest.fixture
def expert_stub():
    return MockExpertClient(responded={(R1, U2)})


@pytest.fixture
def service(expert_stub):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    assert seed(factory) is True
    assert seed(factory) is False
    return RequestService(factory, expert=expert_stub)


def test_get_request_and_details(service):
    req = service.get_request(R1)
    assert len(req.photos) == 2 and req.status == "CREATED"
    assert service.get_request_details(R1).photo_urls[0].endswith("photo1.jpg")
    with pytest.raises(NotFoundError):
        service.get_request(str(sid("req-999")))


def test_filters(service):
    assert len(service.list_requests()) == 5
    assert len(service.list_requests(client_id=U1)) == 3
    assert {r.status for r in service.list_requests(statuses=["DONE", "CANCELLED"])} == {"DONE", "CANCELLED"}
    assert [r.id for r in service.list_requests(search="налёт")] == [R2]
    assert len(service.list_requests(has_expert=True)) == 2 and len(service.list_requests(has_expert=False)) == 3
    period = service.list_requests(created_from=datetime(2026, 1, 15), created_to=datetime(2026, 1, 31))
    assert {r.id for r in period} == {R1, R2, R3}
    assert [r.id for r in service.list_available_requests(client_id=U1)] == [R1]


def test_sorting_and_paging(service):
    asc = service.list_requests()
    assert asc[0].id == str(sid("req-5")) and asc[-1].id == R3
    desc = service.list_requests(descending=True, limit=2)
    assert [r.id for r in desc] == [R3, R2]
    assert len(service.list_requests(limit=2, offset=4)) == 1
    by_status = service.list_requests(sort_by="status")
    assert by_status[0].status == "CANCELLED"
    with pytest.raises(InvalidValueError):
        service.list_requests(sort_by="symptoms")
    with pytest.raises(InvalidValueError):
        service.list_requests(statuses=["WRONG"])
    with pytest.raises(InvalidValueError):
        service.list_requests(created_from=datetime(2026, 2, 1), created_to=datetime(2026, 1, 1))


def test_requests_summary(service):
    s = service.requests_summary()
    assert s.total == 5 and s.by_status == {"CREATED": 2, "IN_PROGRESS": 1, "DONE": 1, "CANCELLED": 1}
    assert service.requests_summary(client_id=U4).by_status == {"CREATED": 1, "DONE": 1}


def test_create_request(service):
    req = service.create_request(U4, "Белый налёт на листьях огурцов", ["https://minio/a.jpg"])
    assert req.status == "CREATED" and req.ai_prediagnosis == "Мучнистая роса" and len(req.photos) == 1


def test_create_request_validation(service):
    with pytest.raises(InvalidValueError):
        service.create_request(U4, "коротко")
    with pytest.raises(InvalidValueError):
        service.create_request(U4, "Описание достаточной длины", ["https://x/%d.jpg" % i for i in range(6)])
    with pytest.raises(PermissionDeniedError):
        service.create_request(U2, "Эксперт не может создавать заявки")      
    with pytest.raises(PermissionDeniedError):
        service.create_request(U5, "Заблокированный пользователь")


def test_active_requests_limit(service):
    service.create_request(U1, "Третья активная заявка клиента")          
    with pytest.raises(BusinessRuleError):
        service.create_request(U1, "Четвёртая активная заявка клиента")


def test_select_expert(service, expert_stub):
    req = service.select_expert(R1, U1, U2)
    assert req.status == "PENDING" and req.expert_id == U2
    assert expert_stub.accepted == [(R1, U2)]


def test_select_expert_rules(service):
    with pytest.raises(PermissionDeniedError):
        service.select_expert(R1, U4, U2)                  
    with pytest.raises(BusinessRuleError):
        service.select_expert(R3, U4, U2)                 
    with pytest.raises(PermissionDeniedError):
        service.select_expert(R1, U1, U4)                  
    with pytest.raises(BusinessRuleError):
        service.select_expert(R2, U1, U2)                 


def test_cancel_request(service):
    assert service.cancel_request(R1, U1).status == "CANCELLED"
    with pytest.raises(BusinessRuleError):
        service.cancel_request(R1, U1)                     
    with pytest.raises(BusinessRuleError):
        service.cancel_request(R2, U1)                   
    with pytest.raises(PermissionDeniedError):
        service.cancel_request(R3, U1)                  


def test_status_flow(service):
    service.select_expert(R1, U1, U2)
    assert service.start_work(R1).status == "IN_PROGRESS"
    done = service.complete_request(R1)
    assert done.status == "DONE" and done.completed_at is not None
    with pytest.raises(BusinessRuleError):
        service.start_work(R3)                           


def test_add_photo(service):
    photo = service.add_photo(R1, U1, "leaf.JPG", b"123")
    assert photo.url.endswith("leaf.JPG") and len(service.get_request(R1).photos) == 3
    with pytest.raises(InvalidValueError):
        service.add_photo(R1, U1, "doc.pdf", b"123")
    with pytest.raises(PermissionDeniedError):
        service.add_photo(R1, U4, "leaf.jpg", b"123")
    with pytest.raises(BusinessRuleError):
        service.add_photo(R2, U1, "leaf.jpg", b"123")    
