import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import taskiq_fastapi

from src.main import app
from src.core.taskiq import broker
from src.core.enums import SearchRunStatus
from src.domains.search_runs.models import SearchRun
from src.domains.search_runs.repository import SearchRunRepository
from src.domains.search_runs.tasks import cleanup_stale_search_runs_task
from tests.factories import SubscriptionFactory, UserFactory


@pytest.fixture(autouse=True)
def setup_taskiq_context():
    taskiq_fastapi.populate_dependency_context(broker, app)
    yield


@pytest.mark.asyncio
async def test_cleanup_stale_search_runs_task(db_session: AsyncSession):
    """
    Test that cleanup_stale_search_runs_task finds runs older than 60 minutes,
    marks them as FAILED, and leaves younger runs untouched.
    """
    user = await UserFactory.acreate(db_session)
    subscription = await SubscriptionFactory.acreate(db_session, user=user)
    
    repo = SearchRunRepository(db_session)
    
    # 1. Fresh pending run (should not be touched)
    fresh_run = await repo.create(
        subscription_id=subscription.id,
        provider="apify_airbnb",
        external_run_id="fresh-run"
    )
    
    # 2. Stale pending run (older than 60 mins -> should be failed)
    stale_run = await repo.create(
        subscription_id=subscription.id,
        provider="apify_airbnb",
        external_run_id="stale-run"
    )
    # Manually backdate created_at
    stale_run.created_at = datetime.now(timezone.utc) - timedelta(minutes=70)
    
    # 3. Stale completed run (already completed -> should not be touched)
    completed_run = await repo.create(
        subscription_id=subscription.id,
        provider="apify_airbnb",
        external_run_id="completed-run"
    )
    completed_run.status = SearchRunStatus.COMPLETED
    completed_run.created_at = datetime.now(timezone.utc) - timedelta(minutes=70)
    
    await db_session.commit()
    
    # Run the cleanup task directly
    await cleanup_stale_search_runs_task.original_func(db=db_session)
    
    # Refresh objects from DB
    await db_session.commit()
    
    res_fresh = await db_session.execute(select(SearchRun).where(SearchRun.id == fresh_run.id))
    assert res_fresh.scalar_one().status == SearchRunStatus.PENDING
    
    res_stale = await db_session.execute(select(SearchRun).where(SearchRun.id == stale_run.id))
    refreshed_stale = res_stale.scalar_one()
    assert refreshed_stale.status == SearchRunStatus.FAILED
    assert refreshed_stale.completed_at is not None
    
    res_completed = await db_session.execute(select(SearchRun).where(SearchRun.id == completed_run.id))
    assert res_completed.scalar_one().status == SearchRunStatus.COMPLETED
