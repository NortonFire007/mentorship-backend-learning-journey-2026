import pytest
import uuid
from unittest.mock import patch
from src.core.events.idempotency import idempotent_event

class MockAsyncRedis:
    """
    In-memory mock of the Redis client for reliable, dependency-free testing.
    """
    def __init__(self):
        self.store = {}

    async def set(self, key: str, value: str, nx: bool = False, ex: int | None = None, keepttl: bool = False) -> bool:
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, key: str) -> int:
        if key in self.store:
            del self.store[key]
            return 1
        return 0

    async def exists(self, key: str) -> int:
        return 1 if key in self.store else 0


@pytest.fixture()
def mock_redis():
    """
    Fixture patching the global redis_client with an in-memory mock.
    """
    mock_client = MockAsyncRedis()
    with patch("src.core.events.idempotency.redis_client", mock_client):
        yield mock_client


@idempotent_event
async def dummy_task(event_dict: dict) -> str:
    """
    Dummy task function wrapped in the idempotent_event decorator for testing.
    """
    if event_dict.get("should_fail"):
        raise ValueError("Simulated task failure")
    return "processed"


@pytest.mark.asyncio
async def test_idempotent_event_deduplication(mock_redis):
    """
    Asserts that the first task execution succeeds and creates a Redis lock key,
    while subsequent executions with the same event_id are ignored.
    """
    event_id = str(uuid.uuid4())
    event_dict = {"event_id": event_id, "should_fail": False}

    res1 = await dummy_task(event_dict)
    assert res1 == "processed"

    # Second execution with the same event_id should be ignored and return None
    res2 = await dummy_task(event_dict)
    assert res2 is None

    # Verify that the lock key was set to "completed" in Redis
    redis_key = f"processed_event:{event_id}"
    status = await mock_redis.get(redis_key)
    assert status == "completed"


@pytest.mark.asyncio
async def test_idempotent_event_failure_releases_lock(mock_redis):
    """
    Asserts that if the task execution fails, the Redis lock key is deleted
    so that subsequent retries of the task can run.
    """
    event_id = str(uuid.uuid4())
    event_dict = {"event_id": event_id, "should_fail": True}

    with pytest.raises(ValueError, match="Simulated task failure"):
        await dummy_task(event_dict)

    redis_key = f"processed_event:{event_id}"
    exists = await mock_redis.exists(redis_key)
    assert not exists
