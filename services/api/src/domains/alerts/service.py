import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.alerts.models import Alert
from src.domains.alerts.repository import AlertRepository
from src.domains.alerts.schemas import AlertCreate

class AlertService:
    def __init__(self, session: AsyncSession):
        self.repository = AlertRepository(session)

    async def create_alert(self, alert_data: AlertCreate) -> Alert:
        """
        Create a new alert.
        """
        return await self.repository.create(alert_data)

    async def get_subscription_alerts(self, subscription_id: uuid.UUID, limit: int = 10) -> Sequence[Alert]:
        """
        Get alerts for a specific subscription.
        """
        return await self.repository.get_by_subscription(subscription_id, limit)

    async def get_latest_alerts(self, subscription_ids: list[uuid.UUID]) -> Sequence[Alert]:
        """
        Get latest alert for multiple subscriptions.
        """
        return await self.repository.get_latest_alerts_by_subscription_ids(subscription_ids)
