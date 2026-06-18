from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.domains.subscriptions.repository import SubscriptionRepository
from src.domains.subscriptions.service import SubscriptionService

def get_subscription_repository(session: AsyncSession = Depends(get_db)) -> SubscriptionRepository:
    return SubscriptionRepository(session)

def get_subscription_service(
    repository: SubscriptionRepository = Depends(get_subscription_repository),
    session: AsyncSession = Depends(get_db),
) -> SubscriptionService:
    return SubscriptionService(repository=repository, session=session)
