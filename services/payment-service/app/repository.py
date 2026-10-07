import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Transaction, Withdrawal

SORT_COLUMNS = {"created_at": Transaction.created_at, "amount": Transaction.amount}


def _dec(value) -> Decimal:
    return Decimal(str(value or 0))


class TransactionRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, obj) -> None:
        self.session.add(obj)

    def get_by_id(self, transaction_id: uuid.UUID) -> Optional[Transaction]:
        return self.session.get(Transaction, transaction_id)

    def get_by_key(self, key: str) -> Optional[Transaction]:
        return self.session.scalars(select(Transaction).where(Transaction.idempotency_key == key)).first()

    def has_successful_payment(self, request_id: uuid.UUID) -> bool:
        stmt = select(Transaction.id).where(Transaction.request_id == request_id,
                                            Transaction.operation_type == "PAYMENT", Transaction.status == "SUCCESS")
        return self.session.scalars(stmt).first() is not None

    def _filtered(self, stmt, request_id=None, user_id=None, expert_id=None, status=None, operation_type=None,
                  min_amount=None, max_amount=None, created_from: Optional[datetime] = None,
                  created_to: Optional[datetime] = None):
        if request_id:
            stmt = stmt.where(Transaction.request_id == request_id)
        if user_id:
            stmt = stmt.where(Transaction.user_id == user_id)
        if expert_id:
            stmt = stmt.where(Transaction.expert_id == expert_id)
        if status:
            stmt = stmt.where(Transaction.status == status)
        if operation_type:
            stmt = stmt.where(Transaction.operation_type == operation_type)
        if min_amount is not None:
            stmt = stmt.where(Transaction.amount >= min_amount)
        if max_amount is not None:
            stmt = stmt.where(Transaction.amount <= max_amount)
        if created_from:
            stmt = stmt.where(Transaction.created_at >= created_from)
        if created_to:
            stmt = stmt.where(Transaction.created_at <= created_to)
        return stmt

    def list_transactions(self, sort_by: str = "created_at", descending: bool = False,
                          limit: Optional[int] = None, offset: int = 0, **filters) -> list[Transaction]:
        stmt = self._filtered(select(Transaction), **filters)
        column = SORT_COLUMNS[sort_by]
        stmt = stmt.order_by(column.desc() if descending else column.asc(), Transaction.id)
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).all())

    def sum_grouped(self, column, **filters) -> dict:
        stmt = self._filtered(select(column, func.sum(Transaction.amount)).group_by(column), **filters)
        return {key: _dec(total) for key, total in self.session.execute(stmt).all()}

    def count(self, **filters) -> int:
        stmt = self._filtered(select(func.count(Transaction.id)), **filters)
        return self.session.scalar(stmt) or 0

    def earned_by_expert(self, expert_id: uuid.UUID) -> Decimal:
        stmt = select(func.sum(Transaction.amount)).where(
            Transaction.expert_id == expert_id, Transaction.operation_type == "PAYMENT",
            Transaction.status == "SUCCESS")
        return _dec(self.session.scalar(stmt))


class WithdrawalRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, obj) -> None:
        self.session.add(obj)

    def get_by_id(self, withdrawal_id: uuid.UUID) -> Optional[Withdrawal]:
        return self.session.get(Withdrawal, withdrawal_id)

    def list_withdrawals(self, expert_id: Optional[uuid.UUID] = None, status: Optional[str] = None,
                         descending: bool = False) -> list[Withdrawal]:
        stmt = select(Withdrawal)
        if expert_id:
            stmt = stmt.where(Withdrawal.expert_id == expert_id)
        if status:
            stmt = stmt.where(Withdrawal.status == status)
        column = Withdrawal.created_at
        return list(self.session.scalars(stmt.order_by(column.desc() if descending else column.asc())).all())

    def sum_by_status(self, expert_id: uuid.UUID, status: str) -> Decimal:
        stmt = select(func.sum(Withdrawal.amount)).where(Withdrawal.expert_id == expert_id, Withdrawal.status == status)
        return _dec(self.session.scalar(stmt))
