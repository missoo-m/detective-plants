class NotFoundError(Exception):
    #Запрошенный объект не найден
    pass


class InvalidValueError(ValueError):
    #Передано недопустимое значение
    pass

class ServiceError(Exception):
    #Базовая ошибка сервиса
    pass

class PermissionDeniedError(ServiceError):
    #Действие запрещено для данного пользователя
    pass


class BusinessRuleError(ServiceError):
    #Нарушено бизнес-правило (недопустимый статус, лимит, дубликат и тд)
    pass