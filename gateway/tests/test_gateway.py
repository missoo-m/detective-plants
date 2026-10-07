#Тесты GraphQL API (Query, Mutation, фильтры, сортировка, агрегаты) на mock-клиентах
import io

from app import clients
from app.mutations import read_upload
from app.schema import schema


def run(query: str, user: str = "user-1", variables=None):
    return schema.execute_sync(query, variable_values=variables, context_value={"current_user_id": user})


def ok(query: str, user: str = "user-1", variables=None) -> dict:
    result = run(query, user, variables)
    assert result.errors is None, result.errors
    return result.data


def fails(query: str, code: str, user: str = "user-1", variables=None) -> str:
    result = run(query, user, variables)
    assert result.errors, "ожидалась ошибка"
    assert result.errors[0].extensions["code"] == code, result.errors[0]
    return result.errors[0].message


def test_me_and_related_data():
    assert ok("{ me { name role status } }")["me"] == {"name": "Анна Петрова", "role": "CLIENT", "status": "ACTIVE"}
    data = ok('''{ request(id: "req-2") { status client { name } expert { name } responses { status }
                   diagnosis { description disease { name } checklist { step } } } }''')["request"]
    assert data["expert"]["name"] == "Иван Сидоров" and data["diagnosis"]["disease"]["name"] == "Мучнистая роса"
    assert len(data["diagnosis"]["checklist"]) == 2


def test_not_found_is_null_and_me_error():
    assert ok('{ request(id: "req-999") { id } user(id: "x") { id } }') == {"request": None, "user": None}
    fails("{ me { id } }", "NOT_FOUND", user="ghost")


def test_requests_filter_sort_paging():
    q = '''{ myRequests(filter: {statuses: [CREATED, CANCELLED]}, sort: {field: CREATED_AT, direction: DESC}) { id status } }'''
    assert [r["id"] for r in ok(q)["myRequests"]] == ["req-1", "req-5"]
    assert [r["id"] for r in ok('{ myRequests(filter: {search: "налёт"}) { id } }')["myRequests"]] == ["req-2"]
    period = '{ myRequests(filter: {createdFrom: "2026-01-15", createdTo: "2026-01-16"}) { id } }'
    assert [r["id"] for r in ok(period)["myRequests"]] == ["req-1", "req-2"]
    assert [r["id"] for r in ok("{ availableRequests(sort: {direction: DESC}) { id } }")["availableRequests"]] == ["req-3", "req-1"]
    assert len(ok("{ myRequests(limit: 1, offset: 1) { id } }")["myRequests"]) == 1
    assert [r["id"] for r in ok("{ requestsByExpert(expertId: \"user-2\", filter: {statuses: [DONE]}) { id } }")["requestsByExpert"]] == ["req-4"]


def test_filter_errors():
    fails('{ myRequests(filter: {createdFrom: "2026-02-01", createdTo: "2026-01-01"}) { id } }', "BAD_USER_INPUT")
    fails('{ myRequests(filter: {createdFrom: "вчера"}) { id } }', "BAD_USER_INPUT")
    fails("{ availableRequests(limit: 0) { id } }", "BAD_USER_INPUT")
    assert run("{ users(filter: {role: SUPERUSER}) { id } }").errors


def test_users_filter_sort():
    names = ok("{ users(sort: {field: NAME, direction: DESC}) { name } }")["users"]
    assert names[0]["name"] == "Пётр Огородников"
    assert [u["id"] for u in ok("{ users(filter: {status: BLOCKED}) { id } }")["users"]] == ["user-5"]
    assert len(ok('{ users(filter: {search: "example.com"}, limit: 2, offset: 1) { id } }')["users"]) == 2


def test_transactions_filter_sort():
    q = '{ transactions(filter: {status: "SUCCESS"}, sort: {field: AMOUNT, direction: DESC}) { id amount } }'
    assert len(ok(q)["transactions"]) == 2
    assert ok("{ transactions(filter: {minAmount: 30}) { id } }")["transactions"] == []
    assert len(ok('{ transactions(filter: {userId: "user-4"}) { id request { symptoms } user { name } } }')["transactions"]) == 2
    fails('{ transactions(filter: {status: "BAD"}) { id } }', "BAD_USER_INPUT")


