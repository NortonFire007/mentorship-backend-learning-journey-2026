import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TravelType
from tests.factories import UserFactory, SubscriptionFactory

@pytest.mark.asyncio
async def test_get_destination_stats(client: AsyncClient, db_session: AsyncSession):
    user = await UserFactory.acreate(db_session)
    
    # Create subscriptions for different destinations
    await SubscriptionFactory.acreate(db_session, user=user, destination="Paris", travel_type=TravelType.FLIGHT, is_active=True)
    await SubscriptionFactory.acreate(db_session, user=user, destination="Paris", travel_type=TravelType.HOTEL, is_active=True)
    await SubscriptionFactory.acreate(db_session, user=user, destination="London", travel_type=TravelType.FLIGHT, is_active=True)
    
    response = await client.get("/api/v1/subscriptions/stats/destinations")
    assert response.status_code == 200
    data = response.json()
    
    # Check that Paris has count 2 and London has count 1
    paris_stats = next((d for d in data if d["destination"] == "Paris"), None)
    london_stats = next((d for d in data if d["destination"] == "London"), None)
    
    assert paris_stats is not None
    assert paris_stats["subscription_count"] >= 2
    
    assert london_stats is not None
    assert london_stats["subscription_count"] >= 1
