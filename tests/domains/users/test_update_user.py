import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory
from src.core.security.password import hash_password, verify_password

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


@pytest.mark.asyncio
async def test_change_password_success(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test successful password change.
    """
    user = verified_user_client.user
    user.password_hash = await hash_password("OldPassword123!")
    await db_session.commit()

    payload = {
        "old_password": "OldPassword123!",
        "new_password": "NewPassword456!"
    }
    
    response = await verified_user_client.post(
        f"/api/v1/users/{user.id}/change-password",
        json=payload
    )
    
    assert response.status_code == 204
    
    await db_session.refresh(user)
    assert await verify_password("NewPassword456!", user.password_hash)


@pytest.mark.asyncio
async def test_change_password_incorrect_old_password(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test password change with incorrect old password (returns 400).
    """
    user = verified_user_client.user
    user.password_hash = await hash_password("OldPassword123!")
    await db_session.commit()

    payload = {
        "old_password": "IncorrectPassword1!",
        "new_password": "NewPassword456!"
    }
    
    response = await verified_user_client.post(
        f"/api/v1/users/{user.id}/change-password",
        json=payload
    )
    
    assert response.status_code == 400
    assert "incorrect old password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_change_password_weak_new_password(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test password change with a new password that fails validation (returns 422).
    """
    user = verified_user_client.user
    user.password_hash = await hash_password("OldPassword123!")
    await db_session.commit()

    payload = {
        "old_password": "OldPassword123!",
        "new_password": "weak"
    }
    
    response = await verified_user_client.post(
        f"/api/v1/users/{user.id}/change-password",
        json=payload
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password_unauthenticated(client: AsyncClient, db_session: AsyncSession):
    """
    Test password change without authentication.
    """
    user = await UserFactory.acreate(db_session)
    payload = {
        "old_password": "OldPassword123!",
        "new_password": "NewPassword456!"
    }
    response = await client.post(f"/api/v1/users/{user.id}/change-password", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_forbidden_other_user(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test that changing someone else's password returns 403 Forbidden.
    """
    other_user = await UserFactory.acreate(db_session)
    payload = {
        "old_password": "OldPassword123!",
        "new_password": "NewPassword456!"
    }
    response = await verified_user_client.post(
        f"/api/v1/users/{other_user.id}/change-password",
        json=payload
    )
    assert response.status_code == 403
    assert "do not have permission" in response.json()["detail"].lower()

