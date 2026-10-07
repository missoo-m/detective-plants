from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, Optional

from sqlalchemy.orm import Session

from . import config
from .clients import AuthClient, ChatClient, MockAuthClient, MockChatClient, MockRequestClient, RequestClient
from .database import get_session_factory
from .errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from .models import Transaction, Withdrawal, utcnow
from .repository import SORT_COLUMNS, TransactionRepository, WithdrawalRepository
from .schemas import BalanceDTO, TransactionDTO, TransactionsSummaryDTO, WithdrawalDTO
from .utils import fmt_dt, parse_uuid

TRANSACTION_STATUSES = {"PENDING", "SUCCESS", "FAILED"}
OPERATION_TYPES = {"PAYMENT", "PAYOUT", "REFUND"}
WITHDRAWAL_STATUSES = {"PENDING", "APPROVED", "REJECTED"}
CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _tx(t: Transaction) -> TransactionDTO:
    return TransactionDTO(id=str(t.id), request_id=str(t.request_id), user_id=str(t.user_id), amount=float(t.amount),
                          operation_type=t.operation_type, status=t.status, created_at=fmt_dt(t.created_at))


def _wd(w: Withdrawal) -> WithdrawalDTO:
    return WithdrawalDTO(id=str(w.id), expert_id=str(w.expert_id), amount=float(w.amount), status=w.status,
                         created_at=fmt_dt(w.created_at), processed_at=fmt_dt(w.processed_at))


