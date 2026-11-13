import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from . import config
from .logging_setup import correlation_id, new_correlation_id
from .errors import (BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError,
                     ServiceUnavailableError)

log = logging.getLogger("events")

TOPIC_OF = {
    "UserRegistered": "auth.events",
    "ExpertVerified": "admin.events", "UserBlocked": "admin.events",
    "RequestCreated": "request.events", "ExpertSelected": "request.events",
    "ExpertResponseCreated": "expert.events", "DiagnosisCreated": "expert.events",
    "PhotoUploaded": "recovery.events", "TreatmentUpdated": "recovery.events",
    "TrackerCreated": "recovery.events", "TrackerCompleted": "recovery.events",
    "PaymentCompleted": "payment.events", "WithdrawalRequested": "payment.events",
    "WithdrawalApproved": "payment.events",
    "PaymentRejected": "request.events",
    "PaymentRefunded": "payment.events",
    "MessageSent": "chat.events",
    "SatelliteAlertCreated": "satellite.events",
}
DEAD_LETTER_TOPIC = "dead-letter.events"
TOPIC_SPECS = {
    "auth.events": (3, 7), "admin.events": (3, 30), "request.events": (6, 30), "expert.events": (6, 30),
    "recovery.events": (3, 30), "payment.events": (6, 90), "chat.events": (6, 7), "satellite.events": (3, 30),
    DEAD_LETTER_TOPIC: (1, 30),
}
KEY_FIELDS = ("request_id", "chat_room_id", "user_id", "field_id", "expert_id", "withdrawal_id")


