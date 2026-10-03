from dataclasses import dataclass
from typing import Optional


@dataclass
class TransactionDTO:
    id: str
    request_id: str
    user_id: str
    amount: float
    operation_type: str
    status: str
    created_at: str


@dataclass
class WithdrawalDTO:
    id: str
    expert_id: str
    amount: float
    status: str
    created_at: str
    processed_at: Optional[str]
