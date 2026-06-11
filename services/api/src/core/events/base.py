import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

@dataclass(kw_only=True)
class Event:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, routing_key: str, event: Event) -> None:
        """
        Publish an event to the registered transport broker.
        """
        pass
