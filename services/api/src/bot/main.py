import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher

from src.core.config import settings
from src.core.security.redis_auth import close_redis
from src.bot.handlers.start import router as start_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main():
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN is not configured! Exiting...")
        sys.exit(1)

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start_router)

    logger.info("Starting Telegram bot polling...")
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Polling loop cancelled.")
    except Exception as e:
        logger.exception("Unexpected error in polling loop: %s", str(e))
    finally:
        logger.info("Shutting down Telegram bot session...")
        await bot.session.close()
        await close_redis()
        logger.info("Cleanup completed, exiting.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot process stopped.")
