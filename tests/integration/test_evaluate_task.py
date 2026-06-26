import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import TravelType, CurrencyEnum
from src.adapters.base import PriceResult
from src.domains.alerts.models import Alert
from src.core.events.events import AlertCreatedEvent
from src.core.events.dispatcher import EventDispatcher
from src.domains.subscriptions.tasks import evaluate_apify_results_task
from tests.factories import UserFactory, SubscriptionFactory
from tests.mocks.event_bus import MockEventPublisher


@pytest.mark.asyncio
async def test_evaluate_task_price_match(db_session: AsyncSession):
    """
    Test that when a price match is found (price <= max_price and currency matches),
    exactly one alert is created, image_url is stored, and AlertCreatedEvent is dispatched.
    """
    user = await UserFactory.acreate(db_session)
    subscription = await SubscriptionFactory.acreate(
        db_session,
        user=user,
        max_price=Decimal("250.00"),
        currency=CurrencyEnum.EUR,
        provider="apify_airbnb",
        is_active=True
    )
    await db_session.commit()

    # Mock adapter fetch_dataset
    mock_price_result = PriceResult(
        provider="apify_airbnb",
        origin="PAR",
        destination=subscription.destination,
        travel_type=TravelType.HOTEL,
        price=Decimal("200.00"),
        currency=CurrencyEnum.EUR,
        departure_date=None,
        return_date=None,
        deep_link="http://airbnb/123",
        image_url="http://img/1"
    )

    mock_adapter = AsyncMock()
    mock_adapter.fetch_dataset.return_value = [mock_price_result]

    # Setup mock event publisher
    mock_publisher = MockEventPublisher()
    dispatcher = EventDispatcher(mock_publisher)
    dispatcher.setup_session(db_session)

    with patch("src.domains.subscriptions.tasks.get_adapter", return_value=mock_adapter):
        await evaluate_apify_results_task.original_func(
            subscription_id=subscription.id,
            dataset_id="ds-123",
            db=db_session
        )

    # Extract events first, before any session queries
    events = dispatcher.extract_events(db_session)

    # Verify alert created in DB
    stmt = select(Alert).where(Alert.subscription_id == subscription.id)
    res = await db_session.execute(stmt)
    alerts = res.scalars().all()
    
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.price_found == Decimal("200.00")
    assert alert.image_url == "http://img/1"

    # Verify event extracted
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, AlertCreatedEvent)
    assert event.alert_id == alert.id
    assert event.subscription_id == subscription.id
    assert event.user_id == user.id
    assert event.price_found == Decimal("200.00")
    assert event.currency == "EUR"
    assert event.deep_link == "http://airbnb/123"
    assert event.image_url == "http://img/1"


@pytest.mark.asyncio
async def test_evaluate_task_price_too_high(db_session: AsyncSession):
    """
    Test that when price > max_price, no alert is created.
    """
    user = await UserFactory.acreate(db_session)
    subscription = await SubscriptionFactory.acreate(
        db_session,
        user_id=user.id,
        max_price=Decimal("250.00"),
        currency=CurrencyEnum.EUR,
        provider="apify_airbnb",
        is_active=True
    )
    await db_session.commit()

    mock_price_result = PriceResult(
        provider="apify_airbnb",
        origin="PAR",
        destination=subscription.destination,
        travel_type=TravelType.HOTEL,
        price=Decimal("300.00"),
        currency=CurrencyEnum.EUR,
        departure_date=None,
        return_date=None,
        deep_link="http://airbnb/123",
        image_url="http://img/1"
    )

    mock_adapter = AsyncMock()
    mock_adapter.fetch_dataset.return_value = [mock_price_result]

    with patch("src.domains.subscriptions.tasks.get_adapter", return_value=mock_adapter):
        await evaluate_apify_results_task.original_func(
            subscription_id=subscription.id,
            dataset_id="ds-123",
            db=db_session
        )

    # Verify no alert created in DB
    stmt = select(Alert).where(Alert.subscription_id == subscription.id)
    res = await db_session.execute(stmt)
    alerts = res.scalars().all()
    assert len(alerts) == 0


