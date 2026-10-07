import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients import MockRecoveryClient
from app.errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from app.models import Base
from app.seed import seed, sid
from app.service import ExpertService

U1, U2, U4 = (str(sid(f"user-{i}")) for i in (1, 2, 4))
R1, R2, R3 = (str(sid(f"req-{i}")) for i in (1, 2, 3))
DIS1, DIS2 = str(sid("dis-1")), str(sid("dis-2"))


@pytest.fixture
def recovery():
    return MockRecoveryClient()


@pytest.fixture
def service(recovery):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    assert seed(factory) is True
    assert seed(factory) is False
    return ExpertService(factory, recovery=recovery)


def test_reads(service):
    assert len(service.list_responses(R1)) == 1 and service.list_responses(R3) == []
    assert service.has_responded(R1, U2) is True and service.has_responded(R3, U2) is False
    diag = service.get_diagnosis_by_request(R2)
    assert diag.duration_days == 14 and diag.checklist[0].step.startswith("Удалить")
    assert service.get_diagnosis(diag.id).id == diag.id
    with pytest.raises(NotFoundError):
        service.get_diagnosis_by_request(R1)


def test_filter_sort_summary(service):
    assert [r.status for r in service.list_responses_by_expert(U2, descending=True)] == ["ACCEPTED", "PENDING"]
    assert [r.status for r in service.list_responses_by_expert(U2, status="PENDING")] == ["PENDING"]
    s = service.responses_summary(U2)
    assert s.total == 2 and s.by_status == {"PENDING": 1, "ACCEPTED": 1}
    with pytest.raises(InvalidValueError):
        service.list_responses_by_expert(U2, status="BAD")


def test_respond_to_request(service):
    r = service.respond_to_request(R3, U2, "  Готов взяться  ")
    assert r.status == "PENDING" and r.comment == "Готов взяться"


def test_respond_rules(service):
    with pytest.raises(BusinessRuleError):
        service.respond_to_request(R1, U2)                    
    with pytest.raises(BusinessRuleError):
        service.respond_to_request(R2, U2)                      
    with pytest.raises(PermissionDeniedError):
        service.respond_to_request(R3, U4)                      
    with pytest.raises(InvalidValueError):
        service.respond_to_request(R3, U2, "x" * 501)
    with pytest.raises(NotFoundError):
        service.respond_to_request(str(sid("req-999")), U2)


def test_accept_response(service):
    service.respond_to_request(R3, U2)
    result = service.accept_response(R3, U2)
    assert [r.status for r in result] == ["ACCEPTED"]
    with pytest.raises(BusinessRuleError):
        service.accept_response(R3, U4)


def test_diagnosis_only_by_selected_expert(service):
    with pytest.raises(PermissionDeniedError):
        service.create_diagnosis(R1, U2, DIS1, "Мучнистая роса")       


def test_create_diagnosis_rules(service):
    with pytest.raises(BusinessRuleError):
        service.create_diagnosis(R2, U2, DIS1, "Мучнистая роса")       
    with pytest.raises(PermissionDeniedError):
        service.create_diagnosis(R2, U4, DIS1, "Мучнистая роса")      
    with pytest.raises(NotFoundError):
        service.create_diagnosis(R2, U2, str(sid("dis-999")), "Мучнистая роса")
    with pytest.raises(InvalidValueError):
        service.create_diagnosis(R2, U2, DIS1, "ok")
    with pytest.raises(InvalidValueError):
        service.create_diagnosis(R2, U2, DIS1, "Мучнистая роса", duration_days=100)


def test_create_diagnosis_success_and_tracker(recovery):
    from app.clients import MockRequestClient
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed(factory)
    requests = MockRequestClient()
    requests.requests[R3].update(expert_id=U2)                          
    requests.requests[R3]["status"] = "PENDING"                        
    service = ExpertService(factory, requests=requests, recovery=recovery)
    with pytest.raises(BusinessRuleError):
        service.create_diagnosis(R3, U2, DIS2, "Корневая гниль, нужна пересадка")
    requests.requests[R3]["status"] = "IN_PROGRESS"                     
    diag = service.create_diagnosis(R3, U2, DIS2, "Корневая гниль, нужна пересадка", duration_days=10,
                                    checklist=[{"step": "Пересадить растение", "frequency": "однократно"},
                                               {"step": "Наладить дренаж", "duration_days": 7}])
    assert diag.duration_days == 10 and [s.step for s in diag.checklist] == ["Пересадить растение", "Наладить дренаж"]
    assert recovery.created == [(R3, U4, U2, 10)]                           
    with pytest.raises(BusinessRuleError):
        service.create_diagnosis(R3, U2, DIS2, "Повторный диагноз")


def test_add_treatment_step(service):
    diag = service.get_diagnosis_by_request(R2)
    step = service.add_treatment_step(diag.id, U2, "Проветривать теплицу", "ежедневно", 14)
    assert step.step == "Проветривать теплицу"
    assert len(service.get_diagnosis(diag.id).checklist) == 3
    with pytest.raises(PermissionDeniedError):
        service.add_treatment_step(diag.id, U4, "Чужой шаг лечения")
    with pytest.raises(InvalidValueError):
        service.add_treatment_step(diag.id, U2, "x")
