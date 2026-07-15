import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
import uuid

from src.domains.auth.service import AuthService
from src.domains.auth.schemas import RegisterRequest
from src.domains.users.models import User
from src.core.security.jwt import decode_token
from src.domains.auth.repository import RefreshTokenRepository


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


@pytest.mark.asyncio
async def test_auth_service_refresh_success(db_session: AsyncSession):
    service = AuthService(db_session)
    reg_data = RegisterRequest(
        name="Refresh",
        surname="User",
        email="refresh.success@example.com",
        password="SecurePassword123!"
    )
    await service.register(reg_data)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    token_pair = await service.login(
        email="refresh.success@example.com",
        password="SecurePassword123!",
        redis_client=mock_redis
    )

    # Refresh
    new_pair = await service.refresh(
        refresh_token_str=token_pair.refresh_token,
        redis_client=mock_redis
    )

    assert new_pair.access_token is not None
    assert new_pair.refresh_token is not None
    assert new_pair.refresh_token != token_pair.refresh_token

    # Verify old token is marked as used
    old_payload = decode_token(token_pair.refresh_token)
    repo = RefreshTokenRepository(db_session)
    old_db_token = await repo.get_by_jti(uuid.UUID(old_payload["jti"]))
    assert old_db_token.is_used is True
    mock_redis.set.assert_called()  # pending cached result and blacklist


@pytest.mark.asyncio
async def test_auth_service_refresh_reuse_post_grace_period(db_session: AsyncSession):
    service = AuthService(db_session)
    reg_data = RegisterRequest(
        name="Reuse",
        surname="User",
        email="refresh.reuse@example.com",
        password="SecurePassword123!"
    )
    await service.register(reg_data)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    token_pair = await service.login(
        email="refresh.reuse@example.com",
        password="SecurePassword123!",
        redis_client=mock_redis
    )

    # First refresh (valid rotation)
    await service.refresh(
        refresh_token_str=token_pair.refresh_token,
        redis_client=mock_redis
    )

    # Manually backdate rotated_at in DB past grace period
    payload = decode_token(token_pair.refresh_token)
    jti = uuid.UUID(payload["jti"])
    repo = RefreshTokenRepository(db_session)
    db_token = await repo.get_by_jti(jti)
    db_token.rotated_at = datetime.now(timezone.utc) - timedelta(seconds=35)
    await db_session.commit()

    # Second refresh attempt should trigger reuse detection
    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(
            refresh_token_str=token_pair.refresh_token,
            redis_client=mock_redis
        )

    assert exc_info.value.status_code == 401
    assert "session compromised" in exc_info.value.detail

    # Verify family is revoked
    db_token = await repo.get_by_jti(jti)
    assert db_token.revoked_at is not None


@pytest.mark.asyncio
async def test_auth_service_refresh_reuse_within_grace_period(db_session: AsyncSession):
    service = AuthService(db_session)
    reg_data = RegisterRequest(
        name="Grace",
        surname="User",
        email="refresh.grace@example.com",
        password="SecurePassword123!"
    )
    await service.register(reg_data)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    token_pair = await service.login(
        email="refresh.grace@example.com",
        password="SecurePassword123!",
        redis_client=mock_redis
    )

    # First refresh
    first_new_pair = await service.refresh(
        refresh_token_str=token_pair.refresh_token,
        redis_client=mock_redis
    )

    # Second refresh within grace period (rotated_at is current time)
    second_new_pair = await service.refresh(
        refresh_token_str=token_pair.refresh_token,
        redis_client=mock_redis
    )

    # Should return the child token pair
    assert second_new_pair.access_token is not None
    # Compare refresh JTIs to ensure they point to same child
    child_payload1 = decode_token(first_new_pair.refresh_token)
    child_payload2 = decode_token(second_new_pair.refresh_token)
    assert child_payload1["jti"] == child_payload2["jti"]


@pytest.mark.asyncio
async def test_auth_service_logout_success(db_session: AsyncSession):
    service = AuthService(db_session)
    reg_data = RegisterRequest(
        name="Logout",
        surname="User",
        email="logout.success@example.com",
        password="SecurePassword123!"
    )
    await service.register(reg_data)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    token_pair = await service.login(
        email="logout.success@example.com",
        password="SecurePassword123!",
        redis_client=mock_redis
    )

    payload = decode_token(token_pair.access_token)
    access_jti = payload["jti"]
    access_exp = payload["exp"]

    # Call logout
    await service.logout(
        access_jti=access_jti,
        access_exp=access_exp,
        refresh_token_str=token_pair.refresh_token,
        redis_client=mock_redis
    )

    mock_redis.set.assert_called()

    refresh_payload = decode_token(token_pair.refresh_token)
    repo = RefreshTokenRepository(db_session)
    db_token = await repo.get_by_jti(uuid.UUID(refresh_payload["jti"]))
    assert db_token.revoked_at is not None


@pytest.mark.asyncio
async def test_auth_service_logout_all_success(db_session: AsyncSession):
    service = AuthService(db_session)
    user_db = await service.register(RegisterRequest(
        name="LogoutAll",
        surname="User",
        email="logoutall.success@example.com",
        password="SecurePassword123!"
    ))

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    pair1 = await service.login(
        email="logoutall.success@example.com",
        password="SecurePassword123!",
        redis_client=mock_redis
    )

    pair2 = await service.login(
        email="logoutall.success@example.com",
        password="SecurePassword123!",
        redis_client=mock_redis
    )

    payload = decode_token(pair1.access_token)
    access_jti = payload["jti"]
    access_exp = payload["exp"]

    await service.logout_all(
        user_id=user_db.id,
        access_jti=access_jti,
        access_exp=access_exp,
        redis_client=mock_redis
    )

    payload1 = decode_token(pair1.refresh_token)
    payload2 = decode_token(pair2.refresh_token)

    repo = RefreshTokenRepository(db_session)
    db_token1 = await repo.get_by_jti(uuid.UUID(payload1["jti"]))
    db_token2 = await repo.get_by_jti(uuid.UUID(payload2["jti"]))

    assert db_token1.revoked_at is not None
    assert db_token2.revoked_at is not None

