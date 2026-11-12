import contextlib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.seed import seed

API_KEY = "test-key"


def make_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed(factory)
    return factory


@contextlib.contextmanager
def serve(service, stub_name, pb_grpc):
    from app.grpc_server import registration
    from app.grpc_support import ServiceChannel, build_server
    registrars, names = registration(service)
    server, port = build_server(registrars, 0, names, api_key=API_KEY)
    server.start()
    channel = ServiceChannel(f"localhost:{port}", "test-service", api_key=API_KEY, retries=0)
    try:
        yield channel.stub(getattr(pb_grpc, stub_name)), channel
    finally:
        channel.close()
        server.stop(0)
