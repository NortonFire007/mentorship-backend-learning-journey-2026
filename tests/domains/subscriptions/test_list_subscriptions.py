import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TravelType
from tests.factories import UserFactory, SubscriptionFactory

@pytest.mark.asyncio
async def test_list_subscriptions(client: AsyncClient, db_session: AsyncSession):
    """
    Test fetching and filtering the list of subscriptions.
    """
    user1 = await UserFactory.acreate(db_session)
    user2 = await UserFactory.acreate(db_session)

    # User 1 has 2 subscriptions (1 active flight, 1 inactive hotel)
    await SubscriptionFactory.acreate(db_session, user=user1, travel_type=TravelType.FLIGHT, is_active=True)
    await SubscriptionFactory.acreate(db_session, user=user1, travel_type=TravelType.HOTEL, is_active=False)
    
    # User 2 has 1 active flight subscription
    await SubscriptionFactory.acreate(db_session, user=user2, travel_type=TravelType.FLIGHT, is_active=True)
    
    # 1. Fetch all
    response = await client.get("/api/v1/subscriptions/")
    assert response.status_code == 200
    assert len(response.json()) >= 3

    # 2. Filter by user_id
    response = await client.get(f"/api/v1/subscriptions/?user_id={user1.id}")
    data = response.json()
    assert len(data) == 2
    assert all(d["user_id"] == str(user1.id) for d in data)

    # 3. Filter by is_active and travel_type
    response = await client.get("/api/v1/subscriptions/?is_active=true&travel_type=flight")
    data = response.json()
    assert len(data) >= 2
    assert all(d["is_active"] is True for d in data)
    assert all(d["travel_type"] == "flight" for d in data)

    # 4. Advanced filtering (min_price, max_price)
    from datetime import date, timedelta
    await SubscriptionFactory.acreate(
        db_session, user=user1, travel_type=TravelType.PACKAGE, is_active=True,
        min_price=100.0, max_price=500.0,
        start_date=date.today(), end_date=date.today() + timedelta(days=7)
    )
    
    response = await client.get("/api/v1/subscriptions/?min_price=200")
    data = response.json()
    assert response.status_code == 200
    
    response = await client.get("/api/v1/subscriptions/?max_price=50")
    data = response.json()
    assert response.status_code == 200

    response = await client.get(f"/api/v1/subscriptions/?start_date_from={date.today()}&start_date_to={date.today() + timedelta(days=1)}")
    data = response.json()
    assert response.status_code == 200
