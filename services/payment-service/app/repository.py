import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Transaction, Withdrawal


class TransactionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, transaction_id: uuid.UUID) -> Optional[Transaction]:
        return self.session.get(Transaction, transaction_id)

    def list_transactions(self, request_id: Optional[uuid.UUID] = None,
                          user_id: Optional[uuid.UUID] = None) -> list[Transaction]:
        stmt = select(Transaction)
        if request_id:
            stmt = stmt.where(Transaction.request_id == request_id)
        if user_id:
            stmt = stmt.where(Transaction.user_id == user_id)
        return list(self.session.scalars(stmt.order_by(Transaction.created_at)).all())


class WithdrawalRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_withdrawals(self, expert_id: Optional[uuid.UUID] = None,
                         status: Optional[str] = None) -> list[Withdrawal]:
        stmt = select(Withdrawal)
        if expert_id:
            stmt = stmt.where(Withdrawal.expert_id == expert_id)
        if status:
            stmt = stmt.where(Withdrawal.status == status)
        return list(self.session.scalars(stmt.order_by(Withdrawal.created_at)).all())
