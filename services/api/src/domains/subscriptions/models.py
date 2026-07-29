from __future__ import annotations
import uuid
from typing import TYPE_CHECKING
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum, Date, Numeric, Integer, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base
from src.core.enums import TravelType, CurrencyEnum

if TYPE_CHECKING:
    from src.domains.users.models import User
    from src.domains.alerts.models import Alert

class Subscription(Base):
    """
    Subscription entity for tracking price deals.
    """
    __tablename__ = "subscriptions"

    __table_args__ = (
        Index("idx_subscriptions_destination_origin", "destination", "origin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        index=True, 
        nullable=False
    )
    
    origin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Enum for flight, hotel, package
    travel_type: Mapped[TravelType] = mapped_column(
        Enum(
            TravelType, 
            name="travel_type_enum", 
            create_type=False,
            values_callable=lambda obj: [item.value for item in obj]
        ), 
        nullable=False
    )
    
    # Dates for travel
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Optional field for duration if dates aren't fixed
    duration_days: Mapped[int | None] = mapped_column(nullable=True)
    
    # Financial data
    max_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[CurrencyEnum] = mapped_column(
        Enum(CurrencyEnum, name="currency_enum", create_type=False),
        default=CurrencyEnum.USD,
        server_default=CurrencyEnum.USD.value
    )
    
    # Search parameters
    adults: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    children: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    min_bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_beds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flexible_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_stops: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )


    # Relationships
    user: Mapped[User] = relationship(back_populates="subscriptions")
    alerts: Mapped[list[Alert]] = relationship(back_populates="subscription", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, destination={self.destination})>"
