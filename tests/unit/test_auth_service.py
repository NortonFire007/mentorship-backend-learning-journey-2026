import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.auth.service import AuthService
from src.domains.auth.schemas import RegisterRequest
from src.domains.users.models import User


@pytest.mark.asyncio
async def test_auth_service_register_success(db_session: AsyncSession):
    service = AuthService(db_session)
    data = RegisterRequest(
        name="Alice",
        surname="Smith",
        email="alice.smith@example.com",
        password="SecurePassword123!"
    )

    user = await service.register(data)

    assert user.name == "Alice"
    assert user.surname == "Smith"
    assert user.email == "alice.smith@example.com"
    assert user.auth_provider == "local"
    assert user.password_hash is not None
    assert user.is_verified is False

    # Check database persistency
    result = await db_session.execute(
        select(User).where(User.email == "alice.smith@example.com")
    )
    db_user = result.scalar_one_or_none()
    assert db_user is not None
    assert db_user.id == user.id


@pytest.mark.asyncio
async def test_auth_service_register_duplicate_email(db_session: AsyncSession):
    service = AuthService(db_session)
    data1 = RegisterRequest(
        name="Alice",
        surname="Smith",
        email="duplicate@example.com",
        password="SecurePassword123!"
    )
    data2 = RegisterRequest(
        name="Bob",
        surname="Jones",
        email="duplicate@example.com",
        password="AnotherSecurePassword123!"
    )

    # First registration should succeed
    await service.register(data1)

    # Second registration with duplicate email should raise 409 HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await service.register(data2)

    assert exc_info.value.status_code == 409
    assert "already registered" in exc_info.value.detail