def test_aggregates():
    s = ok("{ requestsSummary { total byStatus { key count } } }")["requestsSummary"]
    assert s["total"] == 5 and {i["key"]: i["count"] for i in s["byStatus"]}["CREATED"] == 2
    t = ok("{ transactionsSummary { count totalAmount byStatus { key amount } } }")["transactionsSummary"]
    assert t["count"] == 3 and t["totalAmount"] == 75.0
    b = ok('{ expertBalance(expertId: "user-2") { earned commission pending available } }')["expertBalance"]
    assert b == {"earned": 50.0, "commission": 5.0, "pending": 30.0, "available": 15.0}
    assert ok("{ usersSummary { total byRole { key count } } }")["usersSummary"]["total"] == 5
    assert ok('{ trackerProgress(trackerId: "track-1") { photosCount updatesCount } }')["trackerProgress"] == {
        "photosCount": 1, "updatesCount": 1}
    assert ok('{ chatUnreadCount(chatRoomId: "chat-1") }', user="user-2")["chatUnreadCount"] == 1
    assert ok("{ notificationsSummary { total unread } }")["notificationsSummary"] == {"total": 2, "unread": 1}
    assert ok('{ fieldNdviSummary(fieldId: "fld-1") { count trend } }')["fieldNdviSummary"] == {"count": 2, "trend": -0.07}
    assert ok("{ platformSummary { completionRate } }")["platformSummary"]["completionRate"] == 75.0
    assert [e["expertId"] for e in ok("{ topExperts(sortBy: AVG_RATING) { expertId } }")["topExperts"]] == ["user-2", "user-6"]
    assert ok("{ applicationsSummary { total } }")["applicationsSummary"]["total"] == 2


def test_chat_access_control():
    fails('{ chatRoom(id: "chat-1") { id } }', "FORBIDDEN", user="user-4")
    assert ok('{ chatRoom(id: "chat-1") { messages { text } } }')["chatRoom"]["messages"]


def test_full_diagnosis_scenario():
    created = ok('''mutation { createRequest(input: {symptoms: "Белый налёт на листьях огурцов"}) { id status aiPrediagnosis } }''',
                 user="user-4")["createRequest"]
    rid = created["id"]
    assert created["status"] == "CREATED" and created["aiPrediagnosis"] == "Мучнистая роса"

    ok(f'mutation {{ respondToRequest(input: {{requestId: "{rid}", comment: "Готов помочь"}}) {{ status }} }}', user="user-2")
    fails(f'mutation {{ respondToRequest(input: {{requestId: "{rid}"}}) {{ id }} }}', "BUSINESS_RULE_VIOLATION", user="user-2")
    assert ok(f'mutation {{ selectExpert(requestId: "{rid}", expertId: "user-2") {{ status }} }}', user="user-4")["selectExpert"]["status"] == "PENDING"

    fails(f'mutation {{ createDiagnosis(input: {{requestId: "{rid}", diseaseId: "dis-1", description: "Мучнистая роса"}}) {{ id }} }}',
          "BUSINESS_RULE_VIOLATION", user="user-2")                         # до оплаты диагноз ставить нельзя
    pay = f'mutation {{ createPayment(input: {{requestId: "{rid}", idempotencyKey: "key-12345678"}}) {{ id amount status }} }}'
    first = ok(pay, user="user-4")["createPayment"]
    assert first["amount"] == 25.0 and ok(pay, user="user-4")["createPayment"]["id"] == first["id"]
    assert ok(f'{{ request(id: "{rid}") {{ status }} }}')["request"]["status"] == "IN_PROGRESS"

    diag = ok(f'''mutation {{ createDiagnosis(input: {{requestId: "{rid}", diseaseId: "dis-1",
                    description: "Мучнистая роса, нужна обработка", durationDays: 10,
                    checklist: [{{step: "Обработать фунгицидом", frequency: "раз в 5 дней"}}]}}) {{ id checklist {{ step }} }} }}''',
              user="user-2")["createDiagnosis"]
    assert len(diag["checklist"]) == 1
    tracker = ok(f'{{ trackerByRequest(requestId: "{rid}") {{ id status currentStage }} }}')["trackerByRequest"]
    assert tracker["status"] == "ACTIVE" and tracker["currentStage"] == "START"

    ok(f'mutation {{ updateTreatment(trackerId: "{tracker["id"]}", input: {{changeDescription: "Увеличить интервал", newStage: "Лечение"}}) {{ recordType }} }}', user="user-2")
    done = ok(f'mutation {{ completeTracker(trackerId: "{tracker["id"]}") {{ status }} }}', user="user-2")
    assert done["completeTracker"]["status"] == "COMPLETED"
    assert ok(f'{{ request(id: "{rid}") {{ status completedAt }} }}')["request"]["status"] == "DONE"


