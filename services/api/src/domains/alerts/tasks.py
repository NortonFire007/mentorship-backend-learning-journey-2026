import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqEvents, TaskiqState, Context, TaskiqDepends
from aiogram import Bot

from src.core.taskiq import rabbitmq_broker
from src.core.events.idempotency import idempotent_event
from src.core.config import settings
from src.db.database import get_db

logger = logging.getLogger(__name__)


@rabbitmq_broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def setup_bot(state: TaskiqState) -> None:
    """
    Worker startup hook: initializes the aiogram Bot client instance
    and stores it in the TaskiqState singleton.
    """
    logger.info("Initializing Telegram Bot instance in TaskiqState...")
    state.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)


@rabbitmq_broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def teardown_bot(state: TaskiqState) -> None:
    """
    Worker shutdown hook: ensures the Bot singleton's HTTP session is cleanly closed.
    """
    logger.info("Closing Telegram Bot instance in TaskiqState...")
    if hasattr(state, "bot"):
        await state.bot.session.close()


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


@rabbitmq_broker.task(
    task_name="alerts.alert.created",
    retry_on_error=True,
    max_retries=3,
)
@idempotent_event
async def process_alert_created_event(
    event_dict: dict,
    context: Context = TaskiqDepends(),
    db: AsyncSession = TaskiqDepends(get_db)
) -> None:
    """
    Consumer task for processing AlertCreatedEvent.
    Delegates user fetching, formatting, and delivery to AlertService.
    """
    logger.info(f"Processing alert created event: {event_dict}")
    
    alert_id_str = event_dict.get("alert_id")
    user_id_str = event_dict.get("user_id")
    
    if not alert_id_str or not user_id_str:
        logger.warning("Event missing alert_id or user_id. Aborting.")
        return
        
    try:
        alert_id = uuid.UUID(alert_id_str)
        user_id = uuid.UUID(user_id_str)
    except ValueError as e:
        logger.warning(f"Invalid UUID in event_dict: {e}. Aborting.")
        return

    from src.domains.alerts.repository import AlertRepository
    from src.domains.alerts.service import AlertService
    
    alert_service = AlertService(AlertRepository(db), db)
    bot: Bot = context.state.bot

    await alert_service.process_and_send_alert(
        alert_id=alert_id,
        user_id=user_id,
        bot=bot
    )

