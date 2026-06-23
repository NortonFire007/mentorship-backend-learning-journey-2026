import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory

@pytest.mark.asyncio
async def test_get_user_success(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test fetching own user profile.
    """
    user = verified_user_client.user
    response = await verified_user_client.get(f"/api/v1/users/{user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user.email

@pytest.mark.asyncio
async def test_get_user_unauthenticated(client: AsyncClient, db_session: AsyncSession):
    """
    Test fetching user profile without authentication.
    """
    user = await UserFactory.acreate(db_session)
    response = await client.get(f"/api/v1/users/{user.id}")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_user_forbidden(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a regular user cannot fetch someone else's profile (returns 403).
    """
    other_user = await UserFactory.acreate(db_session)
    response = await verified_user_client.get(f"/api/v1/users/{other_user.id}")
    assert response.status_code == 403
    assert "do not have permission" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_get_user_superuser_access(superuser_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a superuser can fetch any user's profile.
    """
    other_user = await UserFactory.acreate(db_session)
    response = await superuser_client.get(f"/api/v1/users/{other_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == other_user.email

@pytest.mark.asyncio
async def test_get_user_superuser_not_found(superuser_client: AsyncClient):
    """
    Test that a superuser fetching a non-existent user profile returns 404.
    """
    response = await superuser_client.get(f"/api/v1/users/{uuid.uuid4()}")
    assert response.status_code == 404
