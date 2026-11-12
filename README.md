# Детектив для растений — ЛР №6: межсервисное взаимодействие (gRPC и Kafka)

Продолжение ЛР1–ЛР5. **Каждый микросервис — отдельный проект** (своя папка, `requirements.txt`, конфигурация, тесты, БД);
10 сервисов + GraphQL Gateway. Сервисы не импортируют друг друга и не обращаются к чужим БД: они общаются только по
**gRPC** (синхронные вызовы) и **Kafka** (события). Mock-заглушки удалены из рабочего кода.

```
Клиент ─ GraphQL ─► Gateway ─ gRPC ─► 10 сервисов ◄─ gRPC ─► друг друга
                                        │   ▲
                         outbox → Kafka ┘   └ consumer (идемпотентный)
```

## Структура

```
plant-detective/
├── proto/                    # protobuf-контракты (10 файлов) — единый источник истины (развитие ЛР2)
├── docker-compose.yml        # 10 × PostgreSQL, Redis, Kafka (KRaft), MinIO
├── scripts/
│   ├── gen_proto.py          # генерация *_pb2*.py в app/proto/ каждого проекта
│   ├── run_all.py            # gen | init | test | start
│   └── demo_scenario.py      # сквозной бизнес-сценарий через GraphQL
├── gateway/                  # GraphQL API: gRPC-клиенты 10 сервисов (app/clients/grpc_clients.py)
└── services/<имя>-service/
    └── app/ config, models, schemas, repository, service        # слои из ЛР4–ЛР5 (бизнес-логика не менялась)
            grpc_server.py   # gRPC-сервер (servicer-адаптер к service.py)
            grpc_support.py  # protobuf↔DTO, статусы ошибок, ключ API, канал клиента (deadline, retry, circuit breaker)
            clients.py       # gRPC-клиенты соседних сервисов
            events.py        # конверт события, outbox, Kafka producer/consumer, DLQ
            handlers.py      # обработчики входящих событий
            main.py          # самостоятельное приложение: gRPC-сервер + relay + consumer
```

## Быстрый запуск

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python scripts/run_all.py test        # тесты, Docker не нужен (тесты gRPC после gen пропускаются без кода protobuf)
python scripts/run_all.py gen         # 1) сгенерировать код protobuf/gRPC (один раз и после правки proto/)

