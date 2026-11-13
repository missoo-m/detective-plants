import base64
import json
from types import SimpleNamespace

from app import clients
from app.context import build_context
from app.errors import DomainError
from app.schema import schema
from app.security.identity import Identity
from app.security.permissions import access
from app.security.policy import AUTHENTICATED, POLICY, PUBLIC
from tests.helpers import ctx_for, token_for


def execute(query, token=None, user=None):
    return schema.execute_sync(query, context_value=ctx_for(user, token))


def code_of(result):
    assert result.errors, "ожидалась ошибка"
    return result.errors[0].extensions["code"]


class Clock:
    now = 1_700_000_000.0

    def __call__(self):
        return self.now


def test_protected_operations_require_token():
    assert code_of(execute("{ me { id } }")) == "UNAUTHENTICATED"
    assert code_of(execute("{ myRequests { id } }")) == "UNAUTHENTICATED"
    assert code_of(execute('mutation { createRequest(input: {symptoms: "Белый налёт на листьях"}) { id } }')) == "UNAUTHENTICATED"
    assert code_of(execute("{ me { id } }", token="garbage")) == "UNAUTHENTICATED"


def test_user_id_header_is_not_trusted():
    assert build_context(None)["identity"] is None
    assert "Bearer" in build_context("Basic abc")["auth_error"]
    assert build_context("Bearer ")["identity"] is None


def test_login_returns_jwt_and_token_gives_access():
    data = execute('mutation { login(input: {email: "anna@example.com", password: "password123"}) { token expiresIn user { id } } }').data
    token = data["login"]["token"]
    assert token.count(".") == 2 and data["login"]["expiresIn"] > 0
    assert execute("{ me { id email } }", token=token).data["me"] == {"id": "user-1", "email": "anna@example.com"}


def test_wrong_password_and_blocked_user_cannot_login():
    bad = execute('mutation { login(input: {email: "anna@example.com", password: "wrong"}) { token } }')
    assert code_of(bad) == "FORBIDDEN"
    blocked = execute('mutation { login(input: {email: "oleg@example.com", password: "password123"}) { token } }')
    assert code_of(blocked) == "FORBIDDEN"


def test_public_operations_work_with_stale_token():
    stale = token_for("user-1")
    clients.security_client.sessions.clear()
    result = execute('mutation { login(input: {email: "anna@example.com", password: "password123"}) { token } }', token=stale)
    assert result.errors is None


def test_logout_ends_session_although_jwt_is_valid():
    token = token_for("user-1")
    assert execute("mutation { logout }", token=token).data == {"logout": True}
    result = execute("{ me { id } }", token=token)
    assert code_of(result) == "UNAUTHENTICATED" and "Сессия" in result.errors[0].message


def test_session_expires_by_ttl_and_is_extended_by_activity():
    clock = Clock()
    clients.security_client._clock = clock
    token = token_for("user-1")
    clock.now += 1700
    assert execute("{ me { id } }", token=token).errors is None
    clock.now += 1700
    assert execute("{ me { id } }", token=token).errors is None
    idle = token_for("user-1")
    clock.now += 1900
    assert "Сессия" in execute("{ me { id } }", token=idle).errors[0].message
    old = token_for("user-1")
    clock.now += 3700
    assert code_of(execute("{ me { id } }", token=old)) == "UNAUTHENTICATED"


def test_forged_and_tampered_tokens_are_rejected():
    token = token_for("user-1")
    head, body, signature = token.split(".")
    assert code_of(execute("{ me { id } }", token=f"{head}.{body}.AAAA")) == "UNAUTHENTICATED"
    forged = base64.urlsafe_b64encode(json.dumps({"sub": "user-3", "role": "ADMIN", "sid": "x", "exp": 9999999999}).encode()).rstrip(b"=").decode()
    assert code_of(execute("{ me { id } }", token=f"{head}.{forged}.{signature}")) == "UNAUTHENTICATED"
    none_alg = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    assert code_of(execute("{ me { id } }", token=f"{none_alg}.{body}.")) == "UNAUTHENTICATED"


def test_blocked_user_loses_access_immediately():
    victim, admin = token_for("user-4"), token_for("user-3")
    assert execute('mutation { blockUser(userId: "user-4") { status } }', token=admin).errors is None
    assert code_of(execute("{ me { id } }", token=victim)) == "UNAUTHENTICATED"
    assert all(s["user_id"] != "user-4" for s in clients.security_client.sessions.values())


def test_matrix_covers_every_query_and_mutation():
    result = schema.execute_sync("{ __schema { queryType { fields { name } } mutationType { fields { name } } } }")
    declared = {f"Query.{f['name']}" for f in result.data["__schema"]["queryType"]["fields"]}
    declared |= {f"Mutation.{f['name']}" for f in result.data["__schema"]["mutationType"]["fields"]}
    assert declared == set(POLICY)


