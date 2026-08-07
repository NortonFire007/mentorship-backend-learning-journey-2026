import uuid
import logging
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.exc import IntegrityError

from src.core.security.redis_auth import get_redis_client
from src.db.database import db_transaction
from src.domains.users.repository import UserRepository

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def start_handler(message: Message, command: CommandObject):
    token = command.args
    if not token:
        onboarding_text = (
            "👋 Welcome to the Mentorship Price Alert Bot!\n\n"
            "To connect your account and receive real-time price alerts, "
            "please click the link button in the Mentorship web application."
        )
        await message.answer(onboarding_text)
        return

    # A token was provided: consume it atomically via Redis GETDEL
    redis_client = get_redis_client()
    try:
        user_id_str = await redis_client.getdel(f"tg_link:{token}")
    except Exception as e:
        logger.exception("Redis error while retrieving deep link token: %s", str(e))
        await message.answer("⚠️ An error occurred while checking the link. Please try again later.")
        return

    if not user_id_str:
        await message.answer("⚠️ This link has expired or has already been used. Please request a new one from the app.")
        return

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        logger.error(f"Invalid UUID token payload retrieved from Redis: {user_id_str}")
        await message.answer("⚠️ An error occurred while linking your account. Please try again.")
        return

    telegram_chat_id = message.from_user.id

    try:
        async with db_transaction() as session:
            repo = UserRepository(session)
            user = await repo.get_by_id(user_id)
            if not user:
                await message.answer("⚠️ Mentorship account not found.")
                return

            if user.telegram_chat_id == telegram_chat_id:
                await message.answer("✅ Your Telegram account is already linked to this Mentorship account.")
                return

            user.telegram_chat_id = telegram_chat_id
    except IntegrityError:
        logger.warning(
            f"IntegrityError: Telegram chat ID {telegram_chat_id} is already linked to another user."
        )
        await message.answer("⚠️ This Telegram account is already linked to a different Mentorship account.")
        return
    except Exception as e:
        logger.exception("Unexpected error during account linking: %s", str(e))
        await message.answer("⚠️ An unexpected error occurred. Please try again later.")
        return

    await message.answer("✅ Your account is now connected! You will receive price alerts here.")
