import pytest
import uuid
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.enums import AlertStatus
from tests.factories import UserFactory, SubscriptionFactory, AlertFactory

@pytest.mark.asyncio
async def test_create_alert_superuser(superuser_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a superuser can manually create a new alert.
    """
    user = await UserFactory.acreate(db_session)
    sub = await SubscriptionFactory.acreate(db_session, user=user)

    payload = {
        "subscription_id": str(sub.id),
        "price_found": "350.00",
        "status": AlertStatus.PENDING.value
    }
    
    response = await superuser_client.post("/api/v1/alerts/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["subscription_id"] == str(sub.id)
    assert data["price_found"] == "350.00"

@pytest.mark.asyncio
async def test_create_alert_regular_user_forbidden(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a regular user cannot create a manual alert (returns 403).
    """
    user = verified_user_client.user
    sub = await SubscriptionFactory.acreate(db_session, user=user)

    payload = {
        "subscription_id": str(sub.id),
        "price_found": "350.00",
        "status": AlertStatus.PENDING.value
    }

    response = await verified_user_client.post("/api/v1/alerts/", json=payload)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_get_subscription_alerts_owner(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a user can retrieve alerts for their own subscription.
    """
    user = verified_user_client.user
    sub = await SubscriptionFactory.acreate(db_session, user=user)
    await AlertFactory.acreate(db_session, subscription=sub, price_found=Decimal("300.00"))

    response = await verified_user_client.get(f"/api/v1/alerts/subscription/{sub.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["price_found"] == "300.00"

@pytest.mark.asyncio
async def test_get_subscription_alerts_forbidden(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a regular user cannot retrieve alerts for a subscription they do not own.
    """
    other_user = await UserFactory.acreate(db_session)
    sub = await SubscriptionFactory.acreate(db_session, user=other_user)
    await AlertFactory.acreate(db_session, subscription=sub)

    response = await verified_user_client.get(f"/api/v1/alerts/subscription/{sub.id}")
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_get_subscription_alerts_superuser(superuser_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a superuser can retrieve alerts for any subscription.
    """
    other_user = await UserFactory.acreate(db_session)
    sub = await SubscriptionFactory.acreate(db_session, user=other_user)
    await AlertFactory.acreate(db_session, subscription=sub, price_found=Decimal("400.00"))

    response = await superuser_client.get(f"/api/v1/alerts/subscription/{sub.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["price_found"] == "400.00"

@pytest.mark.asyncio
async def test_get_subscription_alerts_not_found(verified_user_client: AsyncClient):
    """
    Test that fetching alerts for a non-existent subscription returns 404.
    """
    response = await verified_user_client.get(f"/api/v1/alerts/subscription/{uuid.uuid4()}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_latest_alerts_success(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a user can fetch the latest alerts for their owned subscriptions.
    """
    user = verified_user_client.user
    sub1 = await SubscriptionFactory.acreate(db_session, user=user)
    sub2 = await SubscriptionFactory.acreate(db_session, user=user)
    await AlertFactory.acreate(db_session, subscription=sub1, price_found=Decimal("200.00"))
    await AlertFactory.acreate(db_session, subscription=sub2, price_found=Decimal("250.00"))

    payload = [str(sub1.id), str(sub2.id)]
    response = await verified_user_client.post("/api/v1/alerts/latest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

@pytest.mark.asyncio
async def test_get_latest_alerts_mix_forbidden(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test that requesting latest alerts with a mix of owned and unowned subscriptions returns 403 Forbidden.
    """
    user = verified_user_client.user
    other_user = await UserFactory.acreate(db_session)
    sub_owned = await SubscriptionFactory.acreate(db_session, user=user)
    sub_other = await SubscriptionFactory.acreate(db_session, user=other_user)

    payload = [str(sub_owned.id), str(sub_other.id)]
    response = await verified_user_client.post("/api/v1/alerts/latest", json=payload)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_get_latest_alerts_superuser_mix(superuser_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a superuser can get latest alerts for a mix of subscriptions belonging to different users.
    """
    user1 = await UserFactory.acreate(db_session)
    user2 = await UserFactory.acreate(db_session)
    sub1 = await SubscriptionFactory.acreate(db_session, user=user1)
    sub2 = await SubscriptionFactory.acreate(db_session, user=user2)
    await AlertFactory.acreate(db_session, subscription=sub1, price_found=Decimal("150.00"))
    await AlertFactory.acreate(db_session, subscription=sub2, price_found=Decimal("160.00"))

    payload = [str(sub1.id), str(sub2.id)]
    response = await superuser_client.post("/api/v1/alerts/latest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
