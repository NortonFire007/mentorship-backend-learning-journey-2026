from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base
from src.core.enums import SearchRunStatus


class SearchRun(Base):
    """
    SearchRun entity for tracking the execution lifecycle of data adapter runs.
    """
    __tablename__ = "search_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    external_run_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    status: Mapped[SearchRunStatus] = mapped_column(
        Enum(
            SearchRunStatus,
            name="search_run_status_enum",
            create_type=False,
            values_callable=lambda obj: [item.value for item in obj]
        ),
        default=SearchRunStatus.PENDING,
        server_default=SearchRunStatus.PENDING.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<SearchRun(id={self.id}, subscription_id={self.subscription_id}, provider={self.provider}, status={self.status})>"
