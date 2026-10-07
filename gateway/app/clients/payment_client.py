import copy
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from ..errors import BusinessRuleError, NotFoundError, PermissionDeniedError, ValidationError
from .base import PaymentClientBase
from .common import check_period, check_sort, count_by, lower_bound, new_id, now_iso, paginate, parse_iso, upper_bound

SERVICE_PRICE = Decimal("25.00")
COMMISSION_RATE = Decimal("0.10")
MIN_WITHDRAWAL = Decimal("10.00")
TRANSACTION_STATUSES = {"PENDING", "SUCCESS", "FAILED"}
OPERATION_TYPES = {"PAYMENT", "PAYOUT", "REFUND"}
WITHDRAWAL_STATUSES = {"PENDING", "APPROVED", "REJECTED"}

MOCK_TRANSACTIONS = {
    "tx-1": {"id": "tx-1", "request_id": "req-2", "user_id": "user-1", "expert_id": "user-2", "amount": 25.0,
             "operation_type": "PAYMENT", "status": "SUCCESS", "idempotency_key": "demo-payment-req-2",
             "created_at": "2026-01-16T12:00:00Z"},
    "tx-2": {"id": "tx-2", "request_id": "req-4", "user_id": "user-4", "expert_id": "user-2", "amount": 25.0,
             "operation_type": "PAYMENT", "status": "SUCCESS", "idempotency_key": "demo-payment-req-4",
             "created_at": "2026-01-06T10:00:00Z"},
    "tx-3": {"id": "tx-3", "request_id": "req-3", "user_id": "user-4", "expert_id": "user-2", "amount": 25.0,
             "operation_type": "PAYMENT", "status": "FAILED", "idempotency_key": "demo-payment-req-3",
             "created_at": "2026-01-17T09:30:00Z"},
}

