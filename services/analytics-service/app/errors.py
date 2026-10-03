class NotFoundError(Exception):
    #Запрошенный объект не найден
    pass


class InvalidValueError(ValueError):
    #Передано недопустимое значение
    pass