docker compose up -d                  # 2) PostgreSQL ×10, Redis, Kafka, MinIO
python scripts/run_all.py init        # 3) таблицы и тестовые данные
python scripts/run_all.py start       # 4) все сервисы + Gateway отдельными процессами (Ctrl+C — остановка)
python scripts/demo_scenario.py       # 5) сквозной сценарий (в другом терминале)
```

GraphiQL: <http://localhost:8000/graphql>. Состояние сервисов: <http://localhost:8000/health/services>.
Любой сервис запускается и отдельно: `cd services/request-service && python -m app.main` (работает, пока не остановлен).
Пользователи из seed (пароль `password123`): `anna@example.com` (клиент), `petr@example.com` (клиент),
`ivan.expert@example.com` (эксперт), `admin@example.com` (админ).

Порты gRPC: auth 50051, request 50052, expert 50053, recovery 50054, chat 50055, payment 50056, notification 50057,
analytics 50058, admin 50059, satellite 50060. Gateway — 8000. Auth Service дополнительно сохраняет REST API (8001) из ЛР5.

## gRPC: кто кого вызывает (синхронно)

| Вызывающий → вызываемый | Методы | Где в сценарии |
|---|---|---|
| Gateway → все 10 сервисов | все RPC из `proto/*.proto` | каждый GraphQL-запрос; JWT проверяет `Auth.VerifyToken` |
| Request → Auth | `GetUser` | создание заявки, проверка роли и статуса |
| Request → Expert | `ListResponses` | клиент выбирает эксперта, который откликался |
| Expert → Auth | `GetUser` | проверка роли эксперта |
| Expert → Request | `GetRequestDetails`, `GetDisease` | отклик и диагноз (статус и владелец заявки) |
| Payment → Auth, Request | `GetUser`, `GetRequest` | оплата заявки |
| Recovery → Notification | `SendNotification` | корректировка лечения |
| Admin → Auth | `GetUser`, `AssignRole`, `SetUserStatus` | верификация эксперта и блокировка (действуют сразу) |

Безопасность и надёжность вызовов (`grpc_support.py`): ключ внутреннего API в метаданных (`x-internal-key`); срок ожидания
на каждый вызов; повторы **только** для чтения при `UNAVAILABLE/DEADLINE_EXCEEDED`; предохранитель (circuit breaker);
коды gRPC ↔ ошибки домена (`NOT_FOUND`↔`NotFoundError`, `FAILED_PRECONDITION`↔`BusinessRuleError`, …, недоступность →
`ServiceUnavailableError`/`SERVICE_UNAVAILABLE` в GraphQL); стандартный `grpc.health.v1`.

## Kafka: события (формат из ЛР2: `event_id, event_type, timestamp, payload`)

| Событие (топик) | Публикует | Обрабатывают → действие |
|---|---|---|
| `UserRegistered` (auth.events) | Auth | Notification (приветствие), Analytics |
| `RequestCreated` (request.events) | Request | Notification, Analytics |
| `ExpertSelected` (request.events) | Request | **Expert** (отклик → ACCEPTED, остальные REJECTED), Notification, Analytics |
| `ExpertResponseCreated` (expert.events) | Expert | Notification, Analytics |
| `DiagnosisCreated` (expert.events) | Expert | **Recovery** (создаёт трекер), Notification, Analytics |
| `PaymentCompleted` (payment.events) | Payment | **Request** (PENDING→IN_PROGRESS), **Chat** (открывает чат), Notification, Analytics |
| `TrackerCreated` (recovery.events) | Recovery | Notification, Analytics |
| `PhotoUploaded` (recovery.events) | Recovery | Notification (эксперту) |
| `TrackerCompleted` (recovery.events) | Recovery | **Request** (IN_PROGRESS→DONE), Notification, Analytics (completed_requests) |
| `TreatmentUpdated` (recovery.events) | Recovery | — (клиента уведомляет gRPC `SendNotification`) |
| `MessageSent` (chat.events) | Chat | Notification (получателю) |
| `WithdrawalRequested/Approved` (payment.events) | Payment | Notification (эксперту) |
| `ExpertVerified`, `UserBlocked` (admin.events) | Admin | **Auth** (роль EXPERT / блокировка + завершение сессий), Notification |
| `SatelliteAlertCreated` (satellite.events) | Satellite | Notification (владельцу поля), Analytics |

Надёжность доставки:
* **Transactional outbox** — событие пишется в таблицу `outbox_events` в одной транзакции с изменением данных; фоновый
  `OutboxRelay` отправляет его в Kafka (`acks=all`, идемпотентный producer). Kafka недоступна — бизнес-операция всё равно
  успешна, события доставятся позже, порядок сохраняется.
* **Consumer**: ручная фиксация смещений (at-least-once), таблица `processed_events` исключает повторную обработку,
  временные сбои повторяются, «ядовитые» сообщения уходят в `dead-letter.events`. Для Notification и Analytics запись
  результата и отметка «обработано» — одна транзакция.
* Ключ партиции — `request_id`/`user_id`: события одной заявки читаются по порядку.
* Следствие: переходы по событиям происходят с небольшой задержкой (десятки–сотни миллисекунд) — согласованность в конечном счёте.

## Что исправлено по замечаниям к ЛР5

1. **Интеграция Gateway с Auth Service и Redis.** `GATEWAY_AUTH_MODE` и mock-режим удалены: Gateway всегда проверяет JWT через
   `Auth.VerifyToken` (подпись, срок, сессия в Redis, статус пользователя). Локальных сессий в памяти Gateway нет.
2. **Идентификаторы пользователей.** Mock-данные `user-1…` убраны из рабочего кода; Gateway работает с теми же UUID, что и сервисы.
3. **`verifyExpert` / `blockUser`.** Admin Service вызывает `Auth.AssignRole` / `Auth.SetUserStatus` (роль и статус меняются сразу,
   при блокировке `revoke_user_sessions` завершает все сессии в Redis) и публикует `ExpertVerified` / `UserBlocked`; Auth
   дополнительно применяет событие (идемпотентно), поэтому роль будет выдана, даже если Auth был недоступен в момент команды.
4. **Независимый запуск сервисов.** `python -m app.main` в каждом сервисе запускает gRPC-сервер, Kafka-relay и consumer и
   работает до остановки (`--init-only` — только БД и seed). `scripts/run_all.py start` запускает всё сразу.

## Что заменено вместо mock-заглушек

| Было (ЛР5) | Стало (ЛР6) |
|---|---|
| `Mock*Client` в Gateway (дублировали бизнес-правила) | `GrpcXxxClient` → gRPC-серверы сервисов (правила только в сервисах) |
| `Mock*Client` внутри сервисов | gRPC-клиенты (`app/clients.py`); двойники — только в `tests/fakes.py` |
| `start_work`, `open_room`, `create_tracker`, `accept_response`, `complete_request` как прямые вызовы | события `PaymentCompleted`, `DiagnosisCreated`, `ExpertSelected`, `TrackerCompleted` |
| `MockStorageClient` | MinIO (`app/storage.py`) |
| `MockAiClient` | `KeywordAiClassifier` — локальные правила по ключевым словам (не заглушка внешнего вызова) |

Осталось не интеграцией сервисов, а внешней системой: платёжный провайдер не подключён, платёж считается успешным.

## Отличия от контрактов ЛР2 (и почему)

* Контракты расширены методами, которые нужны Gateway (фильтры, сводки, `AddPhoto`, `GetTrackerByRequest`, чтение чата и т.д.),
  и ролью вызывающего (`actor_role`, проверенная Gateway по JWT). Новые файлы: `analytics.proto`, `satellite.proto`.
* `Register` возвращает пользователя (вход выполняется отдельно, как в ЛР5); `ChargeExpert` заменён событием `PaymentCompleted`
  (баланс считает Payment Service); «нет трекера/чата по заявке» — `found=false`, а не ошибка.
* Recovery → Notification оставлен по gRPC (как в ЛР2), поэтому `TreatmentUpdated` Notification не читает (иначе дубли).
* Новые таблицы: `outbox_events`, `processed_events` (во всех сервисах), `event_counters` (Analytics).

## Тесты

`python scripts/run_all.py test`: тесты бизнес-логики и событий (SQLite в памяти, Kafka/gRPC не нужны) — `tests/test_service.py`,
`tests/test_events.py`; тесты gRPC (`tests/test_grpc.py`, поднимают настоящий gRPC-сервер на localhost) выполняются после
`run_all.py gen` и пропускаются без сгенерированного кода. Gateway: GraphQL-тесты на двойниках сервисов (`tests/fakes`),
тесты gRPC-клиентов и обработки ошибок.
