import json
from unittest.mock import AsyncMock
import pytest
from src.core.security.redis_auth import (
    blacklist_token,
    is_blacklisted,
    increment_login_attempts,
    get_login_attempts,
    clear_login_attempts,
    acquire_refresh_lock,
    get_pending_refresh,
    set_pending_refresh,
)


@pytest.mark.asyncio
async def test_blacklist_token():
    mock_redis = AsyncMock()
    await blacklist_token(mock_redis, "test-jti", "access", 900)
    mock_redis.set.assert_called_once_with("auth:blacklist:access:test-jti", "1", ex=900)


@pytest.mark.asyncio
async def test_is_blacklisted():
    mock_redis = AsyncMock()
    mock_redis.exists.return_value = 1

    res = await is_blacklisted(mock_redis, "test-jti", "access")
    assert res is True
    mock_redis.exists.assert_called_once_with("auth:blacklist:access:test-jti")

    mock_redis.exists.reset_mock()
    mock_redis.exists.return_value = 0
    res = await is_blacklisted(mock_redis, "test-jti", "access")
    assert res is False


@pytest.mark.asyncio
async def test_increment_login_attempts():
    from unittest.mock import MagicMock
    mock_redis = AsyncMock()
    mock_pipeline = MagicMock()
    mock_pipeline.incr.return_value = mock_pipeline
    mock_pipeline.expire.return_value = mock_pipeline
    mock_pipeline.execute = AsyncMock(return_value=[3])
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    res = await increment_login_attempts(mock_redis, "user@example.com")
    assert res == 3
    mock_pipeline.incr.assert_called_once()
    mock_pipeline.expire.assert_called_once()
    mock_pipeline.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_login_attempts():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "5"

    res = await get_login_attempts(mock_redis, "user@example.com")
    assert res == 5

    mock_redis.get.return_value = None
    res = await get_login_attempts(mock_redis, "user@example.com")
    assert res == 0


@pytest.mark.asyncio
async def test_clear_login_attempts():
    mock_redis = AsyncMock()
    await clear_login_attempts(mock_redis, "user@example.com")
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_acquire_refresh_lock():
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True

    res = await acquire_refresh_lock(mock_redis, "test-jti")
    assert res is True
    mock_redis.set.assert_called_once_with("auth:lock:refresh:test-jti", "1", ex=5, nx=True)


@pytest.mark.asyncio
async def test_get_pending_refresh():
    mock_redis = AsyncMock()
    token_pair = {"access_token": "foo", "refresh_token": "bar"}
    mock_redis.get.return_value = json.dumps(token_pair)

    res = await get_pending_refresh(mock_redis, "test-jti")
    assert res == token_pair

    mock_redis.get.return_value = None
    res = await get_pending_refresh(mock_redis, "test-jti")
    assert res is None


@pytest.mark.asyncio
async def test_set_pending_refresh():
    mock_redis = AsyncMock()
    token_pair = {"access_token": "foo", "refresh_token": "bar"}

    await set_pending_refresh(mock_redis, "test-jti", token_pair)
    mock_redis.set.assert_called_once_with(
        "auth:pending:refresh:test-jti", json.dumps(token_pair), ex=10
    )
