import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.domains.mcp_admin.server import mcp
from src.domains.mcp_admin.tools.users import (
    get_user_by_email,
    get_user_subscriptions,
    update_subscription_status,
)
from src.domains.mcp_admin.tools.parsers import (
    get_recent_search_runs,
    get_alert_history,
    trigger_apify_sync,
)
from src.domains.search_runs.repository import SearchRunRepository
from tests.factories import UserFactory, SubscriptionFactory, AlertFactory


@pytest_asyncio.fixture(autouse=True)
def patch_mcp_db_sessions(db_session: AsyncSession):
    """
    Patch AsyncSessionLocal and db_transaction in tools modules so direct tool
    invocations during tests use the isolated test db_session.
    """
    @asynccontextmanager
    async def _mock_session_context(*args, **kwargs):
        yield db_session

    with patch("src.domains.mcp_admin.tools.users.AsyncSessionLocal", _mock_session_context), \
         patch("src.domains.mcp_admin.tools.users.db_transaction", _mock_session_context), \
         patch("src.domains.mcp_admin.tools.parsers.AsyncSessionLocal", _mock_session_context):
        yield


@pytest.mark.asyncio
async def test_mcp_auth_endpoint(client: AsyncClient):
    """
    Test bearer token authentication on /mcp sub-app.
    """
    async with mcp.session_manager.run():
        # 1. Missing Authorization header -> 401
        resp_no_auth = await client.post("/mcp/", json={})
        assert resp_no_auth.status_code == 401

        # 2. Invalid Bearer token -> 401
        resp_invalid_token = await client.post(
            "/mcp/",
            headers={"Authorization": "Bearer invalid_secret_123"},
            json={}
        )
        assert resp_invalid_token.status_code == 401

        # 3. Valid Bearer token -> non-401 (e.g. 200 or 400 bad JSONRPC body)
        resp_valid = await client.post(
            "/mcp/",
            headers={"Authorization": f"Bearer {settings.MCP_API_KEY}"},
            json={"jsonrpc": "2.0", "method": "ping", "id": 1}
        )
        assert resp_valid.status_code != 401


@pytest.mark.asyncio
async def test_get_user_by_email_tool(db_session: AsyncSession):
    """
    Test get_user_by_email MCP tool.
    """
    user = await UserFactory.acreate(db_session)

    # Success case
    profile = await get_user_by_email(user.email)
    assert isinstance(profile, dict)
    assert profile["id"] == str(user.id)
    assert profile["email"] == user.email

    # Not found case
    not_found = await get_user_by_email("nonexistent@example.com")
    assert isinstance(not_found, str)
    assert "User not found" in not_found


@pytest.mark.asyncio
async def test_get_user_subscriptions_tool(db_session: AsyncSession):
    """
    Test get_user_subscriptions MCP tool.
    """
    user = await UserFactory.acreate(db_session)
    sub1 = await SubscriptionFactory.acreate(db_session, user=user)
    sub2 = await SubscriptionFactory.acreate(db_session, user=user)

    # Success case
    subs = await get_user_subscriptions(str(user.id))
    assert isinstance(subs, list)
    assert len(subs) == 2
    sub_ids = {s["id"] for s in subs}
    assert str(sub1.id) in sub_ids
    assert str(sub2.id) in sub_ids

    # Invalid UUID case
    invalid_res = await get_user_subscriptions("not-a-uuid")
    assert isinstance(invalid_res, str)
    assert "Invalid user_id format" in invalid_res

    # Nonexistent user case
    random_uuid = str(uuid.uuid4())
    not_found_res = await get_user_subscriptions(random_uuid)
    assert isinstance(not_found_res, str)
    assert "User not found" in not_found_res