class PaymentService:
    def __init__(self, session_factory: Optional[Callable[[], Session]] = None, auth: Optional[AuthClient] = None,
                 requests: Optional[RequestClient] = None, chat: Optional[ChatClient] = None):
        self._session_factory = session_factory or get_session_factory()
        self._auth = auth or MockAuthClient()
        self._requests = requests or MockRequestClient()
        self._chat = chat or MockChatClient()

    def _require_role(self, user_id: str, role: str) -> None:
        user = self._auth.get_user(user_id)
        if user["status"] != "ACTIVE":
            raise PermissionDeniedError("Учётная запись пользователя заблокирована или не активна")
        if user["role"] != role:
            raise PermissionDeniedError(f"Действие доступно только роли {role}")

    @staticmethod
    def _check_filters(status, operation_type, sort_by, min_amount, max_amount, created_from, created_to) -> None:
        if status is not None and status not in TRANSACTION_STATUSES:
            raise InvalidValueError(f"Неизвестный статус транзакции: {status}")
        if operation_type is not None and operation_type not in OPERATION_TYPES:
            raise InvalidValueError(f"Неизвестный тип операции: {operation_type}")
        if sort_by not in SORT_COLUMNS:
            raise InvalidValueError(f"Сортировка по полю {sort_by} не поддерживается")
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise InvalidValueError("Минимальная сумма не может быть больше максимальной")
        if created_from and created_to and created_from > created_to:
            raise InvalidValueError("Начало периода не может быть позже его конца")

    @staticmethod
    def _ids(request_id, user_id, expert_id) -> dict:
        return {"request_id": parse_uuid(request_id) if request_id else None,
                "user_id": parse_uuid(user_id) if user_id else None,
                "expert_id": parse_uuid(expert_id) if expert_id else None}

    def get_transaction(self, transaction_id: str) -> TransactionDTO:
        with self._session_factory() as session:
            tx = TransactionRepository(session).get_by_id(parse_uuid(transaction_id))
            if tx is None:
                raise NotFoundError(f"Транзакция {transaction_id} не найдена")
            return _tx(tx)

    def list_transactions(self, request_id: Optional[str] = None, user_id: Optional[str] = None,
                          expert_id: Optional[str] = None, status: Optional[str] = None,
                          operation_type: Optional[str] = None, min_amount: Optional[float] = None,
                          max_amount: Optional[float] = None, created_from: Optional[datetime] = None,
                          created_to: Optional[datetime] = None, sort_by: str = "created_at",
                          descending: bool = False, limit: Optional[int] = None, offset: int = 0) -> list[TransactionDTO]:
        self._check_filters(status, operation_type, sort_by, min_amount, max_amount, created_from, created_to)
        if (limit is not None and limit < 1) or offset < 0:
            raise InvalidValueError("limit должен быть больше 0, offset не может быть отрицательным")
        with self._session_factory() as session:
            items = TransactionRepository(session).list_transactions(
                sort_by, descending, limit, offset, **self._ids(request_id, user_id, expert_id), status=status,
                operation_type=operation_type, min_amount=min_amount, max_amount=max_amount,
                created_from=created_from, created_to=created_to)
            return [_tx(t) for t in items]

    def transactions_summary(self, request_id: Optional[str] = None, user_id: Optional[str] = None,
                             expert_id: Optional[str] = None, status: Optional[str] = None,
                             operation_type: Optional[str] = None, created_from: Optional[datetime] = None,
                             created_to: Optional[datetime] = None) -> TransactionsSummaryDTO:
        self._check_filters(status, operation_type, "created_at", None, None, created_from, created_to)
        filters = dict(**self._ids(request_id, user_id, expert_id), status=status, operation_type=operation_type,
                       created_from=created_from, created_to=created_to)
        with self._session_factory() as session:
            repo = TransactionRepository(session)
            by_status = repo.sum_grouped(Transaction.status, **filters)
            by_type = repo.sum_grouped(Transaction.operation_type, **filters)
            return TransactionsSummaryDTO(
                count=repo.count(**filters), total_amount=float(sum(by_status.values(), Decimal("0"))),
                by_status={k: float(v) for k, v in by_status.items()}, by_type={k: float(v) for k, v in by_type.items()})

    def list_withdrawals(self, expert_id: Optional[str] = None, status: Optional[str] = None,
                         descending: bool = False) -> list[WithdrawalDTO]:
        if status is not None and status not in WITHDRAWAL_STATUSES:
            raise InvalidValueError(f"Неизвестный статус вывода: {status}")
        eid = parse_uuid(expert_id) if expert_id else None
        with self._session_factory() as session:
            return [_wd(w) for w in WithdrawalRepository(session).list_withdrawals(eid, status, descending)]

    def expert_balance(self, expert_id: str) -> BalanceDTO:
        eid = parse_uuid(expert_id)
        with self._session_factory() as session:
            return self._balance(session, eid)

    @staticmethod
    def _balance(session: Session, eid) -> BalanceDTO:
        earned = TransactionRepository(session).earned_by_expert(eid)
        commission = _money(earned * config.COMMISSION_RATE)
        wd = WithdrawalRepository(session)
        withdrawn, pending = wd.sum_by_status(eid, "APPROVED"), wd.sum_by_status(eid, "PENDING")
        available = earned - commission - withdrawn - pending
        return BalanceDTO(expert_id=str(eid), earned=float(earned), commission=float(commission),
                          withdrawn=float(withdrawn), pending=float(pending), available=float(available))

    def create_payment(self, request_id: str, client_id: str, idempotency_key: str) -> TransactionDTO:
        key = (idempotency_key or "").strip()
        if not 8 <= len(key) <= 64:
            raise InvalidValueError("Ключ идемпотентности должен содержать от 8 до 64 символов")
        rid, cid = parse_uuid(request_id), parse_uuid(client_id)
        with self._session_factory() as session:
            repo = TransactionRepository(session)
            existing = repo.get_by_key(key)
            if existing is not None:                          
                if existing.request_id != rid or existing.user_id != cid:
                    raise BusinessRuleError("Ключ идемпотентности уже использован для другой операции")
                return _tx(existing)
            self._require_role(client_id, "CLIENT")
            request = self._requests.get_request(request_id)
            if request["client_id"] != client_id:
                raise PermissionDeniedError("Оплатить заявку может только её автор")
            if not request["expert_id"] or request["status"] != "PENDING":
                raise BusinessRuleError("Оплата возможна после выбора эксперта (статус заявки PENDING)")
            if repo.has_successful_payment(rid):
                raise BusinessRuleError("Заявка уже оплачена")
            tx = Transaction(request_id=rid, user_id=cid, expert_id=parse_uuid(request["expert_id"]),
                             amount=config.SERVICE_PRICE, operation_type="PAYMENT", status="SUCCESS",
                             idempotency_key=key)             
            repo.add(tx)
            session.commit()
            result = _tx(tx)
            expert_id = request["expert_id"]
        self._requests.start_work(request_id)                 
        self._chat.open_room(request_id, client_id, expert_id)
        return result

    def request_withdrawal(self, expert_id: str, amount: float) -> WithdrawalDTO:
        eid = parse_uuid(expert_id)
        value = _money(Decimal(str(amount)))
        if value < config.MIN_WITHDRAWAL:
            raise InvalidValueError(f"Минимальная сумма вывода — {config.MIN_WITHDRAWAL} BYN")
        self._require_role(expert_id, "EXPERT")
        with self._session_factory() as session:
            available = Decimal(str(self._balance(session, eid).available))
            if value > available:
                raise BusinessRuleError(f"Недостаточно средств: доступно {available} BYN, запрошено {value} BYN")
            wd = Withdrawal(expert_id=eid, amount=value, status="PENDING")
            WithdrawalRepository(session).add(wd)
            session.commit()
            return _wd(wd)

    def approve_withdrawal(self, withdrawal_id: str, admin_id: str) -> WithdrawalDTO:
        self._require_role(admin_id, "ADMIN")
        with self._session_factory() as session:
            wd = WithdrawalRepository(session).get_by_id(parse_uuid(withdrawal_id))
            if wd is None:
                raise NotFoundError(f"Заявка на вывод {withdrawal_id} не найдена")
            if wd.status != "PENDING":
                raise BusinessRuleError(f"Заявка уже обработана (статус {wd.status})")
            wd.status = "APPROVED"
            wd.processed_at = utcnow()
            session.commit()
            return _wd(wd)
