import uuid
from typing import List, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.alerts.models import Alert
from src.domains.alerts.schemas import AlertCreate
from src.domains.subscriptions.models import Subscription
from src.core.events.events import AlertCreatedEvent

class AlertRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, alert_data: AlertCreate) -> Alert:
        """
        Create a new alert record.
        """

        # Retrieve the subscription to get user_id and currency
        stmt = select(Subscription).where(Subscription.id == alert_data.subscription_id)
        res = await self.session.execute(stmt)
        sub = res.scalar_one()

        model_data = alert_data.model_dump()
        alert = Alert(**model_data)
        if not alert.id:
            alert.id = uuid.uuid4()

        # Record domain event
        alert.record_event(
            AlertCreatedEvent(
                alert_id=alert.id,
                subscription_id=alert.subscription_id,
                user_id=sub.user_id,
                price_found=alert.price_found,
                currency=sub.currency.value if hasattr(sub.currency, "value") else str(sub.currency),
                deep_link=getattr(alert_data, "deep_link", None) or "",
                image_url=alert.image_url,
            )
        )

        self.session.add(alert)
        await self.session.flush()

        return alert

    async def get_by_subscription(self, subscription_id: uuid.UUID, limit: int = 10) -> Sequence[Alert]:
        """
        Get alert history for a specific subscription.
        """
        stmt = (
            select(Alert)
            .where(Alert.subscription_id == subscription_id)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_latest_alerts_by_subscription_ids(self, subscription_ids: List[uuid.UUID]) -> Sequence[Alert]:
        """
        Get the latest alert for each given subscription ID.
        """
        if not subscription_ids:
            return []

        # In SQLAlchemy, distinct() with arguments is supported by PostgreSQL
        stmt = (
            select(Alert)
            .where(Alert.subscription_id.in_(subscription_ids))
            .distinct(Alert.subscription_id)
            .order_by(Alert.subscription_id, Alert.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
