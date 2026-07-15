import uuid
from typing import List
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.domains.alerts.repository import AlertRepository
from src.domains.alerts.service import AlertService
from src.domains.users.models import User
from src.domains.auth.dependencies import get_current_user
from src.domains.subscriptions.repository import SubscriptionRepository
from src.domains.subscriptions.dependencies import get_subscription_repository


def get_alert_repository(session: AsyncSession = Depends(get_db)) -> AlertRepository:
    return AlertRepository(session)


def get_alert_service(
    repository: AlertRepository = Depends(get_alert_repository),
    session: AsyncSession = Depends(get_db),
) -> AlertService:
    return AlertService(repository=repository, session=session)


async def verify_subscription_ownership(
    subscription_id: uuid.UUID,
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
    current_user: User = Depends(get_current_user),
) -> uuid.UUID:
    """
    Ensure the user owns the specified subscription (or is superuser).
    """
    subscription = await sub_repo.get_by_id(subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    if not current_user.is_superuser and subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this subscription's alerts"
        )
    return subscription_id


async def verify_bulk_subscription_ownership(
    subscription_ids: List[uuid.UUID],
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
    current_user: User = Depends(get_current_user),
) -> List[uuid.UUID]:
    """
    Ensure the user owns all of the specified subscriptions (or is superuser).
    Runs a single efficient SELECT count query for validation.
    """
    if not subscription_ids:
        return []
    if current_user.is_superuser:
        return subscription_ids

    unique_ids = list(set(subscription_ids))
    owned_count = await sub_repo.count_owned_subscriptions(unique_ids, current_user.id)
    
    if owned_count != len(unique_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access one or more of the specified subscriptions"
        )
    return subscription_ids
