import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import UserFactory, SubscriptionFactory

@pytest.mark.asyncio
async def test_delete_subscription_success(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test hard deletion of own subscription.
    """
    user = verified_user_client.user
    sub = await SubscriptionFactory.acreate(db_session, user=user)

    # 1. Delete it
    response = await verified_user_client.delete(f"/api/v1/subscriptions/{sub.id}")
    assert response.status_code == 204

    # 2. Verify it's gone
    response = await verified_user_client.get(f"/api/v1/subscriptions/{sub.id}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_subscription_unauthenticated(client: AsyncClient, db_session: AsyncSession):
    """
    Test deleting subscription without authentication.
    """
    user = await UserFactory.acreate(db_session)
    sub = await SubscriptionFactory.acreate(db_session, user=user)
    response = await client.delete(f"/api/v1/subscriptions/{sub.id}")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_delete_subscription_forbidden(verified_user_client: AsyncClient, db_session: AsyncSession):
    """
    Test that deleting someone else's subscription returns 403 Forbidden.
    """
    other_user = await UserFactory.acreate(db_session)
    sub = await SubscriptionFactory.acreate(db_session, user=other_user)
    response = await verified_user_client.delete(f"/api/v1/subscriptions/{sub.id}")
    assert response.status_code == 403
    assert "do not have permission" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_delete_subscription_superuser(superuser_client: AsyncClient, db_session: AsyncSession):
    """
    Test that a superuser can delete any subscription.
    """
    other_user = await UserFactory.acreate(db_session)
    sub = await SubscriptionFactory.acreate(db_session, user=other_user)
    response = await superuser_client.delete(f"/api/v1/subscriptions/{sub.id}")
    assert response.status_code == 204
