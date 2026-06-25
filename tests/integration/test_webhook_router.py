import uuid
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from src.core.enums import SearchRunStatus
from src.domains.search_runs.repository import SearchRunRepository
from tests.factories import UserFactory, SubscriptionFactory


@pytest.mark.asyncio
async def test_webhook_apify_invalid_token(client: AsyncClient):
    """
    Test that invalid token returns 403 Forbidden.
    """
    payload = {
        "eventType": "ACTOR.RUN.SUCCEEDED",
        "eventData": {
            "actorRunId": "run-123",
            "defaultDatasetId": "ds-456"
        }
    }
    with patch("src.core.config.settings.APIFY_WEBHOOK_SECRET", "secret123"):
        response = await client.post(
            "/api/v1/webhooks/apify?token=WRONG",
            json=payload
        )
    assert response.status_code == 403
    assert "Invalid token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_apify_succeeded_success(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    Test that valid token and succeeded event updates status and enqueues task.
    """
    user = await UserFactory.acreate(db_session)
    subscription = await SubscriptionFactory.acreate(db_session, user_id=user.id)

    # Create search run
    repo = SearchRunRepository(db_session)
    run_id = "run-succeeded-123"
    search_run = await repo.create(
        subscription_id=subscription.id,
        provider="apify_airbnb",
        external_run_id=run_id
    )
    await db_session.commit()

    payload = {
        "eventType": "ACTOR.RUN.SUCCEEDED",
        "eventData": {
            "actorRunId": run_id,
            "defaultDatasetId": "ds-succeeded-456"
        }
    }

    with patch("src.core.config.settings.APIFY_WEBHOOK_SECRET", "secret123"), \
         patch("src.domains.webhooks.router.evaluate_apify_results_task.kiq", new_callable=AsyncMock) as mock_kiq:
        
        response = await client.post(
            f"/api/v1/webhooks/apify?token=secret123",
            json=payload
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Webhook processed successfully"
        mock_kiq.assert_called_once_with(
            subscription_id=subscription.id,
            dataset_id="ds-succeeded-456"
        )

    # Verify status is updated in DB
    search_run_id = search_run.id
    db_session.expire_all()
    updated_run = await repo.get_by_id(search_run_id)
    assert updated_run.status == SearchRunStatus.COMPLETED
    assert updated_run.completed_at is not None


@pytest.mark.asyncio
async def test_webhook_apify_failed_success(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    Test that FAILED event updates status to FAILED and returns 200 without enqueuing task.
    """
    user = await UserFactory.acreate(db_session)
    subscription = await SubscriptionFactory.acreate(db_session, user_id=user.id)

    repo = SearchRunRepository(db_session)
    run_id = "run-failed-123"
    search_run = await repo.create(
        subscription_id=subscription.id,
        provider="apify_airbnb",
        external_run_id=run_id
    )
    await db_session.commit()

    payload = {
        "eventType": "ACTOR.RUN.FAILED",
        "eventData": {
            "actorRunId": run_id
        }
    }

    with patch("src.core.config.settings.APIFY_WEBHOOK_SECRET", "secret123"), \
         patch("src.domains.webhooks.router.evaluate_apify_results_task.kiq", new_callable=AsyncMock) as mock_kiq:
        
        response = await client.post(
            f"/api/v1/webhooks/apify?token=secret123",
            json=payload
        )
        
        assert response.status_code == 200
        mock_kiq.assert_not_called()

    # Verify status is updated to FAILED in DB
    search_run_id = search_run.id
    db_session.expire_all()
    updated_run = await repo.get_by_id(search_run_id)
    assert updated_run.status == SearchRunStatus.FAILED
    assert updated_run.completed_at is not None


@pytest.mark.asyncio
async def test_webhook_apify_unknown_run(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    Test that unknown run ID returns 404.
    """
    payload = {
        "eventType": "ACTOR.RUN.SUCCEEDED",
        "eventData": {
            "actorRunId": "unknown-run-id",
            "defaultDatasetId": "ds-456"
        }
    }

    with patch("src.core.config.settings.APIFY_WEBHOOK_SECRET", "secret123"), \
         patch("src.domains.webhooks.router.evaluate_apify_results_task.kiq", new_callable=AsyncMock) as mock_kiq:
        
        response = await client.post(
            "/api/v1/webhooks/apify?token=secret123",
            json=payload
        )
        
        assert response.status_code == 404
        mock_kiq.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_apify_duplicate_idempotent(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    Test duplicate delivery returns 200 and enqueues task only once (the first time).
    """
    user = await UserFactory.acreate(db_session)
    subscription = await SubscriptionFactory.acreate(db_session, user_id=user.id)

    repo = SearchRunRepository(db_session)
    run_id = "run-duplicate-123"
    search_run = await repo.create(
        subscription_id=subscription.id,
        provider="apify_airbnb",
        external_run_id=run_id
    )
    await db_session.commit()

    payload = {
        "eventType": "ACTOR.RUN.SUCCEEDED",
        "eventData": {
            "actorRunId": run_id,
            "defaultDatasetId": "ds-duplicate-456"
        }
    }

    with patch("src.core.config.settings.APIFY_WEBHOOK_SECRET", "secret123"), \
         patch("src.domains.webhooks.router.evaluate_apify_results_task.kiq", new_callable=AsyncMock) as mock_kiq:
        
        # First request
        res1 = await client.post(
            f"/api/v1/webhooks/apify?token=secret123",
            json=payload
        )
        assert res1.status_code == 200
        assert mock_kiq.call_count == 1

        # Second request (duplicate delivery)
        res2 = await client.post(
            f"/api/v1/webhooks/apify?token=secret123",
            json=payload
        )
        assert res2.status_code == 200
        assert mock_kiq.call_count == 1  # Still 1 call (idempotent)


@pytest.mark.asyncio
async def test_webhook_apify_internal_error_ignored(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    Test that internal DB exception is caught, logged, and 200 is returned.
    """
    payload = {
        "eventType": "ACTOR.RUN.SUCCEEDED",
        "eventData": {
            "actorRunId": "run-db-error",
            "defaultDatasetId": "ds-db-error"
        }
    }

    # Force search_run_repo.get_by_external_run_id to raise a database exception
    with patch("src.core.config.settings.APIFY_WEBHOOK_SECRET", "secret123"), \
         patch("src.domains.search_runs.repository.SearchRunRepository.get_by_external_run_id", side_effect=Exception("Database down")), \
         patch("src.domains.webhooks.router.evaluate_apify_results_task.kiq", new_callable=AsyncMock) as mock_kiq:
        
        response = await client.post(
            "/api/v1/webhooks/apify?token=secret123",
            json=payload
        )
        
        # Should return 200 to prevent retries
        assert response.status_code == 200
        assert response.json()["message"] == "Internal error occurred but acknowledged"
        mock_kiq.assert_not_called()
