import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, computed_field, ConfigDict
from src.core.enums import CurrencyEnum

class UserBase(BaseModel):
    """
    Base user schema with common fields.
    """
    name: str
    surname: str
    email: EmailStr
    preferred_currency: CurrencyEnum = CurrencyEnum.USD
    telegram_id: str | None = None

class UserCreate(UserBase):
    """
    Schema for creating a new user.
    """
    pass

class UserUpdate(BaseModel):
    """
    Schema for updating an existing user. All fields are optional.
    """
    name: str | None = None
    surname: str | None = None
    email: EmailStr | None = None
    preferred_currency: CurrencyEnum | None = None
    telegram_id: str | None = None

class UserRead(UserBase):
    """
    Schema for reading user data, including database metadata.
    """
    id: uuid.UUID
    is_active: bool
    created_at: datetime

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"

    model_config = ConfigDict(from_attributes=True)
