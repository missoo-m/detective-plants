import logging

import strawberry

from .errors import DomainError
from .mutations import Mutation
from .queries import Query

log = logging.getLogger("graphql")


class LoggingSchema(strawberry.Schema):

    def process_errors(self, errors, execution_context=None) -> None:
        for error in errors:
            original = getattr(error, "original_error", None) or error
            if isinstance(original, DomainError):
                level = logging.ERROR if original.code == "SERVICE_UNAVAILABLE" else logging.WARNING
                log.log(level, "GraphQL-ошибка %s: %s", original.code, original.message)
            else:
                log.error("Необработанная ошибка GraphQL: %s", error, exc_info=getattr(error, "original_error", None))


schema = LoggingSchema(query=Query, mutation=Mutation)