@pytest.mark.asyncio
async def test_update_subscription_status_tool(db_session: AsyncSession):
    """
    Test update_subscription_status MCP tool.
    """
    sub = await SubscriptionFactory.acreate(db_session, is_active=True)

    # Deactivate subscription
    result = await update_subscription_status(str(sub.id), False)
    assert isinstance(result, dict)
    assert result["status"] == "updated"
    assert result["is_active"] is False

    # Invalid UUID case
    invalid_res = await update_subscription_status("invalid-uuid", True)
    assert isinstance(invalid_res, str)
    assert "Invalid subscription_id format" in invalid_res

    # Nonexistent subscription case
    random_uuid = str(uuid.uuid4())
    not_found_res = await update_subscription_status(random_uuid, True)
    assert isinstance(not_found_res, str)
    assert "Subscription not found" in not_found_res


@pytest.mark.asyncio
async def test_get_recent_search_runs_tool(db_session: AsyncSession):
    """
    Test get_recent_search_runs MCP tool.
    """
    sub = await SubscriptionFactory.acreate(db_session, provider="apify_airbnb")
    search_run_repo = SearchRunRepository(db_session)
    run1 = await search_run_repo.create(sub.id, "apify_airbnb", external_run_id="run_1")

    runs = await get_recent_search_runs(str(sub.id))
    assert isinstance(runs, list)
    assert len(runs) == 1
    assert runs[0]["id"] == str(run1.id)
    assert runs[0]["external_run_id"] == "run_1"

    # Invalid UUID case
    invalid_res = await get_recent_search_runs("invalid-uuid")
    assert isinstance(invalid_res, str)
    assert "Invalid subscription_id format" in invalid_res


@pytest.mark.asyncio
async def test_get_alert_history_tool(db_session: AsyncSession):
    """
    Test get_alert_history MCP tool.
    """
    sub = await SubscriptionFactory.acreate(db_session)
    alert = await AlertFactory.acreate(db_session, subscription=sub)

    alerts = await get_alert_history(str(sub.id))
    assert isinstance(alerts, list)
    assert len(alerts) == 1
    assert alerts[0]["id"] == str(alert.id)

    # Invalid UUID case
    invalid_res = await get_alert_history("invalid-uuid")
    assert isinstance(invalid_res, str)
    assert "Invalid subscription_id format" in invalid_res


@pytest.mark.asyncio
async def test_trigger_apify_sync_tool(db_session: AsyncSession):
    """
    Test trigger_apify_sync MCP tool.
    """
    sub = await SubscriptionFactory.acreate(db_session, is_active=True, provider="apify_airbnb")

    # Success case for active subscription
    sync_res = await trigger_apify_sync(str(sub.id))
    assert isinstance(sync_res, dict)
    assert sync_res["status"] == "queued"
    assert sync_res["subscription_id"] == str(sub.id)
    assert "task_id" in sync_res

    # Inactive subscription case
    inactive_sub = await SubscriptionFactory.acreate(db_session, is_active=False)
    inactive_res = await trigger_apify_sync(str(inactive_sub.id))
    assert isinstance(inactive_res, str)
    assert "inactive" in inactive_res

    # Invalid UUID case
    invalid_res = await trigger_apify_sync("invalid-uuid")
    assert isinstance(invalid_res, str)
    assert "Invalid subscription_id format" in invalid_res


@pytest.mark.asyncio
async def test_get_mcp_token_unauthenticated(client: AsyncClient):
    """
    Test GET /api/v1/users/mcp-token without authentication.
    """
    resp = await client.get("/api/v1/users/mcp-token")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_mcp_token_regular_user_forbidden(verified_user_client: AsyncClient):
    """
    Test GET /api/v1/users/mcp-token for non-superuser returns 403.
    """
    resp = await verified_user_client.get("/api/v1/users/mcp-token")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_mcp_token_superuser_success(superuser_client: AsyncClient):
    """
    Test GET /api/v1/users/mcp-token for superuser returns 200 with mcp_token.
    """
    resp = await superuser_client.get("/api/v1/users/mcp-token")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mcp_token"] == settings.MCP_API_KEY
