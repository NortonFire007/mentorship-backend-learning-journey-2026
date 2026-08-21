import uuid
import logging
from typing import Any

from src.db.database import AsyncSessionLocal
from src.domains.subscriptions.repository import SubscriptionRepository
from src.domains.search_runs.repository import SearchRunRepository
from src.domains.alerts.repository import AlertRepository
from src.domains.subscriptions.tasks import trigger_subscription_sync_task
from src.domains.mcp_admin.server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def get_recent_search_runs(subscription_id: str, limit: int = 10) -> list[dict[str, Any]] | str:
    """
    Retrieve the most recent SearchRun records for a given subscription.
    """
    try:
        parsed_sub_id = uuid.UUID(subscription_id)
    except ValueError:
        return f"Invalid subscription_id format: '{subscription_id}'. Must be a valid UUID."

    async with AsyncSessionLocal() as session:
        search_run_repo = SearchRunRepository(session)
        runs = await search_run_repo.list_by_subscription_id(parsed_sub_id, limit=limit)

        return [
            {
                "id": str(run.id),
                "status": run.status.value if hasattr(run.status, "value") else str(run.status),
                "provider": run.provider,
                "external_run_id": run.external_run_id,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            }
            for run in runs
        ]


@mcp.tool()
async def get_alert_history(subscription_id: str, limit: int = 10) -> list[dict[str, Any]] | str:
    """
    Retrieve alert delivery history for a given subscription.
    """
    try:
        parsed_sub_id = uuid.UUID(subscription_id)
    except ValueError:
        return f"Invalid subscription_id format: '{subscription_id}'. Must be a valid UUID."

    async with AsyncSessionLocal() as session:
        alert_repo = AlertRepository(session)
        alerts = await alert_repo.get_by_subscription(parsed_sub_id, limit=limit)

        return [
            {
                "id": str(alert.id),
                "price_found": str(alert.price_found),
                "status": alert.status.value if hasattr(alert.status, "value") else str(alert.status),
                "image_url": alert.image_url,
                "deep_link": alert.deep_link,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            }
            for alert in alerts
        ]


@mcp.tool()
async def trigger_apify_sync(subscription_id: str) -> dict[str, Any] | str:
    """
    Enqueue an on-demand sync Taskiq task for a specific active subscription.
    """
    try:
        parsed_sub_id = uuid.UUID(subscription_id)
    except ValueError:
        return f"Invalid subscription_id format: '{subscription_id}'. Must be a valid UUID."

    async with AsyncSessionLocal() as session:
        sub_repo = SubscriptionRepository(session)
        sub = await sub_repo.get_by_id(parsed_sub_id)
        if not sub:
            return f"Subscription not found: {subscription_id}"

        if not sub.is_active:
            return f"Subscription {subscription_id} is inactive."

    # Enqueue Taskiq task
    task = await trigger_subscription_sync_task.kiq(parsed_sub_id)

    logger.info(f"MCP Admin triggered apify sync for subscription {subscription_id}, task_id: {task.task_id}")
    return {
        "status": "queued",
        "subscription_id": str(sub.id),
        "task_id": str(task.task_id),
    }
