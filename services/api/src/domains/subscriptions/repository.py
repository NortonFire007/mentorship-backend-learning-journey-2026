import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.subscriptions.models import Subscription
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
        travel_type: TravelType | None = None
    ) -> list[Subscription]:
        """
        Query subscriptions with optional filters.
        """
        query = select(Subscription)
        
        if user_id:
            query = query.where(Subscription.user_id == user_id)
        if is_active is not None:
            query = query.where(Subscription.is_active == is_active)
        if travel_type:
            query = query.where(Subscription.travel_type == travel_type)
        
        query = query.order_by(Subscription.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

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
