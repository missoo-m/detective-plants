import logging

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from . import clients, config
from .context import get_context
from .grpc_support import probe_services
from .schema import schema

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
clients.init_grpc_clients()                

app = FastAPI(title=config.APP_TITLE)

graphql_app = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/services")
def health_services():
    services = probe_services(config.SERVICE_ADDRESSES)
    return {"status": "ok" if all(v == "up" for v in services.values()) else "degraded", "services": services}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, reload=True)
