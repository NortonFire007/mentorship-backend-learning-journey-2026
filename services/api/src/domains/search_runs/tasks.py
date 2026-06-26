import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends

from src.core.taskiq import broker
from src.db.database import get_db
from src.domains.search_runs.repository import SearchRunRepository
from src.core.enums import SearchRunStatus

logger = logging.getLogger(__name__)


@broker.task(
    task_name="cleanup_stale_search_runs",
    schedule=[
        {
            "cron": "*/15 * * * *"
        }
    ]
)
async def cleanup_stale_search_runs_task(
    db: AsyncSession = TaskiqDepends(get_db)
) -> None:
    """
    Periodic task that finds pending search runs older than 60 minutes
    and marks them as FAILED.
    """
    logger.info("Starting cleanup of stale pending search runs...")
    
    search_run_repo = SearchRunRepository(db)
    
    # 1. Fetch search runs that have been pending for > 60 minutes
    stale_runs = await search_run_repo.list_stale_pending(older_than_minutes=60)
    
    if not stale_runs:
        logger.info("No stale pending search runs found.")
        return
        
    logger.info(f"Found {len(stale_runs)} stale pending search run(s) to fail.")
    
    # 2. Mark each run as FAILED
    for run in stale_runs:
        try:
            await search_run_repo.update_status(run, SearchRunStatus.FAILED)
            logger.info(f"Marked stale search run {run.id} (external ID: {run.external_run_id}) as FAILED.")
        except Exception as e:
            logger.error(f"Failed to update status for stale search run {run.id}: {str(e)}", exc_info=True)
            
    await db.commit()
    logger.info("Finished cleanup of stale pending search runs.")
