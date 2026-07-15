import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import patch, AsyncMock
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import CurrencyEnum, SearchRunStatus
from src.domains.subscriptions.models import Subscription
from src.domains.search_runs.models import SearchRun
from src.domains.alerts.models import Alert
from src.domains.subscriptions.tasks import poll_all_active_subscriptions_task
from tests.factories import SubscriptionFactory


@pytest.mark.asyncio
async def test_poll_all_active_subscriptions_success(db_session: AsyncSession):
    """
    Test that poll_all_active_subscriptions_task selects only eligible active subscriptions,
    bulk updates their last_checked_at timestamp, dispatches jobs, and inserts SearchRun records.
    """
    # 0. Clean up pre-existing database rows to isolate this test
    await db_session.execute(delete(Alert))
    await db_session.execute(delete(SearchRun))
    await db_session.execute(delete(Subscription))
    await db_session.commit()

    # 1. Setup subscription records
    now = datetime.now(timezone.utc)

    # Sub 1: Eligible (active, has provider, last_checked_at is None)
    sub1 = await SubscriptionFactory.acreate(
        db_session,
        is_active=True,
        provider="apify_airbnb",
        last_checked_at=None,
        max_price=Decimal("150.00"),
        currency=CurrencyEnum.EUR
    )

    # Sub 2: Eligible (active, has provider, last_checked_at is older than 24 hours)
    sub2 = await SubscriptionFactory.acreate(
        db_session,
        is_active=True,
        provider="apify_airbnb",
        last_checked_at=now - timedelta(hours=25),
        max_price=Decimal("200.00"),
        currency=CurrencyEnum.EUR
    )

    # Sub 3: NOT Eligible (active, has provider, but checked recently)
    sub3 = await SubscriptionFactory.acreate(
        db_session,
        is_active=True,
        provider="apify_airbnb",
        last_checked_at=now - timedelta(hours=1),
        max_price=Decimal("100.00"),
        currency=CurrencyEnum.EUR
    )

    # Sub 4: NOT Eligible (inactive, has provider, last_checked_at is None)
    sub4 = await SubscriptionFactory.acreate(
        db_session,
        is_active=False,
        provider="apify_airbnb",
        last_checked_at=None,
        max_price=Decimal("300.00"),
        currency=CurrencyEnum.EUR
    )

    # Sub 5: NOT Eligible (active, but provider is None)
    sub5 = await SubscriptionFactory.acreate(
        db_session,
        is_active=True,
        provider=None,
        last_checked_at=None,
        max_price=Decimal("250.00"),
        currency=CurrencyEnum.EUR
    )

    await db_session.commit()

    # 2. Setup mock adapter and mock registry lookup
    mock_adapter = AsyncMock()
    mock_adapter.execution_mode = "async_webhook"
    mock_adapter.dispatch.side_effect = ["run-sub1", "run-sub2"]

    with patch("src.domains.subscriptions.tasks.get_adapter", return_value=mock_adapter) as mock_get_adapter:
        # Run the task directly
        await poll_all_active_subscriptions_task.original_func(db=db_session)

    # 3. Verify dispatch calls
    assert mock_get_adapter.call_count == 2
    from unittest.mock import ANY
    mock_adapter.dispatch.assert_any_call(ANY)

    # 4. Verify last_checked_at updates on subscriptions
    # Refresh subscriptions from DB
    await db_session.commit()
    for sub in [sub1, sub2]:
        res = await db_session.execute(select(Subscription).where(Subscription.id == sub.id))
        refreshed = res.scalar_one()
        assert refreshed.last_checked_at is not None
        assert refreshed.last_checked_at > now - timedelta(seconds=10)

    # Verify ineligible ones remain unchanged
    res3 = await db_session.execute(select(Subscription).where(Subscription.id == sub3.id))
    assert res3.scalar_one().last_checked_at == sub3.last_checked_at

    res4 = await db_session.execute(select(Subscription).where(Subscription.id == sub4.id))
    assert res4.scalar_one().last_checked_at is None

    res5 = await db_session.execute(select(Subscription).where(Subscription.id == sub5.id))
    assert res5.scalar_one().last_checked_at is None

    # 5. Verify SearchRun records created
    search_runs_res = await db_session.execute(
        select(SearchRun).where(SearchRun.subscription_id.in_([sub1.id, sub2.id]))
    )
    search_runs = search_runs_res.scalars().all()
    assert len(search_runs) == 2

    # Check search run details
    run_sub1 = next(r for r in search_runs if r.subscription_id == sub1.id)
    assert run_sub1.provider == "apify_airbnb"
    assert run_sub1.external_run_id == "run-sub1"
    assert run_sub1.status == SearchRunStatus.PENDING

    run_sub2 = next(r for r in search_runs if r.subscription_id == sub2.id)
    assert run_sub2.provider == "apify_airbnb"
    assert run_sub2.external_run_id == "run-sub2"
    assert run_sub2.status == SearchRunStatus.PENDING
