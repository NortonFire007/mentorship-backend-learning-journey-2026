import uuid
from datetime import date
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.domains.subscriptions.schemas import SubscriptionCreate, SubscriptionRead, SubscriptionUpdate, DestinationStatsRead
from src.domains.subscriptions.service import SubscriptionService
from decimal import Decimal
from src.core.enums import TravelType

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

@router.post("/", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_subscription_endpoint(
    sub_in: SubscriptionCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new travel deal subscription for a user.
    """
    service = SubscriptionService(db)
    return await service.create_subscription(sub_in)

@router.get("/", response_model=list[SubscriptionRead])
async def list_subscriptions_endpoint(
    user_id: uuid.UUID | None = Query(None, description="Filter results by specific user ID"),
    is_active: bool | None = Query(None, description="Filter results by subscription active status"),
    travel_type: TravelType | None = Query(None, description="Filter results by type of travel (flight, hotel, package)"),
    start_date_from: date | None = Query(None, description="Filter results by start date (from)"),
    start_date_to: date | None = Query(None, description="Filter results by start date (to)"),
    min_price: Decimal | None = Query(None, description="Filter results by minimum price"),
    max_price: Decimal | None = Query(None, description="Filter results by maximum price"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all subscriptions with optional filtering.
    Essential for the deal-finder worker to locate active alerts.
    """
    service = SubscriptionService(db)
    return await service.list_subscriptions(
        user_id, is_active, travel_type,
        start_date_from, start_date_to, min_price, max_price
    )

@router.get("/{sub_id}", response_model=SubscriptionRead)
async def get_subscription_endpoint(
    sub_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve one specific subscription details.
    """
    service = SubscriptionService(db)
    return await service.get_subscription_by_id(sub_id)

@router.patch("/{sub_id}", response_model=SubscriptionRead)
async def update_subscription_endpoint(
    sub_id: uuid.UUID,
    sub_in: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Partially update a subscription (e.g., change budget or destination).
    """
    service = SubscriptionService(db)
    return await service.update_subscription(sub_id, sub_in)

@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription_endpoint(
    sub_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently remove a subscription. Returns No Content.
    """
    service = SubscriptionService(db)
    await service.hard_delete_subscription(sub_id)

@router.get("/stats/destinations", response_model=list[DestinationStatsRead])
async def get_destination_stats_endpoint(
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve statistics on popular travel destinations based on subscriptions.
    """
    service = SubscriptionService(db)
    return await service.get_destination_stats()
