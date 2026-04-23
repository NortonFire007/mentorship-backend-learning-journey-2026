import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory, SubscriptionFactory

@pytest.mark.asyncio
async def test_delete_subscription(client: AsyncClient, db_session: AsyncSession):
    """
    Test hard deletion of a subscription.
    """
    user = await UserFactory.acreate(db_session)
    sub = await SubscriptionFactory.acreate(db_session, user=user)

    # 1. Delete it
    response = await client.delete(f"/api/v1/subscriptions/{sub.id}")
    assert response.status_code == 24 or response.status_code == 204 # Expecting 204

    # 2. Verify it's gone
    response = await client.get(f"/api/v1/subscriptions/{sub.id}")
    assert response.status_code == 404
