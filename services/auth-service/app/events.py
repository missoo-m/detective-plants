import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from . import config
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
    return {"event_id": str(uuid.uuid4()), "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "payload": payload}


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

    def __init__(self, session_factory: Callable, producer, interval: Optional[float] = None, batch_size: int = 50):
        super().__init__(target=self.run, name="outbox-relay", daemon=True)
        self._session_factory, self._producer = session_factory, producer
        self._interval = interval if interval is not None else config.OUTBOX_POLL_SECONDS
        self._batch, self._stop_flag = batch_size, threading.Event()

    def flush_once(self) -> int:
        from sqlalchemy import select
        from .models import OutboxEvent
        sent = 0
        with self._session_factory() as session:
            rows = session.scalars(select(OutboxEvent).where(OutboxEvent.published_at.is_(None))
                                   .order_by(OutboxEvent.seq).limit(self._batch)
                                   .with_for_update(skip_locked=True)).all()
            for row in rows:
                try:
                    self._producer.send(row.topic, row.event_key, row.body)
                except Exception as error:               
                    row.attempts = (row.attempts or 0) + 1
                    log.warning("Событие %s (%s) не отправлено, попытка %s: %s", row.event_type, row.event_id,
                                row.attempts, error)
                    break
                row.published_at = datetime.now(timezone.utc).replace(tzinfo=None)
                sent += 1
            session.commit()
        return sent

    def run(self) -> None:
        while not self._stop_flag.is_set():
            try:
                if self.flush_once() == 0:
                    self._stop_flag.wait(self._interval)
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
                 poll_timeout: float = 1.0, sleep: Callable[[float], None] = time.sleep):
        super().__init__(target=self.run, name="event-consumer", daemon=True)
        self._session_factory, self._handlers = session_factory, handlers
        self._group = group_id or config.KAFKA_GROUP_ID
        self._bootstrap_servers = bootstrap or config.KAFKA_BOOTSTRAP_SERVERS
        self._consumer, self._dlq = consumer, dead_letter_producer
        self._max_attempts, self._poll, self._sleep = max_attempts, poll_timeout, sleep
        self._stop_flag = threading.Event()
        self.topics = sorted({TOPIC_OF[t] for t in handlers})

    def process(self, raw) -> str:
        from .models import ProcessedEvent
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
        with self._session_factory() as session:
            if session.get(ProcessedEvent, event_id) is not None:
                log.info("Событие %s уже обработано, пропуск", event_id)
                return "duplicate"
        for attempt in range(1, self._max_attempts + 1):
            with self._session_factory() as session:
                try:
                    handler(event, session)
                    session.add(ProcessedEvent(event_id=event_id, event_type=event_type))
                    session.commit()
                    return "handled"
                except PERMANENT_ERRORS as error:        
                    session.rollback()
                    log.error("Событие %s (%s) отклонено: %s", event_type, event_id, error)
                    self._dead_letter(text, f"{type(error).__name__}: {error}")
                    self._mark_processed(event_id, event_type)
                    return "rejected"
                except Exception as error:               
                    session.rollback()
                    log.warning("Событие %s (%s): попытка %s/%s не удалась: %s", event_type, event_id, attempt,
                                self._max_attempts, error)
            if attempt < self._max_attempts:
                self._sleep(0.5 * attempt)
        self._dead_letter(text, "превышено число попыток обработки")
        return "failed"

    def _mark_processed(self, event_id: str, event_type: str) -> None:
        from .models import ProcessedEvent
        try:
            with self._session_factory() as session:
                session.add(ProcessedEvent(event_id=event_id, event_type=event_type))
                session.commit()
        except Exception:
            log.exception("Не удалось пометить событие %s обработанным", event_id)

    def _dead_letter(self, text: str, reason: str) -> None:
        if self._dlq is None:
            return
        try:
            self._dlq.send(DEAD_LETTER_TOPIC, None, json.dumps(
                {"service": config.SERVICE_NAME, "reason": reason, "message": text}, ensure_ascii=False))
        except Exception:
            log.exception("Не удалось отправить сообщение в %s", DEAD_LETTER_TOPIC)

    def run(self) -> None:
        consumer = self._consumer
        if consumer is None:
            from confluent_kafka import Consumer
            consumer = Consumer({"bootstrap.servers": self._bootstrap_servers, "group.id": self._group,
                                 "enable.auto.commit": False, "auto.offset.reset": "earliest",
                                 "allow.auto.create.topics": True})
        consumer.subscribe(self.topics)
        log.info("Потребитель %s подписан на %s", self._group, ", ".join(self.topics))
        try:
            while not self._stop_flag.is_set():
                message = consumer.poll(self._poll)
                if message is None:
                    continue
                if message.error():
                    log.warning("Ошибка Kafka: %s", message.error())
                    continue
                try:
                    self.process(message.value())
                    consumer.commit(message=message, asynchronous=False)
                except Exception:
                    log.exception("Сбой обработки сообщения, смещение не зафиксировано")
                    self._stop_flag.wait(1.0)
        finally:
            consumer.close()

    def stop(self) -> None:
        self._stop_flag.set()


def ensure_topics(bootstrap: Optional[str] = None, timeout: float = 10.0) -> None:
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
                    log.warning("Топик %s не создан: %s", name, error)
    except Exception as error:
        log.warning("Не удалось проверить топики Kafka (брокер недоступен?): %s", error)
