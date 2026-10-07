from graphql import GraphQLError


class DomainError(GraphQLError):
    code = "INTERNAL_ERROR"

    def __init__(self, message: str):
        super().__init__(message, extensions={"code": self.code})


class NotFoundError(DomainError):
    code = "NOT_FOUND"


class ValidationError(DomainError):
    code = "BAD_USER_INPUT"


class PermissionDeniedError(DomainError):
    code = "FORBIDDEN"


class BusinessRuleError(DomainError):
    code = "BUSINESS_RULE_VIOLATION"
