import hashlib
import json
import logging
import redis.asyncio as redis
from typing import AsyncGenerator
from src.core.config import settings

logger = logging.getLogger(__name__)

# Global redis client instance
_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Initialize or return the global async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_AUTH_URL, decode_responses=True)
    return _redis_client


async def close_redis() -> None:
    """Close the global Redis client connection."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.close()
        except Exception as e:
            logger.warning("Error closing Redis client: %s", e)
        finally:
            _redis_client = None


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """FastAPI dependency yielding the async Redis client."""
    client = get_redis_client()
    yield client


def get_email_hash(email: str) -> str:
    """Generate SHA-256 hash of normalized email for privacy in Redis keys."""
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


async def blacklist_token(redis_client: redis.Redis, jti: str, token_type: str, ttl_seconds: int) -> None:
    """Blacklist a token JTI for a specified duration."""
    key = f"auth:blacklist:{token_type}:{jti}"
    if ttl_seconds > 0:
        try:
            await redis_client.set(key, "1", ex=ttl_seconds)
        except Exception as e:
            logger.warning("Redis blacklist_token failure: %s", e)


async def is_blacklisted(redis_client: redis.Redis, jti: str, token_type: str) -> bool:
    """Check if a token JTI is blacklisted in Redis (falls back to False on Redis error)."""
    key = f"auth:blacklist:{token_type}:{jti}"
    try:
        exists = await redis_client.exists(key)
        return exists > 0
    except Exception as e:
        logger.warning("Redis is_blacklisted check failure: %s", e)
        return False


async def increment_login_attempts(redis_client: redis.Redis, email: str) -> int:
    """Increment and return the login failure count for an email, with expiry window."""
    email_hash = get_email_hash(email)
    key = f"auth:ratelimit:login:{email_hash}"
    try:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, settings.LOGIN_LOCKOUT_MINUTES * 60)
        results = await pipe.execute()
        return int(results[0])
    except Exception as e:
        logger.warning("Redis increment_login_attempts failure: %s", e)
        return 0


async def get_login_attempts(redis_client: redis.Redis, email: str) -> int:
    """Get the current login attempt count for an email."""
    email_hash = get_email_hash(email)
    key = f"auth:ratelimit:login:{email_hash}"
    try:
        val = await redis_client.get(key)
        return int(val) if val else 0
    except Exception as e:
        logger.warning("Redis get_login_attempts failure: %s", e)
        return 0


async def clear_login_attempts(redis_client: redis.Redis, email: str) -> None:
    """Reset the login attempt count for an email (e.g., after successful login)."""
    email_hash = get_email_hash(email)
    key = f"auth:ratelimit:login:{email_hash}"
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.warning("Redis clear_login_attempts failure: %s", e)


async def acquire_refresh_lock(redis_client: redis.Redis, jti: str) -> bool:
    """Acquire a temporary distributed lock for concurrent refresh token protection."""
    key = f"auth:lock:refresh:{jti}"
    try:
        result = await redis_client.set(key, "1", ex=5, nx=True)
        return bool(result)
    except Exception as e:
        logger.warning("Redis acquire_refresh_lock failure: %s", e)
        # fallback to True/False based on grace period in DB (allow it to run)
        return False


async def get_pending_refresh(redis_client: redis.Redis, jti: str) -> dict | None:
    """Get the cached response of a pending/completed refresh operation."""
    key = f"auth:pending:refresh:{jti}"
    try:
        val = await redis_client.get(key)
        return json.loads(val) if val else None
    except Exception as e:
        logger.warning("Redis get_pending_refresh failure: %s", e)
        return None


async def set_pending_refresh(redis_client: redis.Redis, jti: str, token_pair: dict) -> None:
    """Cache the token pair result of a completed refresh rotation."""
    key = f"auth:pending:refresh:{jti}"
    try:
        await redis_client.set(key, json.dumps(token_pair), ex=10)
    except Exception as e:
        logger.warning("Redis set_pending_refresh failure: %s", e)
