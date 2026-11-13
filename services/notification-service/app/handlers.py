from .models import Notification
from .repository import NotificationRepository
from .utils import parse_uuid


def _notify(session, user_id: str, kind: str, text: str) -> None:
    NotificationRepository(session).add(Notification(user_id=parse_uuid(user_id), type=kind, message=text[:1000],
                                                     status="UNREAD"))


def _short(text, limit: int = 80) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def build_handlers(service=None):
    def user_registered(e, s):
        _notify(s, e["payload"]["user_id"], "WELCOME", f"Добро пожаловать, {e['payload']['name']}! Аккаунт создан.")

    def request_created(e, s):
        _notify(s, e["payload"]["client_id"], "REQUEST_CREATED", "Заявка создана. Эксперты скоро откликнутся.")

    def expert_response(e, s):
        _notify(s, e["payload"]["client_id"], "EXPERT_RESPONSE", "Эксперт откликнулся на вашу заявку.")

    def expert_selected(e, s):
        _notify(s, e["payload"]["expert_id"], "EXPERT_SELECTED", "Клиент выбрал вас. Ожидайте оплату заявки.")

    def payment_completed(e, s):
        p = e["payload"]
        _notify(s, p["client_id"], "PAYMENT_COMPLETED", f"Оплата {p['amount']} {p['currency']} прошла успешно.")
        _notify(s, p["expert_id"], "PAYMENT_RECEIVED", "Заявка оплачена клиентом — можно ставить диагноз.")

    def diagnosis_created(e, s):
        _notify(s, e["payload"]["client_id"], "DIAGNOSIS_READY", "Диагноз готов: " + _short(e["payload"]["description"]))

    def tracker_created(e, s):
        _notify(s, e["payload"]["client_id"], "TRACKER_CREATED",
                f"Создан трекер выздоровления на {e['payload']['duration_days']} дн.")

    def photo_uploaded(e, s):
        _notify(s, e["payload"]["expert_id"], "TRACKER_PHOTO", "Клиент загрузил новое фото растения в трекер.")

    def tracker_completed(e, s):
        _notify(s, e["payload"]["client_id"], "TRACKER_COMPLETED", "Лечение завершено, заявка закрыта.")

    def message_sent(e, s):
        _notify(s, e["payload"]["recipient_id"], "NEW_MESSAGE", "Новое сообщение: " + _short(e["payload"].get("text")))

    def withdrawal_requested(e, s):
        _notify(s, e["payload"]["expert_id"], "WITHDRAWAL_REQUESTED",
                f"Заявка на вывод {e['payload']['amount']} BYN принята.")

    def withdrawal_approved(e, s):
        _notify(s, e["payload"]["expert_id"], "WITHDRAWAL_APPROVED",
                f"Вывод {e['payload']['amount']} BYN одобрен администратором.")

    def payment_refunded(e, s):
        p = e["payload"]
        _notify(s, p["client_id"], "PAYMENT_REFUNDED", f"Платёж {p['amount']} {p['currency']} возвращён: {p['reason']}")

    def expert_verified(e, s):
        _notify(s, e["payload"]["user_id"], "EXPERT_VERIFIED", "Вы подтверждены как эксперт.")

    def user_blocked(e, s):
        _notify(s, e["payload"]["user_id"], "USER_BLOCKED", "Ваша учётная запись заблокирована администратором.")

    def satellite_alert(e, s):
        _notify(s, e["payload"]["owner_id"], "SATELLITE_ALERT", e["payload"]["message"])

    return {"UserRegistered": user_registered, "RequestCreated": request_created,
            "ExpertResponseCreated": expert_response, "ExpertSelected": expert_selected,
            "PaymentCompleted": payment_completed, "DiagnosisCreated": diagnosis_created,
            "TrackerCreated": tracker_created, "PhotoUploaded": photo_uploaded,
            "TrackerCompleted": tracker_completed, "MessageSent": message_sent,
            "WithdrawalRequested": withdrawal_requested, "WithdrawalApproved": withdrawal_approved,
            "PaymentRefunded": payment_refunded, "ExpertVerified": expert_verified, "UserBlocked": user_blocked, "SatelliteAlertCreated": satellite_alert}
