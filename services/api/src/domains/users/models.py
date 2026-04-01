from __future__ import annotations
import uuid
from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base
from src.core.enums import CurrencyEnum

if TYPE_CHECKING:
    from src.domains.subscriptions.models import Subscription

class User(Base):
    """
    Base profile of a person receiving alerts.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    surname: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Validated via EmailStr in Pydantic, stored as string in DB
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    
    # Optional telegram ID for future notifications
    telegram_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Preferred currency enum
    preferred_currency: Mapped[CurrencyEnum] = mapped_column(
        Enum(CurrencyEnum, name="user_currency_enum"),
        default=CurrencyEnum.USD,
        server_default=CurrencyEnum.USD.value
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # Relationships
    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="user", 
        cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
