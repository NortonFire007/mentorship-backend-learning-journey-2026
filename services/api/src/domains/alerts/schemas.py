from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from src.core.enums import AlertStatus

class AlertBase(BaseModel):
    price_found: Decimal
    status: AlertStatus = AlertStatus.PENDING

class AlertCreate(AlertBase):
    subscription_id: UUID

class AlertRead(AlertBase):
    id: UUID
    subscription_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
