import logging
from src.core.taskiq import rabbitmq_broker
from src.core.events.idempotency import idempotent_event

logger = logging.getLogger(__name__)


@rabbitmq_broker.task(
    task_name="notifications.digest.requested",
    retry_on_error=True,
    max_retries=3,
)
@idempotent_event
async def process_digest_requested_event(event_dict: dict) -> None:
    """
    Consumer task for processing DigestRequestedEvent.
    Deduplicated using Redis via the idempotent_event decorator.
    """
    logger.info(f"Successfully processed digest requested event: {event_dict}")
