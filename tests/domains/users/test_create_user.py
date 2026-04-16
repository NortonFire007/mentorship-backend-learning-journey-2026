import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory

@pytest.mark.asyncio
async def test_create_user_success(client: AsyncClient):
    """
    Test creating a new user through the API.
    """
    payload = {
        "name": "Jane",
        "surname": "Doe",
        "email": "jane.doe@example.com",
        "telegram_id": "12345678"
    }

    response = await client.post("/api/v1/users/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane"
    assert data["email"] == "jane.doe@example.com"
    assert data["preferred_currency"] == "USD"
    assert "id" in data

@pytest.mark.asyncio
async def test_create_user_email_conflict(client: AsyncClient, db_session: AsyncSession):
    """
    Test creating a user with an already existing email returns 409.
    """
    # Setup: Add a user directly to DB using .acreate()
    await UserFactory.acreate(db_session, email="existing@example.com")

    # Action: Try creating another user with the same email
    payload = {
        "name": "Another",
        "surname": "User",
        "email": "existing@example.com"
    }
    response = await client.post("/api/v1/users/", json=payload)

    # Assert
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
