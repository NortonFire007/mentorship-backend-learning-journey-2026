import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory, SubscriptionFactory
from src.core.enums import TravelType

@pytest.mark.asyncio
async def test_list_users_with_subscriptions(client: AsyncClient, db_session: AsyncSession):
    """
    Test fetching all users includes their subscriptions due to eager loading.
    """
    user = await UserFactory.acreate(db_session)
    await SubscriptionFactory.acreate(db_session, user=user, travel_type=TravelType.FLIGHT, is_active=True)
    
    response = await client.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    
    user_data = next((d for d in data if d["id"] == str(user.id)), None)
    assert user_data is not None
    assert "subscriptions" in user_data
    assert len(user_data["subscriptions"]) == 1
    assert user_data["subscriptions"][0]["travel_type"] == "flight"
