import logging
import time

from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter

from . import clients, config
from .cache import get_cache
from .context import get_context
from .grpc_support import probe_services
from .logging_setup import configure_logging, correlation_id, deadline_at, new_correlation_id
from .schema import schema

configure_logging(config.SERVICE_NAME)
log = logging.getLogger("http")
clients.init_grpc_clients()

app = FastAPI(title=config.APP_TITLE)


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    cid = request.headers.get("x-correlation-id") or new_correlation_id()
    id_token = correlation_id.set(cid)
    time_token = deadline_at.set(time.monotonic() + config.OPERATION_TIMEOUT_SECONDS)
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("%s %s: необработанная ошибка", request.method, request.url.path)
        raise
    finally:
        deadline_at.reset(time_token)
    log.info("%s %s → %s, %.0f мс", request.method, request.url.path, response.status_code,
             (time.monotonic() - started) * 1000)
    response.headers["X-Correlation-ID"] = cid
    correlation_id.reset(id_token)
    return response


graphql_app = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/services")
def health_services():
    services = probe_services(config.SERVICE_ADDRESSES)
    return {"status": "ok" if all(v == "up" for v in services.values()) else "degraded", "services": services}


@app.get("/health/cache")
def health_cache():
    return get_cache().stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, reload=True)
