import json
import sys
import time
import urllib.error
import urllib.request
import uuid

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/graphql"


CORRELATION = {"id": "demo"}


def gql(query: str, variables: dict = None, token: str = None) -> dict:
    headers = {"Content-Type": "application/json", "X-Correlation-ID": CORRELATION["id"]}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(URL, json.dumps({"query": query, "variables": variables or {}}).encode(), headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.load(response)
    except urllib.error.URLError as error:
        sys.exit(f"Gateway недоступен ({error}). Запущены ли сервисы: python scripts/run_all.py start ?")
    if body.get("errors"):
        raise RuntimeError(body["errors"][0]["message"])
    return body["data"]


def login(email: str) -> tuple:
    data = gql("mutation($i: LoginInput!){ login(input:$i){ token user{ id name role } } }",
               {"i": {"email": email, "password": "password123"}})["login"]
    return data["token"], data["user"]


def wait_for(description: str, probe, timeout: float = 20.0):
    started = time.time()
    while time.time() - started < timeout:
        value = probe()
        if value:
            print(f"    ✓ {description} (через {time.time() - started:.1f} с)")
            return value
        time.sleep(0.3)
    sys.exit(f"    ✗ Не дождались: {description}. Проверьте, что Kafka и все сервисы запущены.")


def step(text: str) -> None:
    CORRELATION["id"] = f"demo-{uuid.uuid4().hex[:8]}"
    print(f"\n▶ {text}\n    correlation_id = {CORRELATION['id']}   (python scripts/trace.py {CORRELATION['id']})")


def main() -> None:
    DISEASE = str(uuid.uuid5(uuid.NAMESPACE_URL, "plant-detective/dis-1"))
    client_token, client = login("petr@example.com")
    expert_token, expert = login("ivan.expert@example.com")
    admin_token, admin = login("admin@example.com")
    print(f"Клиент: {client['name']}, эксперт: {expert['name']}, администратор: {admin['name']}")

    step("1. Клиент создаёт заявку (gRPC Gateway→Request, Request→Auth; событие RequestCreated)")
    request = gql("mutation($i: CreateRequestInput!){ createRequest(input:$i){ id status aiPrediagnosis } }",
                  {"i": {"symptoms": "Белый налёт на листьях томата, листья скручиваются", "photoUrls": []}},
                  client_token)["createRequest"]
    request_id = request["id"]
    print(f"    заявка {request_id}: {request['status']}, AI-преддиагностика: {request['aiPrediagnosis']}")
    wait_for("Notification Service создал уведомление «Заявка создана» (по событию RequestCreated)",
             lambda: [n for n in gql("{ notifications { type } }", token=client_token)["notifications"]
                      if n["type"] == "REQUEST_CREATED"])

    step("2. Эксперт откликается (gRPC Expert→Request; событие ExpertResponseCreated)")
    gql("mutation($i: RespondToRequestInput!){ respondToRequest(input:$i){ id status } }",
        {"i": {"requestId": request_id, "comment": "Похоже на мучнистую росу, готов помочь"}}, expert_token)

    step("3. Клиент выбирает эксперта (gRPC Request→Expert; событие ExpertSelected → Expert принимает отклик)")
    selected = gql("mutation($r: ID!, $e: ID!){ selectExpert(requestId:$r, expertId:$e){ status } }",
                   {"r": request_id, "e": expert["id"]}, client_token)["selectExpert"]
    print(f"    статус заявки: {selected['status']}")

    step("4. Клиент оплачивает (gRPC Payment→Request; событие PaymentCompleted → Request, Chat, Notification, Analytics)")
    payment = gql("mutation($i: CreatePaymentInput!){ createPayment(input:$i){ id amount status } }",
                  {"i": {"requestId": request_id, "idempotencyKey": f"demo-{uuid.uuid4()}"}}, client_token)["createPayment"]
    print(f"    платёж {payment['id']}: {payment['amount']} ({payment['status']})")
    wait_for("Request Service перевёл заявку в IN_PROGRESS",
             lambda: gql("query($i: ID!){ request(id:$i){ status } }", {"i": request_id}, client_token)["request"]["status"] == "IN_PROGRESS")
    room = wait_for("Chat Service открыл чат",
                    lambda: gql("query($i: ID!){ chatRoomByRequest(requestId:$i){ id status } }",
                                {"i": request_id}, client_token)["chatRoomByRequest"])
    print(f"    чат {room['id']}: {room['status']}")

    step("5. Эксперт ставит диагноз (событие DiagnosisCreated → Recovery создаёт трекер → TrackerCreated)")
    gql("mutation($i: CreateDiagnosisInput!){ createDiagnosis(input:$i){ id } }",
        {"i": {"requestId": request_id, "diseaseId": DISEASE, "description": "Мучнистая роса, нужна обработка фунгицидом",
               "durationDays": 7, "checklist": [{"step": "Удалить поражённые листья"},
                                                {"step": "Обработать фунгицидом", "frequency": "раз в 3 дня"}]}},
        expert_token)
    tracker = wait_for("Recovery Service создал трекер выздоровления",
                       lambda: gql("query($i: ID!){ trackerByRequest(requestId:$i){ id status } }",
                                   {"i": request_id}, client_token)["trackerByRequest"])
    print(f"    трекер {tracker['id']}: {tracker['status']}")

    step("6. Эксперт корректирует лечение (gRPC Recovery→Notification: SendNotification)")
    gql("mutation($t: ID!, $i: UpdateTreatmentInput!){ updateTreatment(trackerId:$t, input:$i){ id } }",
        {"t": tracker["id"], "i": {"changeDescription": "Повторить обработку через 3 дня", "newStage": "Лечение"}},
        expert_token)
    wait_for("клиент получил уведомление TREATMENT_UPDATED",
             lambda: [n for n in gql("{ notifications { type } }", token=client_token)["notifications"]
                      if n["type"] == "TREATMENT_UPDATED"])

    step("7. Эксперт завершает лечение (событие TrackerCompleted → Request Service закрывает заявку)")
    gql("mutation($t: ID!){ completeTracker(trackerId:$t){ status } }", {"t": tracker["id"]}, expert_token)
    wait_for("заявка переведена в DONE",
             lambda: gql("query($i: ID!){ request(id:$i){ status } }", {"i": request_id}, client_token)["request"]["status"] == "DONE")

    step("8. Аналитика обновилась по событиям (Analytics Service)")
    stats = wait_for("статистика эксперта учла завершённую заявку",
                     lambda: gql("query($e: ID!){ expertStats(expertId:$e){ totalRequests completedRequests } }",
                                 {"e": expert["id"]}, admin_token)["expertStats"])
    print(f"    всего заявок: {stats['totalRequests']}, завершено: {stats['completedRequests']}")

    step("9. Администратор блокирует пользователя: сессии завершаются сразу (gRPC Admin→Auth)")
    email = f"demo-{uuid.uuid4().hex[:8]}@example.com"
    gql("mutation($i: RegisterInput!){ register(input:$i){ user{ id } } }",
        {"i": {"email": email, "password": "password123", "name": "Демо Пользователь"}})
    victim_token, victim = login(email)
    gql("mutation($u: ID!){ blockUser(userId:$u){ id status } }", {"u": victim["id"]}, admin_token)
    try:
        gql("{ me { id } }", token=victim_token)
        sys.exit("    ✗ Токен заблокированного пользователя всё ещё принимается")
    except RuntimeError as error:
        print(f"    ✓ токен заблокированного пользователя отклонён: {error}")

    print("\nСценарий выполнен: все шаги прошли через gRPC и Kafka.")


if __name__ == "__main__":
    main()
