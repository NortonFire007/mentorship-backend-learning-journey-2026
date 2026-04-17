import pytest
import uuid
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory

@pytest.mark.asyncio
async def test_create_subscription_success(client: AsyncClient, db_session: AsyncSession):
    """
    Test creating a new subscription for an existing user.
    """
    user = await UserFactory.acreate(db_session)

    payload = {
        "user_id": str(user.id),
        "destination": "Paris, France",
        "travel_type": "flight",
        "start_date": str(date.today() + timedelta(days=5)),
        "end_date": str(date.today() + timedelta(days=15)),
        "max_price": "250.00",
        "currency": "EUR"
    }

    response = await client.post("/api/v1/subscriptions/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["destination"] == "Paris, France"
    assert data["max_price"] == "250.00"
    assert "id" in data

@pytest.mark.asyncio
async def test_create_subscription_user_not_found(client: AsyncClient):
    """
    Test creating a subscription fails if the user does not exist.
    """
    payload = {
        "user_id": str(uuid.uuid4()),
        "destination": "London",
        "travel_type": "flight",
        "max_price": "100.00"
    }

    response = await client.post("/api/v1/subscriptions/", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
