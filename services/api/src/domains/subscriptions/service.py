import uuid
from datetime import date
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.subscriptions.repository import SubscriptionRepository
from src.domains.users.repository import UserRepository
from src.domains.subscriptions.schemas import SubscriptionCreate, SubscriptionUpdate
from src.domains.subscriptions.models import Subscription
from src.core.enums import TravelType

class SubscriptionService:
    """
    Service Layer for the Subscription domain.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = SubscriptionRepository(session)

    async def create_subscription(self, sub_data: SubscriptionCreate) -> Subscription:
        """
        Create a new traveler subscription.
        """
        user_repository = UserRepository(self.session)
        user = await user_repository.get_by_id(sub_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {sub_data.user_id} not found. Cannot create subscription."
            )

        sub = await self.repository.create(sub_data)
        await self.session.commit()
        await self.session.refresh(sub)
        return sub

    async def list_subscriptions(
        self, 
        user_id: uuid.UUID | None = None, 
        is_active: bool | None = None,
        travel_type: TravelType | None = None,
        start_date_from: date | None = None,
        start_date_to: date | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None
    ) -> list[Subscription]:
        """
        Retrieve a list of subscriptions based on filters.
        """
        return await self.repository.list(
            user_id, is_active, travel_type, 
            start_date_from, start_date_to, min_price, max_price
        )

    async def get_subscription_by_id(self, sub_id: uuid.UUID) -> Subscription:
        """
        Retrieve a single subscription profile.
        """
        sub = await self.repository.get_by_id(sub_id)
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with ID {sub_id} not found"
            )
        return sub

    async def update_subscription(self, sub_id: uuid.UUID, sub_data: SubscriptionUpdate) -> Subscription:
        """
        Partially update subscription.
        """
        sub = await self.get_subscription_by_id(sub_id)
        
        # Determine final state of dates to prevent invalid ranges
        # Use existing DB values if the update payload doesn't provide them.
        final_start = sub_data.start_date if sub_data.start_date is not None else sub.start_date
        final_end = sub_data.end_date if sub_data.end_date is not None else sub.end_date
        
        if final_start and final_end:
            if final_start > final_end:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Start date cannot be after end date (validation against current database record fail)"
                )
        
        updated_sub = await self.repository.update(sub, sub_data)
        await self.session.commit()
        await self.session.refresh(updated_sub)
        return updated_sub

    async def hard_delete_subscription(self, sub_id: uuid.UUID) -> None:
        """
        Permanently remove a subscription record.
        """
        sub = await self.get_subscription_by_id(sub_id)
        await self.repository.delete(sub)
        await self.session.commit()

    async def get_destination_stats(self) -> list[dict]:
        """
        Retrieve popular travel destinations and subscription counts.
        """
        return await self.repository.get_destination_stats()
