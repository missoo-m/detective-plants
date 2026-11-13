import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = os.getenv("GATEWAY_URL", "http://localhost:8000/graphql")
PORTS = {"auth": 50051, "request": 50052, "expert": 50053, "recovery": 50054, "chat": 50055, "payment": 50056,
         "notification": 50057, "analytics": 50058, "admin": 50059, "satellite": 50060}
results = []


def gql(query, variables=None, token=None, timeout=30):
    headers = {"Content-Type": "application/json", "X-Correlation-ID": f"chk-{uuid.uuid4().hex[:8]}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(URL, json.dumps({"query": query, "variables": variables or {}}).encode(), headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def data(query, variables=None, token=None):
    body = gql(query, variables, token)
    if body.get("errors"):
        raise RuntimeError(body["errors"][0].get("extensions", {}).get("code", "") + ": " + body["errors"][0]["message"])
    return body["data"]


def login(email):
    return data("mutation($i: LoginInput!){ login(input:$i){ token user{ id } } }",
                {"i": {"email": email, "password": "password123"}})["login"]


def sql(service, query):
    out = subprocess.run(["docker", "exec", f"pd-postgres-{service}", "psql", "-U", service, "-d", f"{service}_db", "-tAc", query],
                         capture_output=True, text=True)
    return out.stdout.strip()


def wait(description, probe, timeout=60.0, step=1.0):
    started = time.time()
    while time.time() - started < timeout:
        value = probe()
        if value:
            return value
        time.sleep(step)
    return None


def check(name, ok, detail=""):
    results.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


def stop_service(name):
    pids = subprocess.run(["lsof", "-ti", f"tcp:{PORTS[name]}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()
    for pid in pids:
        os.kill(int(pid), signal.SIGTERM)
    time.sleep(2)
    print(f"  · {name}-service остановлен")


def start_service(name):
    env = dict(os.environ, LOG_DIR=str(ROOT / "logs"), PYTHONUNBUFFERED="1")
    subprocess.Popen([sys.executable, "-m", "app.main"], cwd=ROOT / "services" / f"{name}-service", env=env,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    wait(f"{name} gRPC", lambda: subprocess.run(["lsof", "-ti", f"tcp:{PORTS[name]}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout.strip(), 40)
    print(f"  · {name}-service запущен")


def new_request(token):
    return data("mutation($i: CreateRequestInput!){ createRequest(input:$i){ id } }",
                {"i": {"symptoms": f"Проверка устойчивости {uuid.uuid4().hex[:6]}: белый налёт", "photoUrls": []}}, token)["createRequest"]["id"]


def notifications(token, kind):
    return len([n for n in data("{ notifications { type } }", token=token)["notifications"] if n["type"] == kind])


def experiment_kafka():
    print("\n1. Отказ Kafka: событие не теряется (outbox)")
    client = login("petr@example.com")["token"]
    before = notifications(client, "REQUEST_CREATED")
    subprocess.run(["docker", "compose", "stop", "kafka"], cwd=ROOT, capture_output=True)
    try:
        request_id = new_request(client)
        check("заявка создана при недоступной Kafka", True, request_id)
        pending = wait("outbox", lambda: sql("request", "select count(*) from outbox_events where published_at is null") not in ("", "0"), 10)
        check("событие осталось в outbox_events (published_at пусто)", bool(pending))
    finally:
        subprocess.run(["docker", "compose", "start", "kafka"], cwd=ROOT, capture_output=True)
    print("  · Kafka запускается, ждём доставку (до 120 с)...")
    done = wait("доставка", lambda: sql("request", "select count(*) from outbox_events where published_at is null") == "0", 120, 2)
    check("после запуска Kafka outbox очищен — событие доставлено", bool(done))
    got = wait("уведомление", lambda: notifications(client, "REQUEST_CREATED") > before, 60)
    check("потребитель Notification обработал событие", bool(got))


def experiment_notification():
    print("\n2. Отказ Notification Service: основные операции продолжаются")
    expert = login("ivan.expert@example.com")["token"]
    client = login("petr@example.com")["token"]
    before = notifications(client, "REQUEST_CREATED")
    tracker = str(uuid.uuid5(uuid.NAMESPACE_URL, "plant-detective/track-1"))
    stop_service("notification")
    try:
        started = time.time()
        try:
            data("mutation($t: ID!, $i: UpdateTreatmentInput!){ updateTreatment(trackerId:$t, input:$i){ id } }",
                 {"t": tracker, "i": {"changeDescription": "Проверка устойчивости: повторить обработку"}}, expert)
            check("updateTreatment выполнен без Notification Service (синхронный gRPC недоступен)", True, f"{time.time() - started:.1f} с")
        except RuntimeError as error:
            check("updateTreatment выполнен без Notification Service", False, str(error))
        new_request(client)
        check("createRequest выполнен (событие ждёт в Kafka)", True)
    finally:
        start_service("notification")
    got = wait("уведомление", lambda: notifications(client, "REQUEST_CREATED") > before, 60)
    check("после запуска Notification накопленное событие обработано", bool(got))


def experiment_auth():
    print("\n3. Отказ Auth Service: SERVICE_UNAVAILABLE и предохранитель")
    client = login("petr@example.com")["token"]
    stop_service("auth")
    try:
        times, codes = [], []
        for _ in range(8):
            started = time.time()
            body = gql("{ me { id } }", token=client)
            times.append(time.time() - started)
            codes.append((body.get("errors") or [{}])[0].get("extensions", {}).get("code"))
        check("Gateway отвечает кодом SERVICE_UNAVAILABLE", set(codes) == {"SERVICE_UNAVAILABLE"}, str(set(codes)))
        check("предохранитель: последние ответы быстрее первых", max(times[-3:]) < max(times[:3]) or max(times) < 1.0,
              f"первые {times[0]:.2f} с, последние {times[-1]:.2f} с")
    finally:
        start_service("auth")
    time.sleep(12)
    ok = wait("me", lambda: gql("{ me { id } }", token=client).get("data", {}).get("me"), 30)
    check("после запуска Auth Service запросы снова работают", bool(ok))


def experiment_request():
    print("\n4. Отказ Request Service при оплате: платёж не создаётся, повтор проходит")
    client = login("petr@example.com")
    expert = login("ivan.expert@example.com")
    request_id = new_request(client["token"])
    data("mutation($i: RespondToRequestInput!){ respondToRequest(input:$i){ id } }", {"i": {"requestId": request_id, "comment": "готов"}}, expert["token"])
    data("mutation($r: ID!, $e: ID!){ selectExpert(requestId:$r, expertId:$e){ status } }", {"r": request_id, "e": expert["user"]["id"]}, client["token"])
    stop_service("request")
    key = f"chk-{uuid.uuid4()}"
    try:
        body = gql("mutation($i: CreatePaymentInput!){ createPayment(input:$i){ id } }",
                   {"i": {"requestId": request_id, "idempotencyKey": key}}, client["token"])
        code = (body.get("errors") or [{}])[0].get("extensions", {}).get("code")
        check("createPayment вернул SERVICE_UNAVAILABLE", code == "SERVICE_UNAVAILABLE", str(code))
        count = sql("payment", f"select count(*) from transactions where request_id = '{request_id}'")
        check("платёж не создан (состояние не нарушено)", count == "0", f"транзакций: {count}")
    finally:
        start_service("request")
    time.sleep(12)
    body = wait("оплата", lambda: (lambda b: b if not b.get("errors") else None)(gql(
        "mutation($i: CreatePaymentInput!){ createPayment(input:$i){ id status } }", {"i": {"requestId": request_id, "idempotencyKey": key}}, client["token"])), 40, 3)
    check("повторный вызов после запуска Request Service прошёл", bool(body))
    status = wait("статус", lambda: data("query($i: ID!){ request(id:$i){ status } }", {"i": request_id}, client["token"])["request"]["status"] == "IN_PROGRESS", 40)
    check("заявка переведена в IN_PROGRESS по событию PaymentCompleted", bool(status))


def experiment_cache():
    print("\n5. Кеш Redis: данные в кеше и сброс при блокировке")
    admin = login("admin@example.com")["token"]
    email = f"cache-{uuid.uuid4().hex[:8]}@example.com"
    data("mutation($i: RegisterInput!){ register(input:$i){ user{ id } } }", {"i": {"email": email, "password": "password123", "name": "Кеш Проверка"}})
    user = login(email)
    for _ in range(3):
        data("{ me { id } }", token=user["token"])
    redis = lambda *args: subprocess.run(["docker", "exec", "pd-redis", "redis-cli", "-n", "1", *args], capture_output=True, text=True).stdout.strip()
    key = f"pd:auth-service:user:{user['user']['id']}"
    check("карточка пользователя находится в Redis", redis("exists", key) == "1", f"TTL {redis('ttl', key)} с")
    stats = json.load(urllib.request.urlopen(URL.replace("/graphql", "/health/cache")))
    print(f"  · кеш Gateway: {stats}")
    data("mutation($u: ID!){ blockUser(userId:$u){ id status } }", {"u": user["user"]["id"]}, admin)
    check("после блокировки запись в кеше удалена", redis("exists", key) == "0")
    body = gql("{ me { id } }", token=user["token"])
    check("токен заблокированного пользователя отклонён сразу", bool(body.get("errors")))


EXPERIMENTS = {"kafka": experiment_kafka, "notification": experiment_notification, "auth": experiment_auth,
               "request": experiment_request, "cache": experiment_cache}


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which != "all" and which not in EXPERIMENTS:
        print("python scripts/check_resilience.py [kafka|notification|auth|request|cache|all]")
        return 2
    for tool in ("docker", "lsof"):
        if shutil.which(tool) is None:
            print(f"Нужна утилита {tool} (macOS/Linux)")
            return 2
    for name, run in EXPERIMENTS.items():
        if which in ("all", name):
            run()
    print(f"\nИтог: {sum(results)} из {len(results)} проверок пройдено")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
