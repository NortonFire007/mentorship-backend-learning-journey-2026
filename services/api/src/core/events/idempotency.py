import functools
import logging
from typing import Callable, Any
from redis.asyncio import Redis
from src.core.config import settings

logger = logging.getLogger(__name__)

# Lazy initialized Redis client for idempotency check
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

def idempotent_event(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for TaskIQ task handlers to ensure idempotent event execution.
    Uses Redis SETNX with a 24-hour TTL on 'processed_event:{event_id}'.
    Releases lock (deletes key) if execution raises an exception.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        event_id = None
        
        # Extract event_id safely from arguments
        if args:
            first_arg = args[0]
            if isinstance(first_arg, dict) and "event_id" in first_arg:
                event_id = str(first_arg["event_id"])
            elif hasattr(first_arg, "event_id"):
                event_id = str(first_arg.event_id)
                
        if not event_id:
            if "event_id" in kwargs:
                event_id = str(kwargs["event_id"])
            elif "event" in kwargs:
                event = kwargs["event"]
                if isinstance(event, dict) and "event_id" in event:
                    event_id = str(event["event_id"])
                elif hasattr(event, "event_id"):
                    event_id = str(event.event_id)

        if not event_id:
            logger.warning(f"idempotent_event: Could not extract event_id from function {func.__name__} arguments")
            return await func(*args, **kwargs)

        redis_key = f"processed_event:{event_id}"
        
        # Try to acquire lock using SETNX with 24-hour expiration (86400 seconds)
        # Atomically sets the key only if it does not already exist
        acquired = await redis_client.set(redis_key, "processing", nx=True, ex=86400)
        
        if not acquired:
            logger.info(f"Duplicate event ignored. Event {event_id} has already been processed or is being processed.")
            return None
            
        try:
            result = await func(*args, **kwargs)
            # Mark the event as completed successfully
            await redis_client.set(redis_key, "completed", keepttl=True)
            return result
        except Exception as e:
            # CRITICAL: Delete Redis lock key if task raises an exception so future retries can run
            logger.warning(f"Task failed for event {event_id}. Releasing idempotency lock. Error: {str(e)}")
            try:
                await redis_client.delete(redis_key)
            except Exception as delete_err:
                logger.error(f"Failed to delete idempotency key {redis_key} after failure: {str(delete_err)}")
            raise e

    return wrapper
