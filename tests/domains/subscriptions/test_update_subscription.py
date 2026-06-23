import pytest
import uuid
from datetime import date, timedelta
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.subscriptions.service import SubscriptionService
from src.domains.subscriptions.repository import SubscriptionRepository
from src.domains.subscriptions.schemas import SubscriptionUpdate
from tests.factories import UserFactory, SubscriptionFactory


@pytest.mark.asyncio
async def test_update_subscription_validation(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test cross-field date validation when updating a subscription.
    """
    user = verified_user_client.user

    # Start date is in 10 days, End date is in 20 days
    sub = await SubscriptionFactory.acreate(
        db_session,
        user=user,
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=20)
    )

    # Case 1: Valid update (move end date further)
    payload_valid = {"end_date": str(date.today() + timedelta(days=30))}
    response = await verified_user_client.patch(f"/api/v1/subscriptions/{sub.id}", json=payload_valid)
    assert response.status_code == 200

    # Case 2: Invalid update (move end date BEFORE current start date)
    payload_invalid = {"end_date": str(date.today() + timedelta(days=5))}
    response = await verified_user_client.patch(f"/api/v1/subscriptions/{sub.id}", json=payload_invalid)
    assert response.status_code == 400
    assert "Start date cannot be after end date" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_subscription_hijacking_protection(db_session: AsyncSession):
    """
    Test that modifying user_id is explicitly blocked at the service layer.
    """
    user = await UserFactory.acreate(db_session)
    sub = await SubscriptionFactory.acreate(db_session, user=user)

    repo = SubscriptionRepository(db_session)
    service = SubscriptionService(repo, db_session)

    # Attempt to hijack ownership by subclassing SubscriptionUpdate
    new_user_id = uuid.uuid4()
    
    class HijackedSubscriptionUpdate(SubscriptionUpdate):
        user_id: uuid.UUID | None = None

    payload = HijackedSubscriptionUpdate(user_id=new_user_id)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_subscription(sub.id, payload)

    assert exc_info.value.status_code == 400
    assert "Modifying user_id is not allowed" in exc_info.value.detail
