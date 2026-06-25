import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import SearchRunStatus
from src.domains.search_runs.repository import SearchRunRepository
from tests.factories import UserFactory, SubscriptionFactory


@pytest.mark.asyncio
async def test_search_run_repository_lifecycle(db_session: AsyncSession):
    repo = SearchRunRepository(db_session)
    user = await UserFactory.acreate(db_session)
    subscription = await SubscriptionFactory.acreate(db_session, user_id=user.id)

    # 1. Test Create
    provider = "apify_airbnb"
    external_run_id = "run-12345"
    run = await repo.create(
        subscription_id=subscription.id,
        provider=provider,
        external_run_id=external_run_id
    )
    await db_session.commit()

    assert run.id is not None
    assert run.subscription_id == subscription.id
    assert run.provider == provider
    assert run.external_run_id == external_run_id
    assert run.status == SearchRunStatus.PENDING
    assert run.created_at is not None
    assert run.completed_at is None

    # 2. Test get_by_external_run_id
    fetched = await repo.get_by_external_run_id(external_run_id)
    assert fetched is not None
    assert fetched.id == run.id

    assert await repo.get_by_external_run_id("nonexistent") is None

    # 3. Test get_by_id
    fetched_by_id = await repo.get_by_id(run.id)
    assert fetched_by_id is not None
    assert fetched_by_id.id == run.id

    # 4. Test update_status
    updated = await repo.update_status(run, SearchRunStatus.COMPLETED)
    await db_session.commit()
    
    # Save ID and expire to reload from DB
    run_id = run.id
    db_session.expire_all()

    fetched_after_update = await repo.get_by_id(run_id)
    assert fetched_after_update.status == SearchRunStatus.COMPLETED
    assert fetched_after_update.completed_at is not None


@pytest.mark.asyncio
async def test_search_run_repository_list_stale_pending(db_session: AsyncSession):
    repo = SearchRunRepository(db_session)
    user = await UserFactory.acreate(db_session)
    subscription = await SubscriptionFactory.acreate(db_session, user_id=user.id)

    # Create a fresh run (created now)
    fresh_run = await repo.create(
        subscription_id=subscription.id,
        provider="apify_airbnb",
        external_run_id="fresh-run"
    )

    # Create a stale run (manually backdate created_at)
    stale_run = await repo.create(
        subscription_id=subscription.id,
        provider="apify_airbnb",
        external_run_id="stale-run"
    )
    stale_run.created_at = datetime.now(timezone.utc) - timedelta(minutes=90)
    
    completed_old_run = await repo.create(
        subscription_id=subscription.id,
        provider="apify_airbnb",
        external_run_id="completed-old-run"
    )
    completed_old_run.status = SearchRunStatus.COMPLETED
    completed_old_run.created_at = datetime.now(timezone.utc) - timedelta(minutes=90)

    await db_session.commit()

    stale_runs = await repo.list_stale_pending(older_than_minutes=60)
    stale_ids = [r.id for r in stale_runs]

    assert stale_run.id in stale_ids
    assert fresh_run.id not in stale_ids
    assert completed_old_run.id not in stale_ids