MOCK_WITHDRAWALS = {
    "wd-1": {"id": "wd-1", "expert_id": "user-2", "amount": 30.0, "status": "PENDING",
             "created_at": "2026-01-20T10:00:00Z", "processed_at": None},
}


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class MockPaymentClient(PaymentClientBase):
    #Mock Payment Service

    def __init__(self):
        self.transactions = copy.deepcopy(MOCK_TRANSACTIONS)
        self.withdrawals = copy.deepcopy(MOCK_WITHDRAWALS)

    @staticmethod
    def _registry():
        from .. import clients
        return clients

    def _require_role(self, user_id: str, role: str) -> None:
        user = self._registry().auth_client.get_user(user_id)
        if user["status"] != "ACTIVE":
            raise PermissionDeniedError("Учётная запись пользователя заблокирована или не активна")
        if user["role"] != role:
            raise PermissionDeniedError(f"Действие доступно только роли {role}")

    def _filter(self, request_id=None, user_id=None, expert_id=None, status=None, operation_type=None,
                min_amount=None, max_amount=None, created_from=None, created_to=None) -> list[dict]:
        if status is not None and status not in TRANSACTION_STATUSES:
            raise ValidationError(f"Неизвестный статус транзакции: {status}")
        if operation_type is not None and operation_type not in OPERATION_TYPES:
            raise ValidationError(f"Неизвестный тип операции: {operation_type}")
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise ValidationError("Минимальная сумма не может быть больше максимальной")
        start, end = lower_bound(created_from), upper_bound(created_to)
        check_period(start, end)
        items = list(self.transactions.values())
        for key, value in (("request_id", request_id), ("user_id", user_id), ("expert_id", expert_id),
                           ("status", status), ("operation_type", operation_type)):
            if value:
                items = [t for t in items if t[key] == value]
        if min_amount is not None:
            items = [t for t in items if t["amount"] >= min_amount]
        if max_amount is not None:
            items = [t for t in items if t["amount"] <= max_amount]
        if start:
            items = [t for t in items if parse_iso(t["created_at"]) >= start]
        if end:
            items = [t for t in items if parse_iso(t["created_at"]) <= end]
        return items

    # ---- чтение
    def get_transaction(self, transaction_id: str) -> dict:
        tx = self.transactions.get(transaction_id)
        if not tx:
            raise NotFoundError(f"Транзакция {transaction_id} не найдена")
        return tx

    def list_transactions(self, request_id=None, user_id=None, expert_id=None, status=None, operation_type=None,
                          min_amount=None, max_amount=None, created_from=None, created_to=None,
                          sort_by="created_at", descending=False, limit=None, offset=0) -> list[dict]:
        check_sort(sort_by, {"created_at", "amount"})
        items = self._filter(request_id, user_id, expert_id, status, operation_type, min_amount, max_amount,
                             created_from, created_to)
        items.sort(key=lambda t: (t[sort_by], t["id"]), reverse=descending)
        return paginate(items, limit, offset)

    def transactions_summary(self, request_id=None, user_id=None, expert_id=None, status=None,
                             operation_type=None) -> dict:
        items = self._filter(request_id, user_id, expert_id, status, operation_type)
        by_status, by_type = {}, {}
        for t in items:
            by_status[t["status"]] = by_status.get(t["status"], 0.0) + t["amount"]
            by_type[t["operation_type"]] = by_type.get(t["operation_type"], 0.0) + t["amount"]
        return {"count": len(items), "total_amount": sum(t["amount"] for t in items),
                "by_status": by_status, "by_type": by_type}

    def list_withdrawals(self, expert_id=None, status=None, descending=False) -> list[dict]:
        if status is not None and status not in WITHDRAWAL_STATUSES:
            raise ValidationError(f"Неизвестный статус вывода: {status}")
        items = list(self.withdrawals.values())
        if expert_id:
            items = [w for w in items if w["expert_id"] == expert_id]
        if status:
            items = [w for w in items if w["status"] == status]
        items.sort(key=lambda w: w["created_at"], reverse=descending)
        return items

    def expert_balance(self, expert_id: str) -> dict:
        earned = sum((Decimal(str(t["amount"])) for t in self.transactions.values()
                      if t["expert_id"] == expert_id and t["operation_type"] == "PAYMENT" and t["status"] == "SUCCESS"),
                     Decimal("0"))
        commission = _money(earned * COMMISSION_RATE)

        def total(status: str) -> Decimal:
            return sum((Decimal(str(w["amount"])) for w in self.withdrawals.values()
                        if w["expert_id"] == expert_id and w["status"] == status), Decimal("0"))

        withdrawn, pending = total("APPROVED"), total("PENDING")
        return {"expert_id": expert_id, "earned": float(earned), "commission": float(commission),
                "withdrawn": float(withdrawn), "pending": float(pending),
                "available": float(earned - commission - withdrawn - pending)}

    # ---- бизнес-операции
    def create_payment(self, request_id: str, client_id: str, idempotency_key: str) -> dict:
        key = (idempotency_key or "").strip()
        if not 8 <= len(key) <= 64:
            raise ValidationError("Ключ идемпотентности должен содержать от 8 до 64 символов")
        existing = next((t for t in self.transactions.values() if t["idempotency_key"] == key), None)
        if existing is not None:
            if existing["request_id"] != request_id or existing["user_id"] != client_id:
                raise BusinessRuleError("Ключ идемпотентности уже использован для другой операции")
            return existing
        self._require_role(client_id, "CLIENT")
        registry = self._registry()
        request = registry.request_client.get_request(request_id)
        if request["client_id"] != client_id:
            raise PermissionDeniedError("Оплатить заявку может только её автор")
        if not request["expert_id"] or request["status"] != "PENDING":
            raise BusinessRuleError("Оплата возможна после выбора эксперта (статус заявки PENDING)")
        if any(t["request_id"] == request_id and t["operation_type"] == "PAYMENT" and t["status"] == "SUCCESS"
               for t in self.transactions.values()):
            raise BusinessRuleError("Заявка уже оплачена")
        tx = {"id": new_id("tx"), "request_id": request_id, "user_id": client_id, "expert_id": request["expert_id"],
              "amount": float(SERVICE_PRICE), "operation_type": "PAYMENT", "status": "SUCCESS",
              "idempotency_key": key, "created_at": now_iso()}
        self.transactions[tx["id"]] = tx
        registry.request_client.start_work(request_id)
        registry.chat_client.open_room(request_id, client_id, request["expert_id"])
        return tx

    def request_withdrawal(self, expert_id: str, amount: float) -> dict:
        value = _money(Decimal(str(amount)))
        if value < MIN_WITHDRAWAL:
            raise ValidationError(f"Минимальная сумма вывода — {MIN_WITHDRAWAL} BYN")
        self._require_role(expert_id, "EXPERT")
        available = Decimal(str(self.expert_balance(expert_id)["available"]))
        if value > available:
            raise BusinessRuleError(f"Недостаточно средств: доступно {available} BYN, запрошено {value} BYN")
        wd = {"id": new_id("wd"), "expert_id": expert_id, "amount": float(value), "status": "PENDING",
              "created_at": now_iso(), "processed_at": None}
        self.withdrawals[wd["id"]] = wd
        return wd

    def approve_withdrawal(self, withdrawal_id: str, admin_id: str) -> dict:
        self._require_role(admin_id, "ADMIN")
        wd = self.withdrawals.get(withdrawal_id)
        if not wd:
            raise NotFoundError(f"Заявка на вывод {withdrawal_id} не найдена")
        if wd["status"] != "PENDING":
            raise BusinessRuleError(f"Заявка уже обработана (статус {wd['status']})")
        wd["status"], wd["processed_at"] = "APPROVED", now_iso()
        return wd