def test_request_rules():
    fails('mutation { createRequest(input: {symptoms: "коротко"}) { id } }', "BAD_USER_INPUT")
    fails('mutation { createRequest(input: {symptoms: "Эксперт не может создавать заявки"}) { id } }', "FORBIDDEN", user="user-2")
    fails('mutation { selectExpert(requestId: "req-1", expertId: "user-2") { id } }', "FORBIDDEN", user="user-4")
    assert ok('mutation { cancelRequest(requestId: "req-1") { status } }')["cancelRequest"]["status"] == "CANCELLED"
    fails('mutation { cancelRequest(requestId: "req-1") { id } }', "BUSINESS_RULE_VIOLATION")
    fails('mutation { cancelRequest(requestId: "req-2") { id } }', "BUSINESS_RULE_VIOLATION")      
    fails('mutation { cancelRequest(requestId: "req-999") { id } }', "NOT_FOUND")


def test_active_requests_limit():
    ok('mutation { createRequest(input: {symptoms: "Третья активная заявка клиента"}) { id } }')
    fails('mutation { createRequest(input: {symptoms: "Лишняя активная заявка"}) { id } }', "BUSINESS_RULE_VIOLATION")
    ok('mutation { cancelRequest(requestId: "req-1") { id } }')                       
    ok('mutation { createRequest(input: {symptoms: "Заявка вместо отменённой"}) { id } }')
    fails('mutation { createRequest(input: {symptoms: "Снова лишняя заявка"}) { id } }', "BUSINESS_RULE_VIOLATION")


def test_payment_rules_and_withdrawal():
    fails('mutation { createPayment(input: {requestId: "req-1", idempotencyKey: "key-12345678"}) { id } }', "BUSINESS_RULE_VIOLATION")
    fails('mutation { createPayment(input: {requestId: "req-1", idempotencyKey: "short"}) { id } }', "BAD_USER_INPUT")
    fails("mutation { requestWithdrawal(input: {amount: 5}) { id } }", "BAD_USER_INPUT", user="user-2")
    fails("mutation { requestWithdrawal(input: {amount: 40}) { id } }", "BUSINESS_RULE_VIOLATION", user="user-2")
    wd = ok("mutation { requestWithdrawal(input: {amount: 15}) { id status } }", user="user-2")["requestWithdrawal"]
    assert wd["status"] == "PENDING"
    fails(f'mutation {{ approveWithdrawal(withdrawalId: "{wd["id"]}") {{ id }} }}', "FORBIDDEN", user="user-2")
    assert ok(f'mutation {{ approveWithdrawal(withdrawalId: "{wd["id"]}") {{ status }} }}', user="user-3")["approveWithdrawal"]["status"] == "APPROVED"
    fails(f'mutation {{ approveWithdrawal(withdrawalId: "{wd["id"]}") {{ id }} }}', "BUSINESS_RULE_VIOLATION", user="user-3")


def test_chat_and_notifications():
    msg = ok('mutation { sendMessage(input: {chatRoomId: "chat-1", text: "Добрый день"}) { id isRead } }')["sendMessage"]
    fails('mutation { sendMessage(input: {chatRoomId: "chat-1", text: "Я посторонний"}) { id } }', "FORBIDDEN", user="user-4")
    fails('mutation { sendMessage(input: {chatRoomId: "chat-1", text: "  "}) { id } }', "BAD_USER_INPUT")
    fails(f'mutation {{ markMessageRead(messageId: "{msg["id"]}") {{ id }} }}', "BUSINESS_RULE_VIOLATION")      # автор
    assert ok(f'mutation {{ markMessageRead(messageId: "{msg["id"]}") {{ isRead }} }}', user="user-2")["markMessageRead"]["isRead"]
    assert ok('mutation { createVideoRoom(chatRoomId: "chat-1") { status } }', user="user-2")["createVideoRoom"]["status"] == "CREATED"
    fails('mutation { createVideoRoom(chatRoomId: "chat-1") { id } }', "BUSINESS_RULE_VIOLATION", user="user-2")
    assert ok('mutation { markNotificationRead(notificationId: "notif-1") { status } }')["markNotificationRead"]["status"] == "READ"
    fails('mutation { markNotificationRead(notificationId: "notif-3") { id } }', "FORBIDDEN")
    assert ok("mutation { markAllNotificationsRead }", user="user-2")["markAllNotificationsRead"] == 1


