import uuid
from dataclasses import dataclass
from src.core.events.base import Event

from decimal import Decimal

@dataclass(kw_only=True)
class SubscriptionCreatedEvent(Event):
    subscription_id: uuid.UUID
    user_id: uuid.UUID
    destination: str


@dataclass(kw_only=True)
class DigestRequestedEvent(Event):
    user_id: uuid.UUID
    trigger_type: str


@dataclass(kw_only=True)
class AlertCreatedEvent(Event):
    alert_id: uuid.UUID
    subscription_id: uuid.UUID
    user_id: uuid.UUID
    price_found: Decimal
    currency: str
    deep_link: str
    image_url: str | None

