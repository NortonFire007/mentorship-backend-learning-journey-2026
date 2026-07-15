import uuid
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, status, Query
from src.domains.subscriptions.schemas import SubscriptionCreate, SubscriptionRead, SubscriptionUpdate, DestinationStatsRead
from src.domains.subscriptions.service import SubscriptionService
from src.domains.subscriptions.dependencies import get_subscription_service, get_current_user_subscription
from src.domains.subscriptions.tasks import import_external_subscriptions_task
from src.domains.users.models import User
from src.domains.auth.dependencies import get_current_user, get_current_superuser
from src.core.enums import TravelType
from src.domains.subscriptions.models import Subscription

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

@router.post("/", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_subscription_endpoint(
    sub_in: SubscriptionCreate, 
    service: SubscriptionService = Depends(get_subscription_service),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new travel deal subscription for a user.
    """
    return await service.create_subscription(sub_in, current_user.id)

@router.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def trigger_import_endpoint(
    source_name: str = "booking",
    current_superuser: User = Depends(get_current_superuser),
):
    """
    Trigger a background task to import external data.
    """
    task = await import_external_subscriptions_task.kiq(source_name)
    return {"message": "Import task started", "task_id": task.task_id}

@router.get("/", response_model=list[SubscriptionRead])
async def list_subscriptions_endpoint(
    user_id: uuid.UUID | None = Query(None, description="Filter results by specific user ID"),
    is_active: bool | None = Query(None, description="Filter results by subscription active status"),
    travel_type: TravelType | None = Query(None, description="Filter results by type of travel (flight, hotel, package)"),
    start_date_from: date | None = Query(None, description="Filter results by start date (from)"),
    start_date_to: date | None = Query(None, description="Filter results by start date (to)"),
    min_price: Decimal | None = Query(None, description="Filter results by minimum price"),
    max_price: Decimal | None = Query(None, description="Filter results by maximum price"),
    service: SubscriptionService = Depends(get_subscription_service),
    current_user: User = Depends(get_current_user),
):
    """
    List all subscriptions with optional filtering.
    Essential for the deal-finder worker to locate active alerts.
    """
    return await service.list_subscriptions(
        current_user=current_user,
        user_id=user_id,
        is_active=is_active,
        travel_type=travel_type,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        min_price=min_price,
        max_price=max_price,
    )

@router.get("/{sub_id}", response_model=SubscriptionRead)
async def get_subscription_endpoint(
    subscription: Subscription = Depends(get_current_user_subscription),
):
    """
    Retrieve one specific subscription details.
    """
    return subscription

@router.patch("/{sub_id}", response_model=SubscriptionRead)
async def update_subscription_endpoint(
    sub_in: SubscriptionUpdate,
    subscription: Subscription = Depends(get_current_user_subscription),
    service: SubscriptionService = Depends(get_subscription_service),
):
    """
    Partially update a subscription (e.g., change budget or destination).
    """
    return await service.update_subscription(subscription.id, sub_in)

@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription_endpoint(
    subscription: Subscription = Depends(get_current_user_subscription),
    service: SubscriptionService = Depends(get_subscription_service),
):
    """
    Permanently remove a subscription. Returns No Content.
    """
    await service.hard_delete_subscription(subscription.id)

@router.get("/stats/destinations", response_model=list[DestinationStatsRead])
async def get_destination_stats_endpoint(
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Retrieve statistics on popular travel destinations based on subscriptions.
    """
    return await service.get_destination_stats()
