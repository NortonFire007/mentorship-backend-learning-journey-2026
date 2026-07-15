from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.domains.alerts.service import AlertService
from src.domains.alerts.schemas import AlertCreate, AlertRead
from src.domains.alerts.dependencies import (
    get_alert_service,
    verify_subscription_ownership,
    verify_bulk_subscription_ownership,
)
from src.domains.auth.dependencies import get_current_superuser
from src.domains.users.models import User

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.post("/", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    service: AlertService = Depends(get_alert_service),
    db: AsyncSession = Depends(get_db),
    current_superuser: User = Depends(get_current_superuser),
):
    """
    Create a new alert (Manual seeding for Sprint 2).
    Restricted to superusers.
    """
    alert = await service.create_alert(alert_data)
    await db.commit()
    return alert

@router.get("/subscription/{subscription_id}", response_model=List[AlertRead])
async def get_subscription_alerts(
    subscription_id: UUID = Depends(verify_subscription_ownership),
    limit: int = 10,
    service: AlertService = Depends(get_alert_service),
):
    """
    Get alert history for a specific subscription.
    """
    return await service.get_subscription_alerts(subscription_id, limit)

@router.post("/latest", response_model=List[AlertRead])
async def get_latest_alerts(
    subscription_ids: List[UUID] = Depends(verify_bulk_subscription_ownership),
    service: AlertService = Depends(get_alert_service),
):
    """
    Get latest alert for multiple subscriptions.
    """
    return await service.get_latest_alerts(subscription_ids)
