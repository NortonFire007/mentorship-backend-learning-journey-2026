from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.domains.alerts.service import AlertService
from src.domains.alerts.schemas import AlertCreate, AlertRead

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.post("/", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new alert (Manual seeding for Sprint 2).
    """
    service = AlertService(db)
    alert = await service.create_alert(alert_data)
    await db.commit()
    return alert

@router.get("/subscription/{subscription_id}", response_model=List[AlertRead])
async def get_subscription_alerts(
    subscription_id: UUID,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get alert history for a specific subscription.
    """
    service = AlertService(db)
    return await service.get_subscription_alerts(subscription_id, limit)

@router.post("/latest", response_model=List[AlertRead])
async def get_latest_alerts(
    subscription_ids: List[UUID],
    db: AsyncSession = Depends(get_db)
):
    """
    Get latest alert for multiple subscriptions.
    """
    service = AlertService(db)
    return await service.get_latest_alerts(subscription_ids)