def test_role_matrix_is_enforced():
    for operation, rule in POLICY.items():
        for role in ("CLIENT", "EXPERT", "ADMIN"):
            info = SimpleNamespace(context={"identity": Identity("u", role, "s"), "auth_error": None})
            allowed = rule in (PUBLIC, AUTHENTICATED) or role in rule
            try:
                access(operation)().has_permission(None, info)
                got = True
            except DomainError as error:
                assert error.extensions["code"] == "FORBIDDEN"
                got = False
            assert got == allowed, (operation, role)


def test_roles_restrict_queries_and_mutations():
    forbidden = [
        ("user-1", "{ users { id } }"), ("user-2", "{ usersSummary { total } }"), ("user-1", "{ availableRequests { id } }"),
        ("user-2", "{ myRequests { id } }"), ("user-1", "{ expertApplications { id } }"), ("user-2", "{ platformSummary { experts } }"),
        ("user-2", 'mutation { createRequest(input: {symptoms: "Эксперт не создаёт заявки"}) { id } }'),
        ("user-1", 'mutation { respondToRequest(input: {requestId: "req-1"}) { id } }'),
        ("user-1", 'mutation { approveWithdrawal(withdrawalId: "wd-1") { id } }'),
        ("user-2", 'mutation { verifyExpert(applicationId: "app-1", approve: true) { id } }'),
        ("user-1", 'mutation { blockUser(userId: "user-4") { id } }'),
        ("user-1", 'mutation { createDiagnosis(input: {requestId: "req-2", diseaseId: "dis-1", description: "Диагноз клиента"}) { id } }'),
    ]
    for user, query in forbidden:
        assert code_of(execute(query, user=user)) == "FORBIDDEN", (user, query)
    assert execute("{ users { id } }", user="user-3").errors is None


def test_user_cannot_read_other_users_data():
    cases = [("user-4", '{ request(id: "req-1") { id } }'), ("user-4", '{ diagnosis(id: "diag-1") { id } }'),
             ("user-4", '{ diagnosisByRequest(requestId: "req-2") { id } }'), ("user-4", '{ tracker(id: "track-1") { id } }'),
             ("user-4", '{ trackerProgress(trackerId: "track-1") { percent } }'), ("user-4", '{ chatRoom(id: "chat-1") { id } }'),
             ("user-1", '{ user(id: "user-2") { id } }'), ("user-4", '{ satelliteField(id: "fld-1") { id } }'),
             ("user-4", '{ fieldNdviSummary(fieldId: "fld-1") { count } }'), ("user-2", '{ expertBalance(expertId: "user-6") { earned } }'),
             ("user-1", '{ requestsSummary(clientId: "user-4") { total } }')]
    for user, query in cases:
        assert code_of(execute(query, user=user)) == "FORBIDDEN", (user, query)


def test_owner_expert_and_admin_have_access():
    assert execute('{ request(id: "req-1") { id } }', user="user-1").errors is None
    assert execute('{ request(id: "req-1") { id } }', user="user-2").errors is None
    assert execute('{ request(id: "req-2") { id } }', user="user-3").errors is None
    assert execute('{ diagnosis(id: "diag-1") { id } }', user="user-2").errors is None
    assert execute('{ expertBalance(expertId: "user-2") { earned } }', user="user-3").errors is None


def test_data_is_scoped_by_role():
    ids = lambda user, q, f: sorted(i["id"] for i in execute(q, user=user).data[f])
    assert ids("user-1", "{ transactions { id } }", "transactions") == ["tx-1"]
    assert ids("user-4", "{ transactions { id } }", "transactions") == ["tx-2", "tx-3"]
    assert ids("user-2", "{ transactions { id } }", "transactions") == ["tx-1", "tx-2", "tx-3"]
    assert execute("{ requestsSummary { total } }", user="user-1").data["requestsSummary"]["total"] == 3
    assert execute("{ requestsSummary { total } }", user="user-3").data["requestsSummary"]["total"] == 5
    assert code_of(execute('{ transactions(filter: {userId: "user-4"}) { id } }', user="user-1")) == "FORBIDDEN"
    assert execute("{ notifications { id } }", user="user-4").data["notifications"] == []


def test_actor_comes_from_token_not_from_arguments():
    created = execute('mutation { createRequest(input: {symptoms: "Белый налёт на листьях огурцов"}) { id client { id } } }', user="user-4")
    assert created.data["createRequest"]["client"]["id"] == "user-4"


def test_auth_service_outage_gives_service_unavailable_not_unauthenticated():
    from app import clients
    from app.errors import ServiceUnavailableError

    class DownSecurity:
        def verify(self, token):
            raise ServiceUnavailableError("Сервис auth-service недоступен")

    clients.use(security_client=DownSecurity())
    assert code_of(execute("{ me { id } }", token="any")) == "SERVICE_UNAVAILABLE"
    assert code_of(execute("{ myRequests { id } }", token="any")) == "SERVICE_UNAVAILABLE"
