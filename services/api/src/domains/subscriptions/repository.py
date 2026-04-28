import uuid
from decimal import Decimal
from typing import List, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.subscriptions.models import Subscription
from src.domains.alerts.models import Alert
from src.domains.subscriptions.schemas import SubscriptionCreate, SubscriptionUpdate
from src.core.enums import TravelType

class SubscriptionRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, sub_id: uuid.UUID) -> Subscription | None:
        """
        Fetch a subscription by ID.
        """
        result = await self.session.execute(select(Subscription).where(Subscription.id == sub_id))
        return result.scalar_one_or_none()

    async def list(
        self, 
        user_id: uuid.UUID | None = None, 
        is_active: bool | None = None,
        travel_type: TravelType | None = None,
        start_date_from: str | None = None,
        start_date_to: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None
    ) -> List[Subscription]:
        """
        Query subscriptions with optional filters.
        """
        query = select(Subscription)
        
        conditions = []
        if user_id:
            conditions.append(Subscription.user_id == user_id)
        if is_active is not None:
            conditions.append(Subscription.is_active == is_active)
        if travel_type:
            conditions.append(Subscription.travel_type == travel_type)
        if start_date_from:
            conditions.append(Subscription.start_date >= start_date_from)
        if start_date_to:
            conditions.append(Subscription.start_date <= start_date_to)
        if min_price is not None:
            conditions.append(Subscription.max_price >= min_price)
        if max_price is not None:
            conditions.append(Subscription.max_price <= max_price)
            
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Subscription.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_destination_stats(self) -> List[Tuple[str, int]]:
        """
        Returns a list of tuples containing (destination, count) 
        for active subscriptions.
        """
        stmt = (
            select(Subscription.destination, func.count(Subscription.id).label("subscription_count"))
            .where(Subscription.is_active == True)
            .group_by(Subscription.destination)
            .order_by(func.count(Subscription.id).desc())
        )
        result = await self.session.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def create(self, sub_data: SubscriptionCreate) -> Subscription:
        """
        Create a new subscription record.
        """
        sub = Subscription(**sub_data.model_dump())
        self.session.add(sub)
        await self.session.flush()
        return sub

    async def update(self, sub: Subscription, sub_data: SubscriptionUpdate) -> Subscription:
        """
        Update an existing subscription (e.g., budget change or deactivation).
        """
        update_data = sub_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(sub, field, value)
        
        await self.session.flush()
        return sub

    async def delete(self, sub: Subscription) -> None:
        """
        Hard delete a subscription record.
        """
        await self.session.delete(sub)
        await self.session.flush()

    async def list_with_latest_alert(self, user_id: uuid.UUID) -> List[Tuple[Subscription, Alert | None]]:
        """
        Fetch all subscriptions for a user, each with its latest alert (if any).
        """
        # Subquery to get the latest alert for each subscription
        latest_alert_subquery = (
            select(Alert)
            .distinct(Alert.subscription_id)
            .order_by(Alert.subscription_id, Alert.created_at.desc())
            .subquery()
        )

        # Join Subscription with the subquery
        stmt = (
            select(Subscription, latest_alert_subquery)
            .outerjoin(latest_alert_subquery, Subscription.id == latest_alert_subquery.c.subscription_id)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        )

        result = await self.session.execute(stmt)
        return result.all()
