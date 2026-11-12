import pytest

pytest.importorskip("grpc")
pb = pytest.importorskip("app.proto.payment_pb2")
pb_grpc = pytest.importorskip("app.proto.payment_pb2_grpc")

from app.errors import NotFoundError
from app.seed import sid
from tests.helpers import make_factory, serve
from app.service import PaymentService
from tests.fakes import FakeAuthClient, FakeRequestClient

@pytest.fixture
def api():
    service = PaymentService(make_factory(), auth=FakeAuthClient(), requests=FakeRequestClient())
    with serve(service, "PaymentServiceStub", pb_grpc) as (stub, channel):
        yield stub, channel, service


U2, U4 = str(sid("user-2")), str(sid("user-4"))
R3 = str(sid("req-3"))


def test_balance_and_payment(api):
    stub, channel, _ = api
    before = channel.call(stub.GetBalance, pb.GetBalanceRequest(expert_id=U2), idempotent=True)
    tx = channel.call(stub.CreatePayment, pb.CreatePaymentRequest(request_id=R3, client_id=U4, idempotency_key="key-grpc-0001"))
    assert tx.status == "SUCCESS" and tx.amount == 25.0
    assert channel.call(stub.GetBalance, pb.GetBalanceRequest(expert_id=U2)).earned > before.earned


def test_list_with_dates_and_summary(api):
    stub, channel, _ = api
    reply = channel.call(stub.ListTransactions, pb.ListTransactionsRequest(created_from="2026-01-01", created_to="2026-12-31"))
    assert len(reply.transactions) >= 1
    summary = channel.call(stub.GetTransactionsSummary, pb.TransactionsSummaryRequest())
    assert summary.count >= len(reply.transactions) and summary.total_amount > 0


def test_unknown_transaction(api):
    stub, channel, _ = api
    with pytest.raises(NotFoundError):
        channel.call(stub.GetTransaction, pb.GetTransactionRequest(transaction_id=str(sid("tx-404"))))
