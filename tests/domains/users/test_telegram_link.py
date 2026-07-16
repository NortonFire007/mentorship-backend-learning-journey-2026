import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock
from src.main import app
from src.domains.auth.dependencies import get_redis
from src.core.config import settings
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_generate_telegram_link_success(verified_user_client: AsyncClient):
    """
    Test that an authenticated user can generate a Telegram deep link for their own account.
    Verifies that the token is stored in Redis with 15-minute TTL.
    """
    user = verified_user_client.user
    
    # Retrieve the mock Redis client from dependency overrides
    mock_redis = app.dependency_overrides[get_redis]()
    mock_redis.set = AsyncMock()

    response = await verified_user_client.post(f"/api/v1/users/{user.id}/telegram/link-start")
    
    assert response.status_code == 200
    data = response.json()
    assert "link" in data
    assert data["expires_in_seconds"] == 900
    
    # Verify the link matches the expected pattern
    expected_prefix = f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start="
    assert data["link"].startswith(expected_prefix)
    
    # Extract the generated token
    token = data["link"].split("?start=")[1]
    assert len(token) > 0
    
    # Verify mock Redis SET was called with the correct parameters
    mock_redis.set.assert_called_once_with(
        f"tg_link:{token}",
        str(user.id),
        ex=900
    )


@pytest.mark.asyncio
async def test_generate_telegram_link_forbidden_for_other_user(
    verified_user_client: AsyncClient, db_session: AsyncSession
):
    """
    Test that a user cannot generate a Telegram deep link for another user.
    """
    other_user = await UserFactory.acreate(db_session)
    
    response = await verified_user_client.post(f"/api/v1/users/{other_user.id}/telegram/link-start")
    assert response.status_code == 403
    assert "do not have permission" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_telegram_link_not_found(superuser_client: AsyncClient):
    """
    Test that trying to generate a deep link for a non-existent user returns 404.
    """
    non_existent_id = uuid.uuid4()
    response = await superuser_client.post(f"/api/v1/users/{non_existent_id}/telegram/link-start")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_telegram_link_unauthenticated(client: AsyncClient):
    """
    Test that an unauthenticated request to the link generation endpoint returns 401.
    """
    random_id = uuid.uuid4()
    response = await client.post(f"/api/v1/users/{random_id}/telegram/link-start")
    assert response.status_code == 401
