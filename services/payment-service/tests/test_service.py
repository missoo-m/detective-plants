from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients import MockChatClient, MockRequestClient
from app.errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from app.models import Base
from app.seed import seed, sid
from app.service import PaymentService

U1, U2, U3, U4 = (str(sid(f"user-{i}")) for i in (1, 2, 3, 4))
R1, R2, R3 = (str(sid(f"req-{i}")) for i in (1, 2, 3))


@pytest.fixture
def stubs():
    return MockRequestClient(), MockChatClient()


@pytest.fixture
def service(stubs):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    assert seed(factory) is True
    assert seed(factory) is False
    return PaymentService(factory, requests=stubs[0], chat=stubs[1])


def test_filters_and_sorting(service):
    assert len(service.list_transactions()) == 3
    assert [t.status for t in service.list_transactions(status="SUCCESS")] == ["SUCCESS", "SUCCESS"]
    assert len(service.list_transactions(request_id=R2)) == 1
    assert len(service.list_transactions(user_id=U4)) == 2
    assert len(service.list_transactions(min_amount=30)) == 0 and len(service.list_transactions(max_amount=25)) == 3
    assert len(service.list_transactions(created_from=datetime(2026, 1, 10))) == 2
    newest = service.list_transactions(descending=True)
    assert newest[0].created_at > newest[-1].created_at
    assert len(service.list_transactions(sort_by="amount", limit=2)) == 2
    with pytest.raises(InvalidValueError):
        service.list_transactions(status="BAD")
    with pytest.raises(InvalidValueError):
        service.list_transactions(sort_by="user_id")
    with pytest.raises(InvalidValueError):
        service.list_transactions(min_amount=50, max_amount=10)


def test_transactions_summary(service):
    s = service.transactions_summary()
    assert s.count == 3 and s.total_amount == 75.0
    assert s.by_status == {"SUCCESS": 50.0, "FAILED": 25.0} and s.by_type == {"PAYMENT": 75.0}
    only_ok = service.transactions_summary(status="SUCCESS")
    assert only_ok.count == 2 and only_ok.total_amount == 50.0


def test_expert_balance(service):
    b = service.expert_balance(U2)                      
    assert (b.earned, b.commission, b.withdrawn, b.pending, b.available) == (50.0, 5.0, 0.0, 30.0, 15.0)
    assert service.expert_balance(U4).available == 0.0


def test_get_and_withdrawal_list(service):
    tx = service.list_transactions(request_id=R2)[0]
    assert service.get_transaction(tx.id).amount == 25.0
    assert len(service.list_withdrawals(expert_id=U2)) == 1 and service.list_withdrawals(status="APPROVED") == []
    with pytest.raises(NotFoundError):
        service.get_transaction(str(sid("tx-999")))


def test_create_payment_flow(service, stubs):
    tx = service.create_payment(R3, U4, "key-r3-0001")                
    assert tx.amount == 25.0 and tx.status == "SUCCESS" and tx.operation_type == "PAYMENT"
    assert stubs[0].started == [R3] and stubs[1].opened == [(R3, U4, U2)]
    assert service.expert_balance(U2).earned == 75.0


def test_create_payment_is_idempotent(service, stubs):
    first = service.create_payment(R3, U4, "key-r3-0001")
    again = service.create_payment(R3, U4, "key-r3-0001")
    assert again.id == first.id and stubs[0].started == [R3]             
    with pytest.raises(BusinessRuleError):
        service.create_payment(R2, U1, "key-r3-0001")                      


def test_create_payment_rules(service):
    with pytest.raises(BusinessRuleError):
        service.create_payment(R1, U1, "key-r1-0001")                     
    with pytest.raises(BusinessRuleError):
        service.create_payment(R2, U1, "key-r2-0001")                      
    with pytest.raises(PermissionDeniedError):
        service.create_payment(R3, U1, "key-r3-0002")                      
    with pytest.raises(PermissionDeniedError):
        service.create_payment(R3, U2, "key-r3-0003")                     
    with pytest.raises(InvalidValueError):
        service.create_payment(R3, U4, "short")


def test_withdrawal_rules(service):
    with pytest.raises(InvalidValueError):
        service.request_withdrawal(U2, 5)                                 
    with pytest.raises(BusinessRuleError):
        service.request_withdrawal(U2, 16)                            
    with pytest.raises(PermissionDeniedError):
        service.request_withdrawal(U1, 15)                              
    wd = service.request_withdrawal(U2, 15)
    assert wd.status == "PENDING" and service.expert_balance(U2).available == 0.0
    with pytest.raises(BusinessRuleError):
        service.request_withdrawal(U2, 10)                                 


def test_approve_withdrawal(service):
    wd = service.list_withdrawals(expert_id=U2)[0]
    with pytest.raises(PermissionDeniedError):
        service.approve_withdrawal(wd.id, U2)                              
    done = service.approve_withdrawal(wd.id, U3)
    assert done.status == "APPROVED" and done.processed_at is not None
    b = service.expert_balance(U2)
    assert b.withdrawn == 30.0 and b.pending == 0.0 and b.available == 15.0
    with pytest.raises(BusinessRuleError):
        service.approve_withdrawal(wd.id, U3)                             
    with pytest.raises(NotFoundError):
        service.approve_withdrawal(str(sid("wd-999")), U3)
