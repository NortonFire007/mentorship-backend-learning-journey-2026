import pytest
import uuid
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_task_status_unauthenticated(client: AsyncClient):
    """
    Test that retrieving task status without authentication returns 401.
    """
    response = await client.get(f"/api/v1/tasks/{uuid.uuid4()}")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_task_status_authenticated(verified_user_client: AsyncClient):
    """
    Test that retrieving task status with authentication returns 200.
    """
    task_id = str(uuid.uuid4())
    response = await verified_user_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["is_ready"] is False
