import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory

@pytest.mark.asyncio
async def test_create_user_success(superuser_client: AsyncClient):
    """
    Test creating a new user through the API as a superuser.
    """
    payload = {
        "name": "Jane",
        "surname": "Doe",
        "email": "jane.doe@example.com",
        "telegram_id": "12345678",
        "password": "Password123!"
    }

    response = await superuser_client.post("/api/v1/users/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane"
    assert data["email"] == "jane.doe@example.com"
    assert data["preferred_currency"] == "USD"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_user_email_conflict(superuser_client: AsyncClient, db_session: AsyncSession):
    """
    Test creating a user with an already existing email returns 409.
    """
    await UserFactory.acreate(db_session, email="existing@example.com")

    # Action: Try creating another user with the same email
    payload = {
        "name": "Another",
        "surname": "User",
        "email": "existing@example.com",
        "password": "Password123!"
    }
    response = await superuser_client.post("/api/v1/users/", json=payload)

    # Assert
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_user_unauthorized(client: AsyncClient):
    """
    Test that unauthenticated requests to create a user return 401.
    """
    payload = {
        "name": "Jane",
        "surname": "Doe",
        "email": "jane.doe@example.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/users/", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_user_forbidden_for_regular_user(verified_user_client: AsyncClient):
    """
    Test that regular (non-superuser) verified users cannot create a user (403).
    """
    payload = {
        "name": "Jane",
        "surname": "Doe",
        "email": "jane.doe@example.com",
        "password": "Password123!"
    }
    response = await verified_user_client.post("/api/v1/users/", json=payload)
    assert response.status_code == 403

