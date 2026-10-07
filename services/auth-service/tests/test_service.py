import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.errors import BusinessRuleError, InvalidValueError, NotFoundError, PermissionDeniedError
from app.models import Base
from app.security import issue_token, verify_token
from app.seed import seed, sid
from app.service import AuthService


@pytest.fixture
def service():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    assert seed(factory) is True
    assert seed(factory) is False
    return AuthService(factory)

def test_get_user(service):
    user = service.get_user(str(sid("user-2")))
    assert user.name == "Иван Сидоров" and user.role == "EXPERT" and user.profile.rating == 4.8


def test_not_found_and_invalid_id(service):
    with pytest.raises(NotFoundError):
        service.get_user(str(sid("unknown")))
    with pytest.raises(InvalidValueError):
        service.get_user("not-a-uuid")


def test_list_filters(service):
    assert len(service.list_users()) == 5
    assert [u.name for u in service.list_users(role="EXPERT")] == ["Иван Сидоров"]
    assert [u.name for u in service.list_users(status="BLOCKED")] == ["Олег Заблокированный"]
    assert [u.name for u in service.list_users(search="Огород")] == ["Пётр Огородников"]
    with pytest.raises(InvalidValueError):
        service.list_users(role="HACKER")


def test_search_and_sort_and_paging(service):
    assert service.list_users(search="example.com", sort_by="name")[0].name == "Анна Петрова"
    desc = service.list_users(sort_by="name", descending=True)
    assert desc[0].name == "Пётр Огородников"
    assert len(service.list_users(limit=2)) == 2 and len(service.list_users(limit=2, offset=4)) == 1
    with pytest.raises(InvalidValueError):
        service.list_users(sort_by="password_hash")


def test_users_summary(service):
    s = service.users_summary()
    assert s.total == 5 and s.by_role == {"CLIENT": 3, "EXPERT": 1, "ADMIN": 1}
    assert s.by_status == {"ACTIVE": 4, "BLOCKED": 1}


def test_validate_user(service):
    assert service.validate_user(str(sid("user-1"))).valid is True
    assert service.validate_user(str(sid("user-5"))).valid is False
    assert service.validate_user("garbage").valid is False


def test_register_creates_client(service):
    user = service.register("New.User@Example.com", "strongpass1", "Новый Клиент")
    assert user.role == "CLIENT" and user.status == "ACTIVE" and user.email == "new.user@example.com"
    assert service.get_user(user.id).profile.language == "ru"


def test_register_validation(service):
    with pytest.raises(BusinessRuleError):
        service.register("anna@example.com", "strongpass1", "Дубликат")
    with pytest.raises(InvalidValueError):
        service.register("not-email", "strongpass1", "Имя Имя")
    with pytest.raises(InvalidValueError):
        service.register("a@b.by", "short", "Имя Имя")
    with pytest.raises(InvalidValueError):
        service.register("a@b.by", "strongpass1", " ")


def test_login(service):
    result = service.login("anna@example.com", "password123")
    assert result.user.name == "Анна Петрова" and verify_token(result.token) == result.user.id
    with pytest.raises(PermissionDeniedError):
        service.login("anna@example.com", "wrong-password")
    with pytest.raises(PermissionDeniedError):
        service.login("oleg@example.com", "password123")        


def test_token_expiry():
    token = issue_token("u-1", now=0)
    assert verify_token(token, now=10) == "u-1"
    assert verify_token(token, now=10**9) is None
    assert verify_token(token + "x") is None


def test_update_profile(service):
    user = service.update_profile(str(sid("user-1")), name="Анна Новая", language="en", description="Новое описание")
    assert user.name == "Анна Новая" and user.profile.language == "en" and user.profile.description == "Новое описание"
    with pytest.raises(InvalidValueError):
        service.update_profile(str(sid("user-1")), language="xx")
    with pytest.raises(PermissionDeniedError):
        service.update_profile(str(sid("user-5")), name="Новое Имя")


def test_assign_role_and_status(service):
    assert service.assign_role(str(sid("user-4")), "EXPERT").role == "EXPERT"
    with pytest.raises(BusinessRuleError):
        service.assign_role(str(sid("user-3")), "CLIENT")            
    assert service.set_status(str(sid("user-1")), "BLOCKED").status == "BLOCKED"
    with pytest.raises(BusinessRuleError):
        service.set_status(str(sid("user-3")), "BLOCKED")           
    with pytest.raises(InvalidValueError):
        service.set_status(str(sid("user-1")), "UNKNOWN")
