from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import config
from .models import Base


@lru_cache
def get_engine():
    return create_engine(config.DATABASE_URL, echo=config.SQL_ECHO, pool_pre_ping=True)


@lru_cache
def get_session_factory():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session():
    return get_session_factory()()


def init_db(engine=None) -> None:
    Base.metadata.create_all(engine or get_engine())
