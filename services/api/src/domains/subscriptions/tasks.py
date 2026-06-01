import asyncio
import logging
from decimal import Decimal
from taskiq import TaskiqDepends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.taskiq import broker
from src.core.taskiq import rabbitmq_broker
from src.core.events.idempotency import idempotent_event
from src.core.enums import TravelType, CurrencyEnum
from src.db.database import get_db
from src.domains.users.models import User
from src.domains.subscriptions.models import Subscription

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

