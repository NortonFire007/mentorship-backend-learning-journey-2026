import pytest
import uuid
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory

@pytest.mark.asyncio
async def test_create_subscription_success(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test creating a new subscription for an authenticated user.
    Verifies that the subscription is automatically bound to the current user.
    """
    user = verified_user_client.user

    payload = {
        "destination": "Paris, France",
        "travel_type": "flight",
        "start_date": str(date.today() + timedelta(days=5)),
        "end_date": str(date.today() + timedelta(days=15)),
        "max_price": "250.00",
        "currency": "EUR"
    }

    response = await verified_user_client.post("/api/v1/subscriptions/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["destination"] == "Paris, France"
    assert data["max_price"] == "250.00"
    assert "id" in data
    # Verify server-side binding to the current logged-in user
    assert data["user_id"] == str(user.id)

@pytest.mark.asyncio
async def test_create_subscription_unauthenticated(client: AsyncClient):
    """
    Test that unauthenticated requests to create a subscription return 401.
    """
    payload = {
        "destination": "London",
        "travel_type": "flight",
        "max_price": "100.00"
    }

    response = await client.post("/api/v1/subscriptions/", json=payload)
    assert response.status_code == 401
