from __future__ import annotations
import uuid
from typing import TYPE_CHECKING
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Enum, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base
from src.core.enums import AlertStatus

if TYPE_CHECKING:
    from src.domains.subscriptions.models import Subscription

class Alert(Base):
    """
    Alert entity for tracking sent notifications about price deals.
    """
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    price_found: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    status: Mapped[AlertStatus] = mapped_column(
        Enum(
            AlertStatus, 
            name="alert_status_enum", 
            create_type=False,
            values_callable=lambda obj: [item.value for item in obj]
        ),
        default=AlertStatus.PENDING,
        server_default=AlertStatus.PENDING.value
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        index=True
    )

    # Relationships
    subscription: Mapped[Subscription] = relationship(back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, subscription_id={self.subscription_id}, price={self.price_found}, status={self.status})>"
