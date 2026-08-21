import uuid
import logging
from typing import Any

from src.db.database import AsyncSessionLocal, db_transaction
from src.domains.users.repository import UserRepository
from src.domains.subscriptions.repository import SubscriptionRepository
from src.domains.mcp_admin.server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def get_user_by_email(email: str) -> dict[str, Any] | str:
    """
    Retrieve a user's full profile given their email address.
    """
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_email(email)
        if not user:
            return f"User not found: {email}"

        return {
            "id": str(user.id),
            "name": user.name,
            "surname": user.surname,
            "email": user.email,
            "telegram_chat_id": user.telegram_chat_id,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "preferred_currency": user.preferred_currency.value if hasattr(user.preferred_currency, "value") else str(user.preferred_currency),
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }


@mcp.tool()
async def get_user_subscriptions(user_id: str) -> list[dict[str, Any]] | str:
    """
    Retrieve all subscriptions belonging to the specified user ID.
    """
    try:
        parsed_user_id = uuid.UUID(user_id)
    except ValueError:
        return f"Invalid user_id format: '{user_id}'. Must be a valid UUID."

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(parsed_user_id)
        if not user:
            return f"User not found: {user_id}"

        sub_repo = SubscriptionRepository(session)
        subscriptions = await sub_repo.list(user_id=parsed_user_id)

        return [
            {
                "id": str(sub.id),
                "origin": sub.origin,
                "destination": sub.destination,
                "is_active": sub.is_active,
                "max_price": str(sub.max_price),
                "currency": sub.currency.value if hasattr(sub.currency, "value") else str(sub.currency),
                "travel_type": sub.travel_type.value if hasattr(sub.travel_type, "value") else str(sub.travel_type),
                "last_checked_at": sub.last_checked_at.isoformat() if sub.last_checked_at else None,
            }
            for sub in subscriptions
        ]


@mcp.tool()
async def update_subscription_status(subscription_id: str, is_active: bool) -> dict[str, Any] | str:
    """
    Update the is_active status of a subscription using a database transaction.
    """
    try:
        parsed_sub_id = uuid.UUID(subscription_id)
    except ValueError:
        return f"Invalid subscription_id format: '{subscription_id}'. Must be a valid UUID."

    async with db_transaction() as session:
        sub_repo = SubscriptionRepository(session)
        sub = await sub_repo.get_by_id(parsed_sub_id)
        if not sub:
            return f"Subscription not found: {subscription_id}"

        sub.is_active = is_active
        await session.flush()

        logger.info(f"MCP Admin updated subscription {subscription_id} status to is_active={is_active}")
        return {
            "status": "updated",
            "subscription_id": str(sub.id),
            "is_active": sub.is_active,
        }
