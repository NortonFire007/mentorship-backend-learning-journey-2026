import logging
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.enums import SearchRunStatus
from src.db.database import get_db
from src.domains.search_runs.dependencies import get_search_run_repository
from src.domains.search_runs.repository import SearchRunRepository
from src.domains.subscriptions.tasks import evaluate_apify_results_task
from src.domains.webhooks.schemas import ApifyWebhookPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/apify", status_code=status.HTTP_200_OK)
async def apify_webhook_endpoint(
    payload: ApifyWebhookPayload,
    token: str,
    search_run_repo: SearchRunRepository = Depends(get_search_run_repository),
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook callback endpoint for Apify actor run completion.
    """
    # 1. Token validation: compare query param token with settings.APIFY_WEBHOOK_SECRET
    if not settings.APIFY_WEBHOOK_SECRET or not secrets.compare_digest(token, settings.APIFY_WEBHOOK_SECRET):
        logger.warning("Unauthorized access attempt to Apify webhook: invalid or missing token.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid token"
        )

    try:
        run_id = payload.eventData.actorRunId
        event_type = payload.eventType
        
        # 2. Look up SearchRun
        search_run = await search_run_repo.get_by_external_run_id(run_id)
        if not search_run:
            logger.error(f"SearchRun with external_run_id '{run_id}' not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SearchRun with external_run_id '{run_id}' not found."
            )

        # 3. Process eventType
        if event_type == "ACTOR.RUN.SUCCEEDED":
            # Idempotency check: if already completed, do nothing and return HTTP 200
            if search_run.status == SearchRunStatus.COMPLETED:
                logger.info(f"SearchRun '{run_id}' already COMPLETED. Skipping duplicate callback.")
                return {"message": "Webhook processed successfully (duplicate)"}

            # Update status to COMPLETED
            await search_run_repo.update_status(search_run, SearchRunStatus.COMPLETED)
            
            # Commit immediately to database to ensure status is saved before enqueuing task
            await db.commit()

            # Enqueue the evaluation taskiq task
            dataset_id = payload.eventData.defaultDatasetId or ""
            await evaluate_apify_results_task.kiq(
                subscription_id=search_run.subscription_id,
                dataset_id=dataset_id
            )
            logger.info(f"SearchRun '{run_id}' marked COMPLETED. Evaluation task enqueued.")

        elif event_type == "ACTOR.RUN.FAILED":
            # Update status to FAILED
            await search_run_repo.update_status(search_run, SearchRunStatus.FAILED)
            await db.commit()
            logger.warning(f"SearchRun '{run_id}' marked FAILED via webhook.")

        return {"message": "Webhook processed successfully"}

    except HTTPException:
        # Re-raise HTTPExceptions so FastAPI can return 403 or 404
        raise
    except Exception as e:
        # Catch all unexpected errors (e.g. database errors) and return 200 to prevent retries
        logger.error(f"Unexpected error processing Apify webhook: {e}", exc_info=True)
        return {"message": "Internal error occurred but acknowledged"}