def make_event(event_type: str, payload: dict) -> dict:
    if event_type not in TOPIC_OF:
        raise ValueError(f"Неизвестный тип события: {event_type}")
    current = correlation_id.get()
    return {"event_id": str(uuid.uuid4()), "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "correlation_id": None if current == "-" else current, "payload": payload}


def partition_key(payload: dict) -> Optional[str]:
    return next((str(payload[k]) for k in KEY_FIELDS if payload.get(k)), None)


def add_event(session, event_type: str, payload: dict) -> dict:
    from .models import OutboxEvent
    event = make_event(event_type, payload)
    session.add(OutboxEvent(event_id=event["event_id"], topic=TOPIC_OF[event_type], event_key=partition_key(payload),
                            event_type=event_type, body=json.dumps(event, ensure_ascii=False)))
    return event


class KafkaProducer:

    def __init__(self, bootstrap: Optional[str] = None, producer=None):
        if producer is None:
            from confluent_kafka import Producer
            producer = Producer({"bootstrap.servers": bootstrap or config.KAFKA_BOOTSTRAP_SERVERS, "acks": "all",
                                 "enable.idempotence": True, "retries": 5, "linger.ms": 5,
                                 "message.timeout.ms": 10000, "socket.timeout.ms": 5000})
        self._producer = producer

    def send(self, topic: str, key: Optional[str], body: str) -> None:
        failures: list = []

        def on_delivery(error, _message):
            if error is not None:
                failures.append(error)

        try:
            self._producer.produce(topic, value=body.encode("utf-8"), key=key.encode("utf-8") if key else None,
                                   on_delivery=on_delivery)
            pending = self._producer.flush(10)
        except Exception as error:
            raise ServiceUnavailableError(f"Kafka недоступна: {error}") from None
        if failures or pending:
            raise ServiceUnavailableError(f"Событие не доставлено в {topic}: {failures[0] if failures else 'таймаут'}")


class OutboxRelay(threading.Thread):

    MAX_PAUSE = 30.0

    def __init__(self, session_factory: Callable, producer, interval: Optional[float] = None, batch_size: int = 50,
                 clock: Callable[[], float] = time.monotonic):
        super().__init__(name="outbox-relay", daemon=True)
        self._session_factory, self._producer = session_factory, producer
        self._interval = interval if interval is not None else config.OUTBOX_POLL_SECONDS
        self._batch, self._stop_flag, self._clock = batch_size, threading.Event(), clock
        self._failures, self._retry_at = 0, 0.0

    @property
    def pause(self) -> float:
        return 0.0 if not self._failures else min(self.MAX_PAUSE, 0.5 * 2 ** (self._failures - 1))

    def pending(self) -> int:
        from sqlalchemy import func, select
        from .models import OutboxEvent
        with self._session_factory() as session:
            return session.scalar(select(func.count()).select_from(OutboxEvent).where(OutboxEvent.published_at.is_(None))) or 0

    def flush_once(self) -> int:
        from sqlalchemy import select
        from .models import OutboxEvent
        if self._clock() < self._retry_at:
            return 0
        sent = 0
        with self._session_factory() as session:
            rows = session.scalars(select(OutboxEvent).where(OutboxEvent.published_at.is_(None))
                                   .order_by(OutboxEvent.seq).limit(self._batch)
                                   .with_for_update(skip_locked=True)).all()
            for row in rows:
                body = json.loads(row.body)
                token = correlation_id.set(body.get("correlation_id") or "-")
                try:
                    self._producer.send(row.topic, row.event_key, row.body)
                except Exception as error:
                    row.attempts = (row.attempts or 0) + 1
                    self._failures += 1
                    self._retry_at = self._clock() + self.pause
                    log.log(logging.ERROR if row.attempts >= 10 else logging.WARNING,
                            "Kafka: событие %s (%s) не отправлено, попытка %s, следующая через %.1f с: %s",
                            row.event_type, row.event_id, row.attempts, self.pause, error)
                    break
                finally:
                    correlation_id.reset(token)
                row.published_at = datetime.now(timezone.utc).replace(tzinfo=None)
                self._failures, self._retry_at = 0, 0.0
                sent += 1
                log.info("Kafka: отправлено %s (%s) в %s", row.event_type, row.event_id, row.topic)
            session.commit()
        return sent

    def run(self) -> None:
        while not self._stop_flag.is_set():
            try:
                if self.flush_once() == 0:
                    self._stop_flag.wait(max(self._interval, 0.05))
            except Exception:
                log.exception("Сбой отправки событий из outbox")
                self._stop_flag.wait(max(self._interval, 2.0))

    def stop(self) -> None:
        self._stop_flag.set()


Handler = Callable[[dict, object], None]
PERMANENT_ERRORS = (NotFoundError, InvalidValueError, BusinessRuleError, PermissionDeniedError)


class EventConsumer(threading.Thread):
    def __init__(self, session_factory: Callable, handlers: dict, group_id: Optional[str] = None,
                 bootstrap: Optional[str] = None, consumer=None, dead_letter_producer=None, max_attempts: int = 3,
                 poll_timeout: float = 1.0, sleep: Callable[[float], None] = time.sleep,
                 after_handled: Optional[Callable[[dict], None]] = None):
        super().__init__(name="event-consumer", daemon=True)
        self._session_factory, self._handlers = session_factory, handlers
        self._group = group_id or config.KAFKA_GROUP_ID
        self._kafka_bootstrap = bootstrap or config.KAFKA_BOOTSTRAP_SERVERS
        self._consumer, self._dlq = consumer, dead_letter_producer
        self._max_attempts, self._poll, self._sleep = max_attempts, poll_timeout, sleep
        self._after_handled = after_handled
        self._stop_flag = threading.Event()
        self.topics = sorted({TOPIC_OF[t] for t in handlers})

    def process(self, raw, force: bool = False) -> str:
        text = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
        try:
            event = json.loads(text)
            event_id, event_type = str(event["event_id"]), event["event_type"]
            if not isinstance(event["payload"], dict):
                raise TypeError("payload")
        except (ValueError, KeyError, TypeError):
            log.error("Некорректное сообщение пропущено: %.200s", text)
            self._dead_letter(text, "некорректный формат события")
            return "invalid"
        handler = self._handlers.get(event_type)
        if handler is None:
            return "ignored"
        token = correlation_id.set(event.get("correlation_id") or new_correlation_id())
        started = time.monotonic()
        try:
            outcome = self._handle(event, text, event_id, event_type, handler, force)
        finally:
            elapsed = (time.monotonic() - started) * 1000
            correlation_id.reset(token)
        return self._report(outcome, event, elapsed)

    def _report(self, outcome: str, event: dict, elapsed: float) -> str:
        token = correlation_id.set(event.get("correlation_id") or "-")
        try:
            level = logging.INFO if outcome in ("handled", "duplicate") else logging.ERROR
            log.log(level, "Kafka ← %s (%s): %s, %.0f мс", event["event_type"], event["event_id"], outcome, elapsed)
        finally:
            correlation_id.reset(token)
        return outcome

    def _handle(self, event, text, event_id, event_type, handler, force) -> str:
        from .models import ProcessedEvent
        if not force:
            with self._session_factory() as session:
                if session.get(ProcessedEvent, event_id) is not None:
                    return "duplicate"
        for attempt in range(1, self._max_attempts + 1):
            with self._session_factory() as session:
                try:
                    handler(event, session)
                    if session.get(ProcessedEvent, event_id) is None:
                        session.add(ProcessedEvent(event_id=event_id, event_type=event_type))
                    session.commit()
                except PERMANENT_ERRORS as error:
                    session.rollback()
                    log.error("Событие %s (%s) отклонено: %s", event_type, event_id, error)
                    self._dead_letter(text, f"{type(error).__name__}: {error}", event_id, event_type)
                    self._mark_processed(event_id, event_type)
                    return "rejected"
                except Exception as error:
                    session.rollback()
                    log.warning("Событие %s (%s): попытка %s/%s не удалась: %s", event_type, event_id, attempt,
                                self._max_attempts, error)
                else:
                    self._notify_handled(event)
                    return "handled"
            if attempt < self._max_attempts:
                self._sleep(0.5 * 2 ** (attempt - 1))
        self._dead_letter(text, "превышено число попыток обработки", event_id, event_type)
        return "failed"

    def _notify_handled(self, event: dict) -> None:
        if self._after_handled is not None:
            try:
                self._after_handled(event)
            except Exception:
                log.exception("Ошибка действия после обработки события %s", event.get("event_id"))

    def _mark_processed(self, event_id: str, event_type: str) -> None:
        from .models import ProcessedEvent
        try:
            with self._session_factory() as session:
                if session.get(ProcessedEvent, event_id) is None:
                    session.add(ProcessedEvent(event_id=event_id, event_type=event_type))
                    session.commit()
        except Exception:
            log.exception("Не удалось пометить событие %s обработанным", event_id)

    def _dead_letter(self, text: str, reason: str, event_id: Optional[str] = None, event_type: Optional[str] = None) -> None:
        try:
            from .models import DeadLetter
            with self._session_factory() as session:
                session.add(DeadLetter(event_id=event_id, event_type=event_type, reason=reason[:2000], body=text))
                session.commit()
        except Exception:
            log.exception("Не удалось сохранить необработанное событие в dead_letters")
        if self._dlq is None:
            return
        try:
            self._dlq.send(DEAD_LETTER_TOPIC, None, json.dumps(
                {"service": config.SERVICE_NAME, "reason": reason, "message": text}, ensure_ascii=False))
        except Exception:
            log.exception("Не удалось отправить сообщение в %s", DEAD_LETTER_TOPIC)

    def replay_dead_letters(self) -> dict:
        from sqlalchemy import select
        from .models import DeadLetter
        with self._session_factory() as session:
            pending = [(row.id, row.body) for row in session.scalars(
                select(DeadLetter).where(DeadLetter.replayed_at.is_(None)).order_by(DeadLetter.id)).all()]
        result = {"handled": 0, "still_failing": 0}
        for row_id, body in pending:
            outcome = self.process(body, force=True)
            if outcome in ("handled", "duplicate", "ignored"):
                with self._session_factory() as session:
                    row = session.get(DeadLetter, row_id)
                    row.replayed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    session.commit()
                result["handled"] += 1
            else:
                result["still_failing"] += 1
        log.info("Повторная обработка dead_letters: %s", result)
        return result

    def _build_consumer(self):
        from confluent_kafka import Consumer
        return Consumer({"bootstrap.servers": self._kafka_bootstrap, "group.id": self._group,
                         "enable.auto.commit": False, "auto.offset.reset": "earliest",
                         "allow.auto.create.topics": True, "session.timeout.ms": 15000})

    def run(self) -> None:
        pause = 1.0
        while not self._stop_flag.is_set():
            consumer = self._consumer or self._build_consumer()
            try:
                consumer.subscribe(self.topics)
                log.info("Потребитель %s подписан на %s", self._group, ", ".join(self.topics))
                pause = 1.0
                while not self._stop_flag.is_set():
                    message = consumer.poll(self._poll)
                    if message is None:
                        continue
                    if message.error():
                        log.warning("Ошибка Kafka: %s", message.error())
                        self._stop_flag.wait(0.5)
                        continue
                    self.process(message.value())
                    consumer.commit(message=message, asynchronous=False)
                break
            except Exception:
                log.exception("Сбой потребителя Kafka, переподключение через %.0f с", pause)
                self._stop_flag.wait(pause)
                pause = min(pause * 2, 30.0)
            finally:
                try:
                    consumer.close()
                except Exception:
                    pass
                if self._consumer is not None:
                    break

    def stop(self) -> None:
        self._stop_flag.set()


def ensure_topics(bootstrap: Optional[str] = None, timeout: float = 10.0, attempts: int = 3,
                  sleep: Callable[[float], None] = time.sleep) -> bool:
    for attempt in range(1, attempts + 1):
        try:
            from confluent_kafka.admin import AdminClient, NewTopic
            admin = AdminClient({"bootstrap.servers": bootstrap or config.KAFKA_BOOTSTRAP_SERVERS})
            topics = [NewTopic(name, num_partitions=parts, replication_factor=1,
                               config={"retention.ms": str(days * 86_400_000)}) for name, (parts, days) in TOPIC_SPECS.items()]
            for name, future in admin.create_topics(topics).items():
                try:
                    future.result(timeout)
                except Exception as error:
                    if "TOPIC_ALREADY_EXISTS" not in str(error):
                        raise
            return True
        except Exception as error:
            log.warning("Kafka недоступна при проверке топиков (попытка %s/%s): %s", attempt, attempts, error)
            if attempt < attempts:
                sleep(2.0 * attempt)
    log.error("Kafka недоступна: сервис запущен, события будут накапливаться в outbox")
    return False