def test_register_login_profile():
    data = ok('mutation { register(input: {email: "New@Example.com", password: "strongpass1", name: "Новая Клиентка"}) { token user { role } } }')
    assert data["register"]["user"]["role"] == "CLIENT"
    fails('mutation { register(input: {email: "anna@example.com", password: "strongpass1", name: "Дубль Имя"}) { token } }', "BUSINESS_RULE_VIOLATION")
    fails('mutation { login(input: {email: "anna@example.com", password: "wrong"}) { token } }', "FORBIDDEN")
    assert ok('mutation { login(input: {email: "anna@example.com", password: "password123"}) { user { id } } }')["login"]["user"]["id"] == "user-1"
    assert ok('mutation { updateProfile(input: {language: "en"}) { language } }')["updateProfile"]["language"] == "en"
    fails('mutation { updateProfile(input: {language: "xx"}) { language } }', "BAD_USER_INPUT")


def test_expert_verification_and_blocking():
    app = ok('mutation { applyForExpert(input: {documentsUrl: "https://minio/docs/u1.pdf"}) { id status } }')["applyForExpert"]
    fails('mutation { applyForExpert(input: {documentsUrl: "https://minio/docs/u1.pdf"}) { id } }', "BUSINESS_RULE_VIOLATION")
    fails(f'mutation {{ verifyExpert(applicationId: "{app["id"]}", approve: true) {{ id }} }}', "FORBIDDEN")
    res = ok(f'mutation {{ verifyExpert(applicationId: "{app["id"]}", approve: true) {{ status }} }}', user="user-3")
    assert res["verifyExpert"]["status"] == "APPROVED"
    assert ok("{ me { role } }")["me"]["role"] == "EXPERT"
    assert ok('mutation { blockUser(userId: "user-4") { status } }', user="user-3")["blockUser"]["status"] == "BLOCKED"
    fails('mutation { blockUser(userId: "user-4") { id } }', "BUSINESS_RULE_VIOLATION", user="user-3")
    fails('mutation { blockUser(userId: "user-3") { id } }', "BUSINESS_RULE_VIOLATION", user="user-3")
    fails('mutation { createRequest(input: {symptoms: "Заблокированный пользователь"}) { id } }', "FORBIDDEN", user="user-4")


def test_create_field_and_upload_helper():
    sq = '{\\"type\\": \\"Polygon\\", \\"coordinates\\": [[[27.5, 53.9], [27.6, 53.9], [27.6, 54.0], [27.5, 54.0], [27.5, 53.9]]]}'
    assert ok(f'mutation {{ createField(input: {{name: "Моя делянка", geometry: "{sq}"}}) {{ name }} }}', user="user-4")
    fails(f'mutation {{ createField(input: {{name: "моя делянка", geometry: "{sq}"}}) {{ id }} }}', "BUSINESS_RULE_VIOLATION", user="user-4")
    fails('mutation { createField(input: {name: "Плохое", geometry: "not json"}) { id } }', "BAD_USER_INPUT", user="user-4")

    class FakeUpload:
        filename = "leaf.png"
        file = io.BytesIO(b"data")

    name, content = read_upload(FakeUpload())
    assert (name, content) == ("leaf.png", b"data")
    photo = clients.request_client.add_photo("req-1", "user-1", name, content)
    assert photo["url"].endswith("leaf.png")
    for bad in ("doc.pdf", ""):
        try:
            clients.request_client.add_photo("req-1", "user-1", bad or "x.png", b"" if not bad else b"1")
            assert False
        except Exception as exc:
            assert exc.extensions["code"] == "BAD_USER_INPUT"
