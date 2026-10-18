from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from . import config
from .context import get_context
from .schema import schema

app = FastAPI(title=config.APP_TITLE)

graphql_app = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, reload=True)
