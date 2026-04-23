import pytest
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory, SubscriptionFactory

@pytest.mark.asyncio
async def test_update_subscription_validation(client: AsyncClient, db_session: AsyncSession):
    """
    Test cross-field date validation when updating a subscription.
    """
    user = await UserFactory.acreate(db_session)

    # Start date is in 10 days, End date is in 20 days
    sub = await SubscriptionFactory.acreate(
        db_session,
        user=user,
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=20)
    )

    # Case 1: Valid update (move end date further)
    payload_valid = {"end_date": str(date.today() + timedelta(days=30))}
    response = await client.patch(f"/api/v1/subscriptions/{sub.id}", json=payload_valid)
    assert response.status_code == 200

    # Case 2: Invalid update (move end date BEFORE current start date)
    payload_invalid = {"end_date": str(date.today() + timedelta(days=5))}
    response = await client.patch(f"/api/v1/subscriptions/{sub.id}", json=payload_invalid)
    assert response.status_code == 400
    assert "Start date cannot be after end date" in response.json()["detail"]
