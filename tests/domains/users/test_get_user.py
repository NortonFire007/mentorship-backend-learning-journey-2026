import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory

@pytest.mark.asyncio
async def test_get_user_success(client: AsyncClient, db_session: AsyncSession):
    """
    Test fetching an existing user profile.
    """
    user = await UserFactory.acreate(db_session)

    response = await client.get(f"/api/v1/users/{user.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user.email

@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    """
    Test fetching a non-existent user returns 404.
    """
    response = await client.get(f"/api/v1/users/{uuid.uuid4()}")
    assert response.status_code == 404
