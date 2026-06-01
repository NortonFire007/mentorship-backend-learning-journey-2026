import uuid
from dataclasses import dataclass
from src.core.events.base import Event

@dataclass
class SubscriptionCreatedEvent(Event):
    subscription_id: uuid.UUID
    user_id: uuid.UUID
    destination: str
