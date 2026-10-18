class ServiceError(Exception):
    pass

class NotFoundError(ServiceError):
    pass

class InvalidValueError(ServiceError, ValueError):
    pass

class PermissionDeniedError(ServiceError):
    pass

class BusinessRuleError(ServiceError):
    pass

class AuthenticationError(ServiceError):
    pass