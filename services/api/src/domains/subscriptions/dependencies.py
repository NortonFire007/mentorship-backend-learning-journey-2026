import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.domains.subscriptions.repository import SubscriptionRepository
from src.domains.subscriptions.service import SubscriptionService
from src.domains.subscriptions.models import Subscription
from src.domains.users.models import User
from src.domains.auth.dependencies import get_current_user

def get_subscription_repository(session: AsyncSession = Depends(get_db)) -> SubscriptionRepository:
    return SubscriptionRepository(session)

def get_subscription_service(
    repository: SubscriptionRepository = Depends(get_subscription_repository),
    session: AsyncSession = Depends(get_db),
) -> SubscriptionService:
    return SubscriptionService(repository=repository, session=session)

async def get_current_user_subscription(
    sub_id: uuid.UUID,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user: User = Depends(get_current_user),
) -> Subscription:
    subscription = await service.get_subscription_by_id(sub_id)
    if not current_user.is_superuser and subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access or modify this subscription"
        )
    return subscription
