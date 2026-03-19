from abc import ABC, abstractmethod
from typing import Any


class A2ASender(ABC):
    @abstractmethod
    async def send(self, agent_id: str, message: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class A2AReceiver(ABC):
    @abstractmethod
    async def on_message(self, message: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class A2ABus(ABC):
    @abstractmethod
    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def subscribe(self, topic: str, handler: A2AReceiver) -> None:
        raise NotImplementedError
