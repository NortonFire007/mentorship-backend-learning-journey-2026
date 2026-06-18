import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory, SubscriptionFactory
from src.core.enums import TravelType

@pytest.mark.asyncio
async def test_get_user_active_counts(superuser_client: AsyncClient, db_session: AsyncSession):
    """
    Test fetching active subscription counts per user (as superuser).
    """
    user1 = await UserFactory.acreate(db_session)
    user2 = await UserFactory.acreate(db_session)
    
    # User 1 has 2 active subscriptions
    await SubscriptionFactory.acreate(db_session, user=user1, is_active=True)
    await SubscriptionFactory.acreate(db_session, user=user1, is_active=True)
    
    # User 2 has 1 active and 1 inactive
    await SubscriptionFactory.acreate(db_session, user=user2, is_active=True)
    await SubscriptionFactory.acreate(db_session, user=user2, is_active=False)
    
    response = await superuser_client.get("/api/v1/users/stats/active-counts")
    assert response.status_code == 200
    data = response.json()
    
    user1_stats = next((d for d in data if d["id"] == str(user1.id)), None)
    user2_stats = next((d for d in data if d["id"] == str(user2.id)), None)
    
    assert user1_stats is not None
    assert user1_stats["active_subscriptions_count"] >= 2
    
    assert user2_stats is not None
    assert user2_stats["active_subscriptions_count"] >= 1


@pytest.mark.asyncio
async def test_get_user_active_counts_unauthorized(client: AsyncClient):
    """
    Test that unauthenticated requests to get user active counts return 401.
    """
    response = await client.get("/api/v1/users/stats/active-counts")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_user_active_counts_forbidden(verified_user_client: AsyncClient):
    """
    Test that regular (non-superuser) verified users cannot get active counts (403).
    """
    response = await verified_user_client.get("/api/v1/users/stats/active-counts")
    assert response.status_code == 403

