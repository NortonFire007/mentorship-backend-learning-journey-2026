import pytest
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import TravelType
from tests.factories import UserFactory, SubscriptionFactory


@pytest.mark.asyncio
async def test_list_subscriptions_superuser(superuser_client: AsyncClient, db_session: AsyncSession):
    """
    Test fetching and filtering the list of subscriptions as an admin/superuser.
    """
    user1 = await UserFactory.acreate(db_session)
    user2 = await UserFactory.acreate(db_session)

    # User 1 has 2 subscriptions (1 active flight, 1 inactive hotel)
    await SubscriptionFactory.acreate(db_session, user=user1, travel_type=TravelType.FLIGHT, is_active=True)
    await SubscriptionFactory.acreate(db_session, user=user1, travel_type=TravelType.HOTEL, is_active=False)
    
    # User 2 has 1 active flight subscription
    await SubscriptionFactory.acreate(db_session, user=user2, travel_type=TravelType.FLIGHT, is_active=True)
    
    # 1. Fetch all
    response = await superuser_client.get("/api/v1/subscriptions/")
    assert response.status_code == 200
    assert len(response.json()) >= 3

    # 2. Filter by user_id
    response = await superuser_client.get(f"/api/v1/subscriptions/?user_id={user1.id}")
    data = response.json()
    assert len(data) == 2
    assert all(d["user_id"] == str(user1.id) for d in data)

    # 3. Filter by is_active and travel_type
    response = await superuser_client.get("/api/v1/subscriptions/?is_active=true&travel_type=flight")
    data = response.json()
    assert len(data) >= 2
    assert all(d["is_active"] is True for d in data)
    assert all(d["travel_type"] == "flight" for d in data)

    # 4. Advanced filtering (min_price, max_price)
    await SubscriptionFactory.acreate(
        db_session, user=user1, travel_type=TravelType.PACKAGE, is_active=True,
        min_price=100.0, max_price=500.0,
        start_date=date.today(), end_date=date.today() + timedelta(days=7)
    )
    
    response = await superuser_client.get("/api/v1/subscriptions/?min_price=200")
    assert response.status_code == 200
    
    response = await superuser_client.get("/api/v1/subscriptions/?max_price=50")
    assert response.status_code == 200

    response = await superuser_client.get(f"/api/v1/subscriptions/?start_date_from={date.today()}&start_date_to={date.today() + timedelta(days=1)}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_subscriptions_regular_user(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a regular user only sees their own subscriptions, even if they filter for others.
    """
    user = verified_user_client.user
    other_user = await UserFactory.acreate(db_session)

    # Subscriptions owned by the logged-in user
    await SubscriptionFactory.acreate(db_session, user=user, travel_type=TravelType.FLIGHT, is_active=True)
    # Subscription owned by someone else
    await SubscriptionFactory.acreate(db_session, user=other_user, travel_type=TravelType.FLIGHT, is_active=True)

    # 1. Fetching all should only return the logged-in user's subscriptions
    response = await verified_user_client.get("/api/v1/subscriptions/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == str(user.id)

    # 2. Querying with other_user's user_id should be ignored and still return the logged-in user's subscriptions
    response = await verified_user_client.get(f"/api/v1/subscriptions/?user_id={other_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == str(user.id)


@pytest.mark.asyncio
async def test_list_subscriptions_unauthenticated(client: AsyncClient):
    """
    Test that listing subscriptions without authentication returns 401.
    """
    response = await client.get("/api/v1/subscriptions/")
    assert response.status_code == 401
