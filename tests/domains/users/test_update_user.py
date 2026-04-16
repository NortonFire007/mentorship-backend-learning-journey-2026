import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory

@pytest.mark.asyncio
async def test_update_user_partial(client: AsyncClient, db_session: AsyncSession):
    """
    Test partial update (PATCH) of user profile.
    """
    user = await UserFactory.acreate(db_session, preferred_currency="USD")

    payload = {
        "preferred_currency": "EUR",
        "telegram_id": "88888888"
    }

    response = await client.patch(f"/api/v1/users/{user.id}", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["preferred_currency"] == "EUR"
    assert data["telegram_id"] == "88888888"
    assert data["email"] == user.email
