import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import taskiq_fastapi

from src.main import app
from src.core.taskiq import broker
from src.domains.users.models import User
from src.domains.subscriptions.models import Subscription
from src.domains.subscriptions.tasks import import_external_subscriptions_task


@pytest.fixture(autouse=True)
def setup_taskiq_context():
    """
    Populate dependency context for the InMemoryBroker.
    Ensures taskiq-fastapi can resolve dependencies during test runs.
    """
    taskiq_fastapi.populate_dependency_context(broker, app)
    yield


@pytest.fixture(autouse=True)
async def cleanup_db(db_session: AsyncSession):
    """
    Ensure the database is completely clean of imported users and subscriptions before each test.
    This prevents state leakage between tests when tasks perform explicit commits.
    """
    # Delete subscriptions first due to foreign key constraints
    await db_session.execute(delete(Subscription))
    # Delete the system importer user
    await db_session.execute(delete(User).where(User.email == "system.importer@example.com"))
    await db_session.commit()
    yield


@pytest.mark.asyncio
async def test_trigger_import_endpoint(client: AsyncClient):
    """
    Test that triggering the import endpoint starts a task and returns 202 status.
    """
    response = await client.post("/api/v1/subscriptions/import?source_name=aviasales")
    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Import task started"
    assert "task_id" in data


@pytest.mark.asyncio
async def test_import_external_subscriptions_success(db_session: AsyncSession):
    """
    Test that the import task successfully creates a system user
    and inserts mock subscriptions.
    """
    # Verify no system user and subscriptions exist initially
    system_email = "system.importer@example.com"
    user_stmt = select(User).where(User.email == system_email)
    user_res = await db_session.execute(user_stmt)
    assert user_res.scalar_one_or_none() is None

    sub_stmt = select(Subscription)
    sub_res = await db_session.execute(sub_stmt)
    assert len(sub_res.scalars().all()) == 0

    # Execute task directly
    result = await import_external_subscriptions_task(source_name="booking", db=db_session)

    assert result["status"] == "success"
    assert result["imported"] == 3
    assert result["skipped"] == 0

    # Verify system user was created
    user_res = await db_session.execute(user_stmt)
    system_user = user_res.scalar_one_or_none()
    assert system_user is not None
    assert system_user.name == "System"

    # Verify subscriptions were inserted
    sub_res = await db_session.execute(select(Subscription).where(Subscription.user_id == system_user.id))
    subs = sub_res.scalars().all()
    assert len(subs) == 3
    assert any(s.origin == "NYC" and s.destination == "PAR" for s in subs)
    assert any(s.origin == "LON" and s.destination == "TYO" for s in subs)
    assert any(s.origin == "MOW" and s.destination == "DXB" for s in subs)


@pytest.mark.asyncio
async def test_import_external_subscriptions_idempotency(db_session: AsyncSession):
    """
    Test that executing the task multiple times is idempotent
    and does not result in duplicate database subscriptions.
    """
    # 1st execution: should import 3 subscriptions
    res1 = await import_external_subscriptions_task(source_name="booking", db=db_session)
    assert res1["imported"] == 3
    assert res1["skipped"] == 0

    # 2nd execution: should skip all 3 (imported = 0, skipped = 3)
    res2 = await import_external_subscriptions_task(source_name="booking", db=db_session)
    assert res2["imported"] == 0
    assert res2["skipped"] == 3

    # Verify DB has only 3 subscriptions total
    sub_res = await db_session.execute(select(Subscription))
    subs = sub_res.scalars().all()
    assert len(subs) == 3


@pytest.mark.asyncio
async def test_import_external_subscriptions_flaky_retry(db_session: AsyncSession):
    """
    Test that the task raises RuntimeError when run against flaky_api
    to trigger Taskiq's built-in retry mechanism.
    """
    with pytest.raises(RuntimeError, match="Simulated network timeout connecting to flaky_api!"):
        await import_external_subscriptions_task(source_name="flaky_api", db=db_session)
