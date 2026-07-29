import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace

from taskiq import TaskiqDepends
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.taskiq import broker, rabbitmq_broker
from src.core.config import settings
from src.core.events.idempotency import idempotent_event
from src.core.enums import TravelType, CurrencyEnum, SearchRunStatus
from src.db.database import get_db
from src.domains.users.models import User
from src.domains.subscriptions.models import Subscription
from src.domains.alerts.models import Alert
from src.domains.alerts.repository import AlertRepository
from src.domains.alerts.service import AlertService
from src.domains.alerts.schemas import AlertCreate
from src.domains.search_runs.repository import SearchRunRepository
from src.adapters.registry import get_adapter

logger = logging.getLogger(__name__)


@broker.task(
    task_name="import_external_subscriptions",
    retry_on_error=True,
    max_retries=3,
)
async def import_external_subscriptions_task(
    source_name: str,
    db: AsyncSession = TaskiqDepends(get_db)
):
    """
    Simulates importing subscription deals from an external source.
    Ensures idempotency by checking duplicate records before inserting.
    Simulates transient errors for 'flaky_api' to test the Taskiq retry mechanism.
    """
    logger.info(f"Starting to import data from source: '{source_name}'...")

    # 1. Simulate network / API request latency
    await asyncio.sleep(2)

    if source_name == "flaky_api":
        logger.warning("Simulating temporary API connection failure for 'flaky_api'...")
        raise RuntimeError("Simulated network timeout connecting to flaky_api!")

    system_email = "system.importer@example.com"
    stmt = select(User).where(User.email == system_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.info("System importer user not found. Creating default importer profile...")
        user = User(
            name="System",
            surname="Importer",
            email=system_email,
            preferred_currency=CurrencyEnum.USD,
            is_active=True
        )
        db.add(user)
        await db.flush()
        logger.info(f"Created System importer user with ID: {user.id}")

    mock_deals = [
        {
            "origin": "NYC",
            "destination": "PAR",
            "travel_type": TravelType.FLIGHT,
            "max_price": Decimal("550.00"),
            "currency": CurrencyEnum.USD,
            "duration_days": 7
        },
        {
            "origin": "LON",
            "destination": "TYO",
            "travel_type": TravelType.FLIGHT,
            "max_price": Decimal("850.00"),
            "currency": CurrencyEnum.USD,
            "duration_days": 10
        },
        {
            "origin": "MOW",
            "destination": "DXB",
            "travel_type": TravelType.FLIGHT,
            "max_price": Decimal("399.99"),
            "currency": CurrencyEnum.USD,
            "duration_days": 5
        }
    ]

    # 1. Fetch all active subscriptions of the user in a single query to avoid N+1 queries
    exist_stmt = select(Subscription.origin, Subscription.destination, Subscription.travel_type).where(
        Subscription.user_id == user.id,
        Subscription.is_active == True
    )
    exist_result = await db.execute(exist_stmt)
    
    # 2. Store existing subscriptions in a set for O(1) lookup
    existing_deals = {
        (row.origin, row.destination, row.travel_type) 
        for row in exist_result.all()
    }

    imported_count = 0
    skipped_count = 0

    for deal in mock_deals:
        deal_key = (deal["origin"], deal["destination"], deal["travel_type"])
        
        if deal_key in existing_deals:
            logger.info(
                f"Skipping duplicate subscription: {deal['origin']} -> {deal['destination']} "
                f"({deal['travel_type'].value}) for user {user.id} to ensure idempotency."
            )
            skipped_count += 1
            continue

        new_sub = Subscription(
            user_id=user.id,
            origin=deal["origin"],
            destination=deal["destination"],
            travel_type=deal["travel_type"],
            max_price=deal["max_price"],
            currency=deal["currency"],
            duration_days=deal["duration_days"],
            is_active=True
        )
        db.add(new_sub)
        imported_count += 1
        logger.info(
            f"Successfully imported new subscription: {deal['origin']} -> {deal['destination']} "
            f"for user {user.id}"
        )

    logger.info(
        f"Completed import from '{source_name}'. Imported: {imported_count}, Skipped: {skipped_count}."
    )

    return {
        "status": "success",
        "source": source_name,
        "imported": imported_count,
        "skipped": skipped_count
    }


@rabbitmq_broker.task(
    task_name="subscriptions.subscription.created",
    retry_on_error=True,
    max_retries=3,
)
@idempotent_event
async def process_subscription_created_event(event_dict: dict) -> None:
    """
    Consumer task for processing SubscriptionCreatedEvent.
    Deduplicated using Redis via the idempotent_event decorator.
    """
    logger.info(f"Successfully processed subscription created event: {event_dict}")


@broker.task(
    task_name="evaluate_apify_results",
    retry_on_error=True,
    max_retries=3,
)
async def evaluate_apify_results_task(
    subscription_id: uuid.UUID,
    dataset_id: str,
    db: AsyncSession = TaskiqDepends(get_db)
):
    """
    Retrieves results from the Apify dataset, evaluates prices against subscription
    criteria, and creates an Alert (with domain event dispatch) on the first match.
    """
    logger.info(f"Starting price evaluation for subscription {subscription_id} and dataset {dataset_id}")

    # 0. Guard: dataset_id must be a non-empty string
    if not dataset_id or not dataset_id.strip():
        logger.error(
            f"evaluate_apify_results_task called with empty dataset_id for subscription {subscription_id}. "
            "This means Apify did not produce a dataset. Aborting without retry."
        )
        return

    # 1. Load subscription
    stmt = select(Subscription).where(Subscription.id == subscription_id)
    res = await db.execute(stmt)
    subscription = res.scalar_one_or_none()

    if not subscription:
        logger.warning(f"Subscription {subscription_id} not found. Skipping evaluation.")
        return

    # 2. Check if active
    if not subscription.is_active:
        logger.warning(f"Subscription {subscription_id} is inactive. Skipping evaluation.")
        return

    # 3. Get adapter and fetch dataset
    if not subscription.provider:
        logger.warning(f"Subscription {subscription_id} has no provider configured. Skipping evaluation.")
        return

    try:
        adapter = get_adapter(subscription.provider)
    except ValueError as e:
        logger.error(f"Failed to get adapter for provider '{subscription.provider}': {e}")
        return

    # Fetch results from Apify dataset
    price_results = await adapter.fetch_dataset(dataset_id)
    if not price_results:
        logger.info(f"No price results fetched from dataset {dataset_id} for subscription {subscription_id}.")
        return

    # 4. Filter PriceResult list by price <= max_price AND currency match
    matching_result = None
    for result in price_results:
        # Check currency match
        if result.currency != subscription.currency:
            continue
        # Check price match
        if result.price <= subscription.max_price:
            matching_result = result
            break

    if not matching_result:
        logger.info(f"No pricing match found for subscription {subscription_id} (max_price={subscription.max_price} {subscription.currency}).")
        return

    # 5. Check 24h duplicate suppression
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
    alert_exists_stmt = select(Alert).where(
        Alert.subscription_id == subscription_id,
        Alert.created_at >= time_threshold
    )
    alert_exists_res = await db.execute(alert_exists_stmt)
    if alert_exists_res.scalars().first():
        logger.info(f"Alert already created for subscription {subscription_id} in the last 24 hours. Suppressing duplicate alert.")
        return

    # 6. Call AlertService.create_alert() (passing image_url and deep_link)
    alert_repo = AlertRepository(db)
    alert_service = AlertService(alert_repo, db)

    alert_create = AlertCreate(
        subscription_id=subscription.id,
        price_found=matching_result.price,
        image_url=matching_result.image_url,
        deep_link=matching_result.deep_link
    )
    
    created_alert = await alert_service.create_alert(alert_create)
    logger.info(f"Alert {created_alert.id} successfully created for subscription {subscription_id} with price {matching_result.price}")


def get_cron_expression(minutes: int) -> str:
    """
    Generate a valid crontab pattern from a minutes interval.
    If minutes is a multiple of 60, uses hourly cron to be standard-compliant.
    """
    if minutes >= 60 and minutes % 60 == 0:
        return f"0 */{minutes // 60} * * *"
    return f"*/{minutes} * * * *"




@broker.task(
    task_name="poll_all_active_subscriptions",
    schedule=[
        {
            "cron": get_cron_expression(settings.APIFY_POLL_INTERVAL_MINUTES)
        }
    ]
)
async def poll_all_active_subscriptions_task(
    db: AsyncSession = TaskiqDepends(get_db)
) -> None:
    """
    Scheduler task that finds active subscriptions eligible for checking,
    bulk updates their timestamps to prevent double-scheduling,
    and dispatches them to their respective adapters.
    """
    logger.info("Starting scheduler check for active subscriptions...")

    # Calculate cutoff time for checking
    recheck_threshold = datetime.now(timezone.utc) - timedelta(hours=settings.APIFY_SUBSCRIPTION_RECHECK_HOURS)

    # 1. Fetch eligible active subscriptions up to the batch limit
    stmt = (
        select(Subscription)
        .where(
            Subscription.is_active == True,
            Subscription.provider.is_not(None),
            or_(
                Subscription.last_checked_at.is_(None),
                Subscription.last_checked_at <= recheck_threshold
            )
        )
        .order_by(Subscription.last_checked_at.asc().nullsfirst())
        .limit(settings.APIFY_POLL_BATCH_SIZE)
    )
    res = await db.execute(stmt)
    subscriptions = res.scalars().all()

    if not subscriptions:
        logger.info("No active subscriptions eligible for price check found.")
        return

    logger.info(f"Found {len(subscriptions)} subscription(s) eligible for checking.")

    # 2. Extract needed attributes to prevent lazy-loading issues after transaction commit
    sub_copies = []
    for sub in subscriptions:
        sub_copies.append(SimpleNamespace(
            id=sub.id,
            provider=sub.provider,
            destination=sub.destination,
            start_date=sub.start_date,
            end_date=sub.end_date,
            adults=sub.adults,
            children=sub.children,
            min_bedrooms=sub.min_bedrooms,
            min_beds=sub.min_beds,
            flexible_days=sub.flexible_days,
            max_stops=sub.max_stops
        ))

    # 3. Bulk update last_checked_at first to serve as a distributed mutex
    sub_ids = [sub.id for sub in sub_copies]
    update_stmt = (
        update(Subscription)
        .where(Subscription.id.in_(sub_ids))
        .values(last_checked_at=datetime.now(timezone.utc))
    )
    await db.execute(update_stmt)
    await db.commit()

    # 4. Loop through subscriptions, get their adapter, and dispatch price checking jobs
    search_run_repo = SearchRunRepository(db)
    for sub in sub_copies:
        try:
            adapter = get_adapter(sub.provider)
            
            if adapter.execution_mode == "async_webhook":
                logger.info(f"Dispatching async webhook job for subscription {sub.id} (provider: {sub.provider})...")
                run_id = await adapter.dispatch(sub)
                
                # Create SearchRun in PENDING status
                await search_run_repo.create(
                    subscription_id=sub.id,
                    provider=sub.provider,
                    external_run_id=run_id
                )
                await db.commit()
                logger.info(f"Dispatched subscription {sub.id} successfully. SearchRun external ID: {run_id}")
            else:
                logger.warning(
                    f"Unsupported execution mode '{adapter.execution_mode}' for provider '{sub.provider}' on subscription {sub.id}."
                )
        except Exception as e:
            logger.error(
                f"Error dispatching price check for subscription {sub.id} (provider: {sub.provider}): {str(e)}",
                exc_info=True
            )



