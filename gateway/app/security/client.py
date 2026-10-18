from abc import ABC, abstractmethod

from .identity import Identity


class AuthSecurityClient(ABC):
    @abstractmethod
    def register(self, email: str, password: str, name: str) -> dict:
        """Регистрация клиента - данные пользователя"""

    @abstractmethod
    def login(self, email: str, password: str) -> dict:
        """Проверка учётных данных, создание сессии и выдача JWT - {access_token, expires_in, session_id, user}"""

    @abstractmethod
    def verify(self, token: str) -> Identity:
        """Проверка подписи JWT, срока действия и активной сессии - Identity"""

    @abstractmethod
    def logout(self, token: str) -> bool:
        """Завершает текущую сессию"""
