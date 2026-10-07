from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session_factory
from .models import Transaction, Withdrawal

import uuid


def sid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"plant-detective/{name}")


def seed(session_factory: Optional[Callable[[], Session]] = None) -> bool:
    factory = session_factory or get_session_factory()
    with factory() as session:
        if session.scalars(select(Transaction)).first():
            return False
        session.add_all([
            Transaction(id=sid("tx-1"), request_id=sid("req-2"), user_id=sid("user-1"), expert_id=sid("user-2"),
                        amount=25.00, operation_type="PAYMENT", status="SUCCESS",
                        idempotency_key="demo-payment-req-2", created_at=datetime(2026, 1, 16, 12, 0)),
            Transaction(id=sid("tx-2"), request_id=sid("req-4"), user_id=sid("user-4"), expert_id=sid("user-2"),
                        amount=25.00, operation_type="PAYMENT", status="SUCCESS",
                        idempotency_key="demo-payment-req-4", created_at=datetime(2026, 1, 6, 10, 0)),
            Transaction(id=sid("tx-3"), request_id=sid("req-3"), user_id=sid("user-4"), expert_id=sid("user-2"),
                        amount=25.00, operation_type="PAYMENT", status="FAILED",
                        idempotency_key="demo-payment-req-3", created_at=datetime(2026, 1, 17, 9, 30)),
        ])
        session.add(Withdrawal(id=sid("wd-1"), expert_id=sid("user-2"), amount=30.00, status="PENDING",
                               created_at=datetime(2026, 1, 20, 10, 0)))
        session.commit()
        return True
