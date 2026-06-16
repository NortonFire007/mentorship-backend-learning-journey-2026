import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_register_router_success(client: AsyncClient):
    payload = {
        "name": "Bob",
        "surname": "Doe",
        "email": "bob.doe.auth@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Bob"
    assert data["email"] == "bob.doe.auth@example.com"
    assert "id" in data
    # Password hash must not leak in the response schema
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_router_duplicate_email(client: AsyncClient):
    payload = {
        "name": "Bob",
        "surname": "Doe",
        "email": "duplicate.auth@example.com",
        "password": "StrongPassword123!"
    }

    # First request should succeed
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    # Second request with the same email should fail with 409
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "weak_password,expected_error",
    [
        ("short", "Password must be at least 8 characters long"),
        ("nouppercase123!", "Password must contain at least one uppercase letter"),
        ("NoDigits!", "Password must contain at least one digit"),
        ("NoSpecialChar123", "Password must contain at least one special character"),
    ],
)
async def test_register_router_weak_password_validation(
    client: AsyncClient, weak_password: str, expected_error: str
):
    payload = {
        "name": "Bob",
        "surname": "Doe",
        "email": "bob.doe.auth@example.com",
        "password": weak_password
    }

    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422

    # Pydantic validation error details contain custom error messages
    details = response.json()["detail"]
    assert any(expected_error in error["msg"] for error in details)


@pytest.mark.asyncio
async def test_login_router_success(client: AsyncClient):
    from unittest.mock import AsyncMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    app.dependency_overrides[get_redis] = lambda: mock_redis

    email = "login.success.router@example.com"
    password = "StrongPassword123!"

    # Register
    await client.post("/api/v1/auth/register", json={
        "name": "Login",
        "surname": "Success",
        "email": email,
        "password": password
    })

    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900

    # Verify HttpOnly cookie is set
    cookie_header = response.headers.get("set-cookie", "")
    assert "refresh_token" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Secure" in cookie_header
    assert "SameSite=strict" in cookie_header
    assert "Path=/api/v1/auth" in cookie_header

    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_login_router_wrong_password(client: AsyncClient):
    from unittest.mock import AsyncMock, MagicMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_pipeline = MagicMock()
    mock_pipeline.incr.return_value = mock_pipeline
    mock_pipeline.expire.return_value = mock_pipeline
    mock_pipeline.execute = AsyncMock(return_value=[1])
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
    app.dependency_overrides[get_redis] = lambda: mock_redis

    email = "wrong.pass.router@example.com"
    password = "StrongPassword123!"

    # Register
    await client.post("/api/v1/auth/register", json={
        "name": "Wrong",
        "surname": "Pass",
        "email": email,
        "password": password
    })

    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "WrongPassword123!"
    })

    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]
    mock_pipeline.incr.assert_called_once()
    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_login_router_non_existent_email(client: AsyncClient):
    from unittest.mock import AsyncMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    app.dependency_overrides[get_redis] = lambda: mock_redis

    response = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent.router@example.com",
        "password": "StrongPassword123!"
    })

    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]
    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_login_router_inactive_user(client: AsyncClient, db_session: AsyncSession):
    from unittest.mock import AsyncMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis
    from sqlalchemy import select
    from src.domains.users.models import User

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    app.dependency_overrides[get_redis] = lambda: mock_redis

    email = "inactive.router@example.com"
    password = "StrongPassword123!"

    # Register
    await client.post("/api/v1/auth/register", json={
        "name": "Inactive",
        "surname": "Router",
        "email": email,
        "password": password
    })

    # Mark user inactive in DB
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.is_active = False
    await db_session.commit()

    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })

    assert response.status_code == 401
    assert "Account is disabled" in response.json()["detail"]
    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_login_router_rate_limit(client: AsyncClient):
    from unittest.mock import AsyncMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis

    mock_redis = AsyncMock()
    mock_redis.get.return_value = "5"
    app.dependency_overrides[get_redis] = lambda: mock_redis

    response = await client.post("/api/v1/auth/login", json={
        "email": "ratelimit.router@example.com",
        "password": "StrongPassword123!"
    })

    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]
    app.dependency_overrides.pop(get_redis, None)
