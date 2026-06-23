import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory

@pytest.mark.asyncio
async def test_update_user_success(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test partial update (PATCH) of own user profile.
    """
    user = verified_user_client.user

    payload = {
        "preferred_currency": "EUR",
        "telegram_id": "88888888"
    }

    response = await verified_user_client.patch(f"/api/v1/users/{user.id}", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["preferred_currency"] == "EUR"
    assert data["telegram_id"] == "88888888"
    assert data["email"] == user.email

@pytest.mark.asyncio
async def test_update_user_unauthenticated(client: AsyncClient, db_session: AsyncSession):
    """
    Test updating user profile without authentication.
    """
    user = await UserFactory.acreate(db_session)
    payload = {"preferred_currency": "EUR"}
    response = await client.patch(f"/api/v1/users/{user.id}", json=payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_update_user_forbidden(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test that updating someone else's user profile returns 403 Forbidden.
    """
    other_user = await UserFactory.acreate(db_session)
    payload = {"preferred_currency": "EUR"}
    response = await verified_user_client.patch(f"/api/v1/users/{other_user.id}", json=payload)
    assert response.status_code == 403
    assert "do not have permission" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_update_user_superuser(superuser_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a superuser can update any user's profile.
    """
    other_user = await UserFactory.acreate(db_session, preferred_currency="USD")
    payload = {"preferred_currency": "EUR"}
    response = await superuser_client.patch(f"/api/v1/users/{other_user.id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["preferred_currency"] == "EUR"
