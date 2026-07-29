import uuid
import html
import logging
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.core.enums import AlertStatus
from src.domains.alerts.models import Alert
from src.domains.alerts.repository import AlertRepository
from src.domains.alerts.schemas import AlertCreate
from src.domains.users.models import User
from src.domains.subscriptions.models import Subscription

logger = logging.getLogger(__name__)


def _is_valid_field(value: any) -> bool:
    if value is None:
        return False
    val_str = str(value).strip()
    if not val_str:
        return False
    if val_str.lower() in ("string", "none", "null"):
        return False
    return True


class AlertService:
    def __init__(self, repository: AlertRepository, session: AsyncSession):
        self.repository = repository
        self.session = session

    async def create_alert(self, alert_data: AlertCreate) -> Alert:
        """
        Create a new alert.
        """
        return await self.repository.create(alert_data)

    async def get_subscription_alerts(self, subscription_id: uuid.UUID, limit: int = 10) -> Sequence[Alert]:
        """
        Get alerts for a specific subscription.
        """
        return await self.repository.get_by_subscription(subscription_id, limit)

    async def get_latest_alerts(self, subscription_ids: list[uuid.UUID]) -> Sequence[Alert]:
        """
        Get latest alert for multiple subscriptions.
        """
        return await self.repository.get_latest_alerts_by_subscription_ids(subscription_ids)

    def format_alert_message(self, subscription: Subscription, alert: Alert) -> str:
        """
        Builds a user-friendly HTML message for the Telegram alert.
        Omits any fields that are empty or have default values (e.g. 'string', 'None').
        """
        message_lines = ["🔔 <b>New Price Alert Found!</b>", ""]

        if _is_valid_field(subscription.destination):
            escaped_destination = html.escape(str(subscription.destination))
            message_lines.append(f"📍 <b>Destination:</b> {escaped_destination}")

        if _is_valid_field(subscription.origin):
            escaped_origin = html.escape(str(subscription.origin))
            message_lines.append(f"🛫 <b>From:</b> {escaped_origin}")

        # Price is always present and should always be shown
        escaped_price = html.escape(f"{alert.price_found:.2f}")
        currency_val = subscription.currency.value if hasattr(subscription.currency, "value") else subscription.currency
        if _is_valid_field(currency_val):
            escaped_currency = html.escape(str(currency_val))
            message_lines.append(f"💰 <b>Price:</b> <code>{escaped_price} {escaped_currency}</code>")
        else:
            message_lines.append(f"💰 <b>Price:</b> <code>{escaped_price}</code>")

        # Dates
        if subscription.start_date and subscription.end_date:
            dates_str = f"{subscription.start_date} to {subscription.end_date}"
        elif subscription.start_date:
            dates_str = f"From {subscription.start_date}"
        elif subscription.duration_days:
            dates_str = f"{subscription.duration_days} days"
        else:
            dates_str = "Flexible dates"

        if _is_valid_field(dates_str):
            escaped_dates = html.escape(dates_str)
            message_lines.append(f"📅 <b>Dates:</b> {escaped_dates}")

        # Travel Type
        travel_type_val = subscription.travel_type.value if hasattr(subscription.travel_type, "value") else subscription.travel_type
        if _is_valid_field(travel_type_val):
            escaped_travel_type = html.escape(str(travel_type_val).capitalize())
            message_lines.append(f"🎫 <b>Type:</b> {escaped_travel_type}")

        return "\n".join(message_lines) + "\n"

    async def process_and_send_alert(
        self,
        alert_id: uuid.UUID,
        user_id: uuid.UUID,
        bot: Bot,
    ) -> None:
        """
        Processes alert event, formats notification message, and delivers it via Telegram.
        Updates alert status appropriately.
        """
        user_stmt = select(User).where(User.id == user_id)
        user_res = await self.session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User {user_id} not found in database. Aborting alert processing.")
            return

        # Fetch Alert with subscription eagerly loaded
        alert_stmt = select(Alert).where(Alert.id == alert_id).options(selectinload(Alert.subscription))
        alert_res = await self.session.execute(alert_stmt)
        alert = alert_res.scalar_one_or_none()
        
        if not alert:
            logger.warning(f"Alert {alert_id} not found in database. Aborting alert processing.")
            return

        if user.telegram_chat_id is None:
            logger.info(f"User {user_id} does not have a telegram_chat_id linked. Skipping alert delivery.")
            alert.status = AlertStatus.SKIPPED
            await self.session.commit()
            return

        subscription = alert.subscription
        if not subscription:
            sub_stmt = select(Subscription).where(Subscription.id == alert.subscription_id)
            sub_res = await self.session.execute(sub_stmt)
            subscription = sub_res.scalar_one_or_none()
            if not subscription:
                logger.warning(f"Subscription {alert.subscription_id} not found for alert {alert_id}. Aborting.")
                return

        html_text = self.format_alert_message(subscription, alert)

        # Inline button keyboard markup
        keyboard = None
        if alert.deep_link:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔗 View Listing",
                            url=alert.deep_link
                        )
                    ]
                ]
            )

        # Attempt message delivery
        try:
            if alert.image_url:
                try:
                    await bot.send_photo(
                        chat_id=user.telegram_chat_id,
                        photo=alert.image_url,
                        caption=html_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                except TelegramBadRequest as photo_err:
                    logger.warning(
                        f"Failed sending photo for alert {alert.id} due to TelegramBadRequest ({photo_err}). "
                        "Falling back to text-only send_message."
                    )
                    await bot.send_message(
                        chat_id=user.telegram_chat_id,
                        text=html_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            else:
                await bot.send_message(
                    chat_id=user.telegram_chat_id,
                    text=html_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
            alert.status = AlertStatus.SENT
            await self.session.commit()
            logger.info(f"Successfully sent Telegram alert for alert {alert.id} to user {user.id}")

        except TelegramForbiddenError as e:
            # User blocked the bot: set telegram_chat_id = None and alert.status = FAILED
            logger.warning(f"User {user.id} has blocked the bot. Removing telegram_chat_id. Error: {e}")
            alert.status = AlertStatus.FAILED
            user.telegram_chat_id = None
            await self.session.commit()
            
        except TelegramBadRequest as e:
            # Invalid chat or parsing error: set status = FAILED and user.telegram_chat_id = None
            logger.warning(f"TelegramBadRequest for user {user.id}. Removing telegram_chat_id. Error: {e}")
            alert.status = AlertStatus.FAILED
            user.telegram_chat_id = None
            await self.session.commit()

        except TelegramRetryAfter as e:
            # Rate-limited: re-raise to trigger retry policy
            logger.warning(f"Telegram rate limited (retry after {e.retry_after}s). Re-raising to trigger task retry.")
            raise
            
        except Exception as e:
            # Unexpected error: log and re-raise to retry
            logger.error(f"Unexpected error sending Telegram alert for alert {alert.id}: {e}", exc_info=True)
            raise
