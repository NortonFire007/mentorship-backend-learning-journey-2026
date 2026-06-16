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


@pytest.mark.asyncio
async def test_auth_service_login_success(db_session: AsyncSession):
    from unittest.mock import AsyncMock
    service = AuthService(db_session)
    reg_data = RegisterRequest(
        name="John",
        surname="Doe",
        email="john.doe@example.com",
        password="SecurePassword123!"
    )
    await service.register(reg_data)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    token_pair = await service.login(
        email="john.doe@example.com",
        password="SecurePassword123!",
        redis_client=mock_redis
    )

    assert token_pair.access_token is not None
    assert token_pair.refresh_token is not None
    mock_redis.delete.assert_called_once()  # clear_login_attempts


@pytest.mark.asyncio
async def test_auth_service_login_wrong_password(db_session: AsyncSession):
    from unittest.mock import AsyncMock, MagicMock
    service = AuthService(db_session)
    reg_data = RegisterRequest(
        name="John",
        surname="Doe",
        email="john.doe.wrong@example.com",
        password="SecurePassword123!"
    )
    await service.register(reg_data)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_pipeline = MagicMock()
    mock_pipeline.incr.return_value = mock_pipeline
    mock_pipeline.expire.return_value = mock_pipeline
    mock_pipeline.execute = AsyncMock(return_value=[1])
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    with pytest.raises(HTTPException) as exc_info:
        await service.login(
            email="john.doe.wrong@example.com",
            password="WrongPassword123!",
            redis_client=mock_redis
        )

    assert exc_info.value.status_code == 401
    assert "Invalid credentials" in exc_info.value.detail
    mock_pipeline.incr.assert_called_once()


@pytest.mark.asyncio
async def test_auth_service_login_non_existent_email(db_session: AsyncSession):
    from unittest.mock import AsyncMock
    service = AuthService(db_session)
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await service.login(
            email="nonexistent@example.com",
            password="SomePassword123!",
            redis_client=mock_redis
        )

    assert exc_info.value.status_code == 401
    assert "Invalid credentials" in exc_info.value.detail


@pytest.mark.asyncio
async def test_auth_service_login_inactive_user(db_session: AsyncSession):
    from unittest.mock import AsyncMock
    service = AuthService(db_session)
    reg_data = RegisterRequest(
        name="Inactive",
        surname="User",
        email="inactive@example.com",
        password="SecurePassword123!"
    )
    user = await service.register(reg_data)
    user.is_active = False
    await db_session.commit()

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await service.login(
            email="inactive@example.com",
            password="SecurePassword123!",
            redis_client=mock_redis
        )

    assert exc_info.value.status_code == 401
    assert "Account is disabled" in exc_info.value.detail


@pytest.mark.asyncio
async def test_auth_service_login_rate_limit(db_session: AsyncSession):
    from unittest.mock import AsyncMock
    service = AuthService(db_session)
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "5"

    with pytest.raises(HTTPException) as exc_info:
        await service.login(
            email="rate_limit@example.com",
            password="SecurePassword123!",
            redis_client=mock_redis
        )

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
