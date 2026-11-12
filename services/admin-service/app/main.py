import argparse
import logging
import signal
import threading

from . import config
from .database import get_session_factory, init_db
from .grpc_server import registration
from .grpc_support import build_server
from .seed import seed
from .service import AdminService
from .events import KafkaProducer, OutboxRelay, ensure_topics

log = logging.getLogger(config.SERVICE_NAME)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Admin Service")
    parser.add_argument("--init-only", action="store_true", help="создать таблицы и тестовые данные и завершиться")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    init_db()
    if config.SEED_ON_START or args.init_only:
        log.info("Тестовые данные добавлены" if seed() else "Тестовые данные уже есть")
    if args.init_only:
        return 0

    factory = get_session_factory()
    service = AdminService(factory)                
    registrars, names = registration(service)
    workers = []
    ensure_topics()
    workers.append(OutboxRelay(factory, KafkaProducer()))
    for worker in workers:
        worker.start()
    server, port = build_server(registrars, config.GRPC_PORT, names, config.INTERNAL_API_KEY)
    server.start()
    log.info("%s: gRPC слушает порт %s", config.SERVICE_NAME, port)

    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    stop.wait()
    log.info("Остановка...")
    server.stop(5).wait()
    for worker in workers:
        worker.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
