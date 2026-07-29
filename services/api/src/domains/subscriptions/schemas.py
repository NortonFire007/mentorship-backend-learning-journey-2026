import uuid
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from src.core.enums import TravelType, CurrencyEnum

class SubscriptionBase(BaseModel):
    """
    Base subscription schema with validation rules.
    """
    origin: str | None = Field(default=None, max_length=255)
    destination: str = Field(..., min_length=2, max_length=255)
    travel_type: TravelType
    
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    duration_days: int | None = Field(default=None, ge=1, le=365)
    
    # Financial data: strictly positive budget
    max_price: Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencyEnum = CurrencyEnum.USD
    provider: str | None = Field(default=None, max_length=255)
    
    # Search filters
    adults: int = Field(default=1, ge=1, le=16)
    children: int = Field(default=0, ge=0, le=16)
    min_bedrooms: int | None = Field(default=None, ge=0, le=10)
    min_beds: int | None = Field(default=None, ge=0, le=16)
    flexible_days: int | None = Field(default=None, ge=0, le=14)
    max_stops: int | None = Field(default=None, ge=0, le=3)

class SubscriptionCreate(SubscriptionBase):
    """
    Schema for creating a new subscription. 
    Strictly forbids past dates and invalid date ranges.
    """

    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, v: date | None) -> date | None:
        if v and v < date.today():
            raise ValueError("Start date cannot be in the past")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "SubscriptionCreate":
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("Start date cannot be after end date")
        return self

class SubscriptionUpdate(BaseModel):
    """
    Schema for updating an existing subscription. 
    """
    origin: str | None = Field(default=None, max_length=255)
    destination: str | None = Field(default=None, min_length=2, max_length=255)
    travel_type: TravelType | None = Field(default=None)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    duration_days: int | None = Field(default=None, ge=1, le=365)
    max_price: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    currency: CurrencyEnum | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    provider: str | None = Field(default=None, max_length=255)
    
    # Search filters
    adults: int | None = Field(default=None, ge=1, le=16)
    children: int | None = Field(default=None, ge=0, le=16)
    min_bedrooms: int | None = Field(default=None, ge=0, le=10)
    min_beds: int | None = Field(default=None, ge=0, le=16)
    flexible_days: int | None = Field(default=None, ge=0, le=14)
    max_stops: int | None = Field(default=None, ge=0, le=3)

class SubscriptionRead(SubscriptionBase):
    """
    Schema for reading subscription data. 
    """
    id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DestinationStatsRead(BaseModel):
    """
    Schema for aggregated destination popularity stats.
    """
    destination: str
    subscription_count: int
