from abc import ABC, abstractmethod

from .identity import Identity


class AuthSecurityClient(ABC):
    @abstractmethod
    def register(self, email: str, password: str, name: str) -> dict:
        pass

    @abstractmethod
    def login(self, email: str, password: str) -> dict:
        pass

    @abstractmethod
    def verify(self, token: str) -> Identity:
        pass

    @abstractmethod
    def logout(self, token: str) -> bool:
        pass
