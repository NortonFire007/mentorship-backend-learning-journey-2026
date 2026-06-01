import uuid
from dataclasses import dataclass
from src.core.events.base import Event

@dataclass(kw_only=True)
class SubscriptionCreatedEvent(Event):
    subscription_id: uuid.UUID
    user_id: uuid.UUID
    destination: str


@dataclass(kw_only=True)
class DigestRequestedEvent(Event):
    user_id: uuid.UUID
    trigger_type: str