@pytest.mark.asyncio
async def test_evaluate_task_currency_mismatch(db_session: AsyncSession):
    """
    Test that when currency does not match, no alert is created.
    """
    user = await UserFactory.acreate(db_session)
    subscription = await SubscriptionFactory.acreate(
        db_session,
        user_id=user.id,
        max_price=Decimal("250.00"),
        currency=CurrencyEnum.EUR,
        provider="apify_airbnb",
        is_active=True
    )
    await db_session.commit()

    mock_price_result = PriceResult(
        provider="apify_airbnb",
        origin="PAR",
        destination=subscription.destination,
        travel_type=TravelType.HOTEL,
        price=Decimal("200.00"),
        currency=CurrencyEnum.USD,  # EUR vs USD
        departure_date=None,
        return_date=None,
        deep_link="http://airbnb/123",
        image_url="http://img/1"
    )

    mock_adapter = AsyncMock()
    mock_adapter.fetch_dataset.return_value = [mock_price_result]

    with patch("src.domains.subscriptions.tasks.get_adapter", return_value=mock_adapter):
        await evaluate_apify_results_task.original_func(
            subscription_id=subscription.id,
            dataset_id="ds-123",
            db=db_session
        )

    # Verify no alert created in DB
    stmt = select(Alert).where(Alert.subscription_id == subscription.id)
    res = await db_session.execute(stmt)
    alerts = res.scalars().all()
    assert len(alerts) == 0


@pytest.mark.asyncio
async def test_evaluate_task_recent_alert_suppressed(db_session: AsyncSession):
    """
    Test that when an alert was created for the same subscription in the last 24h,
    the new alert is suppressed (duplicate suppression).
    """
    user = await UserFactory.acreate(db_session)
    subscription = await SubscriptionFactory.acreate(
        db_session,
        user_id=user.id,
        max_price=Decimal("250.00"),
        currency=CurrencyEnum.EUR,
        provider="apify_airbnb",
        is_active=True
    )

    # Pre-create alert within the last 24 hours
    alert = Alert(
        subscription_id=subscription.id,
        price_found=Decimal("180.00"),
        created_at=datetime.now(timezone.utc) - timedelta(hours=2)
    )
    db_session.add(alert)
    await db_session.commit()

    mock_price_result = PriceResult(
        provider="apify_airbnb",
        origin="PAR",
        destination=subscription.destination,
        travel_type=TravelType.HOTEL,
        price=Decimal("200.00"),
        currency=CurrencyEnum.EUR,
        departure_date=None,
        return_date=None,
        deep_link="http://airbnb/123",
        image_url="http://img/1"
    )

    mock_adapter = AsyncMock()
    mock_adapter.fetch_dataset.return_value = [mock_price_result]

    with patch("src.domains.subscriptions.tasks.get_adapter", return_value=mock_adapter):
        await evaluate_apify_results_task.original_func(
            subscription_id=subscription.id,
            dataset_id="ds-123",
            db=db_session
        )

    # Verify only the pre-existing alert exists
    stmt = select(Alert).where(Alert.subscription_id == subscription.id)
    res = await db_session.execute(stmt)
    alerts = res.scalars().all()
    assert len(alerts) == 1
    assert alerts[0].price_found == Decimal("180.00")


@pytest.mark.asyncio
async def test_evaluate_task_inactive_subscription_skipped(db_session: AsyncSession):
    """
    Test that when the subscription is inactive, no alert is created and a warning is logged.
    """
    user = await UserFactory.acreate(db_session)
    subscription = await SubscriptionFactory.acreate(
        db_session,
        user_id=user.id,
        max_price=Decimal("250.00"),
        currency=CurrencyEnum.EUR,
        provider="apify_airbnb",
        is_active=False  # Inactive
    )
    await db_session.commit()

    mock_price_result = PriceResult(
        provider="apify_airbnb",
        origin="PAR",
        destination=subscription.destination,
        travel_type=TravelType.HOTEL,
        price=Decimal("200.00"),
        currency=CurrencyEnum.EUR,
        departure_date=None,
        return_date=None,
        deep_link="http://airbnb/123",
        image_url="http://img/1"
    )

    mock_adapter = AsyncMock()
    mock_adapter.fetch_dataset.return_value = [mock_price_result]

    with patch("src.domains.subscriptions.tasks.get_adapter", return_value=mock_adapter), \
         patch("src.domains.subscriptions.tasks.logger.warning") as mock_warn:
        await evaluate_apify_results_task.original_func(
            subscription_id=subscription.id,
            dataset_id="ds-123",
            db=db_session
        )

    # Verify no alert created in DB
    stmt = select(Alert).where(Alert.subscription_id == subscription.id)
    res = await db_session.execute(stmt)
    alerts = res.scalars().all()
    assert len(alerts) == 0
    mock_warn.assert_any_call(f"Subscription {subscription.id} is inactive. Skipping evaluation.")
