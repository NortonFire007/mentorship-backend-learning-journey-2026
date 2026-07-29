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
        "origin": "London",
        "travel_type": "flight",
        "max_price": "100.00"
    }

    response = await client.post("/api/v1/subscriptions/", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_subscription_with_search_filters(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test creating a subscription with advanced search parameters.
    Verifies that the values are correctly parsed, validated, and stored.
    """
    user = verified_user_client.user

    payload = {
        "destination": "London, UK",
        "travel_type": "hotel",
        "start_date": str(date.today() + timedelta(days=5)),
        "end_date": str(date.today() + timedelta(days=15)),
        "max_price": "500.00",
        "currency": "USD",
        "adults": 4,
        "children": 2,
        "min_bedrooms": 3,
        "min_beds": 5,
        "flexible_days": 3,
        "max_stops": 1
    }

    response = await verified_user_client.post("/api/v1/subscriptions/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["adults"] == 4
    assert data["children"] == 2
    assert data["min_bedrooms"] == 3
    assert data["min_beds"] == 5
    assert data["flexible_days"] == 3
    assert data["max_stops"] == 1

    # Verify defaults are set correctly if omitted
    payload_defaults = {
        "destination": "Paris, France",
        "travel_type": "hotel",
        "max_price": "300.00"
    }
    response_defaults = await verified_user_client.post("/api/v1/subscriptions/", json=payload_defaults)
    assert response_defaults.status_code == 201
    data_defaults = response_defaults.json()
    assert data_defaults["adults"] == 1
    assert data_defaults["children"] == 0
    assert data_defaults["min_bedrooms"] is None
    assert data_defaults["min_beds"] is None
    assert data_defaults["flexible_days"] is None
    assert data_defaults["max_stops"] is None

    # Verify out of range constraints
    payload_invalid = {
        "destination": "Paris, France",
        "travel_type": "hotel",
        "max_price": "300.00",
        "adults": 0  # Invalid, must be >= 1
    }
    response_invalid = await verified_user_client.post("/api/v1/subscriptions/", json=payload_invalid)
    assert response_invalid.status_code == 422
