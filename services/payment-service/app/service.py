"""Сервисный слой Payment Service."""
from typing import Callable, Optional

from sqlalchemy.orm import Session

from .database import get_session_factory
from .errors import InvalidValueError, NotFoundError
from .models import Transaction, Withdrawal
from .repository import TransactionRepository, WithdrawalRepository
from .schemas import TransactionDTO, WithdrawalDTO
from .utils import fmt_dt, parse_uuid

WITHDRAWAL_STATUSES = {"PENDING", "APPROVED", "REJECTED"}


def _tx(t: Transaction) -> TransactionDTO:
    return TransactionDTO(id=str(t.id), request_id=str(t.request_id), user_id=str(t.user_id),
                          amount=float(t.amount), operation_type=t.operation_type, status=t.status,
                          created_at=fmt_dt(t.created_at))


def _wd(w: Withdrawal) -> WithdrawalDTO:
    return WithdrawalDTO(id=str(w.id), expert_id=str(w.expert_id), amount=float(w.amount),
                         status=w.status, created_at=fmt_dt(w.created_at),
                         processed_at=fmt_dt(w.processed_at))


class PaymentService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None):
        self._session_factory = session_factory or get_session_factory()

    def get_transaction(self, transaction_id: str) -> TransactionDTO:
        tid = parse_uuid(transaction_id)
        with self._session_factory() as session:
            tx = TransactionRepository(session).get_by_id(tid)
            if tx is None:
                raise NotFoundError(f"Транзакция {transaction_id} не найдена")
            return _tx(tx)

    def list_transactions(self, request_id: Optional[str] = None,
                          user_id: Optional[str] = None) -> list[TransactionDTO]:
        rid = parse_uuid(request_id) if request_id else None
        uid = parse_uuid(user_id) if user_id else None
        with self._session_factory() as session:
            return [_tx(t) for t in TransactionRepository(session).list_transactions(rid, uid)]

    def list_withdrawals(self, expert_id: Optional[str] = None,
                         status: Optional[str] = None) -> list[WithdrawalDTO]:
        if status is not None and status not in WITHDRAWAL_STATUSES:
            raise InvalidValueError(f"Неизвестный статус вывода: {status}")
        eid = parse_uuid(expert_id) if expert_id else None
        with self._session_factory() as session:
            return [_wd(w) for w in WithdrawalRepository(session).list_withdrawals(eid, status)]
