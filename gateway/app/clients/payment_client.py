from typing import Optional
from .base import NotFoundError, PaymentClientBase

MOCK_TRANSACTIONS = {
    "tx-1": {
        "id": "tx-1",
        "request_id": "req-2",
        "user_id": "user-1",
        "amount": 25.0,
        "operation_type": "PAYMENT",
        "status": "SUCCESS",
        "created_at": "2026-01-16T12:00:00Z",
    },
}

MOCK_WITHDRAWALS = {
    "wd-1": {
        "id": "wd-1",
        "expert_id": "user-2",
        "amount": 100.0,
        "status": "PENDING",
        "created_at": "2026-01-20T10:00:00Z",
        "processed_at": None,
    },
}


class MockPaymentClient(PaymentClientBase):
    #Mock-клиент Payment Service

    def get_transaction(self, transaction_id: str) -> dict:
        tx = MOCK_TRANSACTIONS.get(transaction_id)
        if not tx:
            raise NotFoundError(f"Транзакция {transaction_id} не найдена")
        return tx

    def list_transactions(self, request_id: Optional[str] = None,
                          user_id: Optional[str] = None) -> list[dict]:
        txs = list(MOCK_TRANSACTIONS.values())
        if request_id:
            txs = [t for t in txs if t["request_id"] == request_id]
        if user_id:
            txs = [t for t in txs if t["user_id"] == user_id]
        return txs

    def list_withdrawals(self, expert_id: Optional[str] = None) -> list[dict]:
        wds = list(MOCK_WITHDRAWALS.values())
        if expert_id:
            wds = [w for w in wds if w["expert_id"] == expert_id]
        return wds