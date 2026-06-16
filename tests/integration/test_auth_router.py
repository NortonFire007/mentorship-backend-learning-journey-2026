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


@pytest.mark.asyncio
async def test_refresh_router_success(client: AsyncClient):
    from unittest.mock import AsyncMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis
    import re

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    app.dependency_overrides[get_redis] = lambda: mock_redis

    email = "refresh.router.success@example.com"
    password = "StrongPassword123!"

    # Register
    await client.post("/api/v1/auth/register", json={
        "name": "Refresh",
        "surname": "Router",
        "email": email,
        "password": password
    })

    # Login
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    cookie_header = login_res.headers.get("set-cookie", "")
    match = re.search(r"refresh_token=([^;]+)", cookie_header)
    refresh_token = match.group(1)

    # Refresh
    response = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify new cookie is set
    new_cookie_header = response.headers.get("set-cookie", "")
    assert "refresh_token" in new_cookie_header
    assert "HttpOnly" in new_cookie_header
    assert "Secure" in new_cookie_header
    assert "SameSite=strict" in new_cookie_header
    assert "Path=/api/v1/auth" in new_cookie_header

    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_refresh_router_missing_cookie(client: AsyncClient):
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert "Refresh token is missing" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_router_spa_race_condition(client: AsyncClient):
    from unittest.mock import AsyncMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis
    import re

    # In a real race, the second concurrent request fails to get lock
    # and reads the cached value from pending.
    mock_redis = AsyncMock()
    # Mock lock acquisition failed
    mock_redis.set.return_value = None
    mock_redis.get.return_value = '{"access_token": "cached_access", "refresh_token": "cached_refresh"}'
    app.dependency_overrides[get_redis] = lambda: mock_redis

    email = "race.router@example.com"
    password = "StrongPassword123!"

    # Register
    await client.post("/api/v1/auth/register", json={
        "name": "Race",
        "surname": "Router",
        "email": email,
        "password": password
    })

    # Login
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    cookie_header = login_res.headers.get("set-cookie", "")
    match = re.search(r"refresh_token=([^;]+)", cookie_header)
    refresh_token = match.group(1)

    # Refresh request (hitting simulated concurrent lock)
    response = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "cached_access"

    cookie_header = response.headers.get("set-cookie", "")
    assert "refresh_token=cached_refresh" in cookie_header

    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_refresh_router_grace_period_boundary(client: AsyncClient, db_session: AsyncSession):
    from unittest.mock import AsyncMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis
    from src.domains.auth.repository import RefreshTokenRepository
    from src.core.security.jwt import decode_token
    from datetime import datetime, timezone, timedelta
    import uuid
    import re

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    app.dependency_overrides[get_redis] = lambda: mock_redis

    email = "grace.boundary@example.com"
    password = "StrongPassword123!"

    # Register
    await client.post("/api/v1/auth/register", json={
        "name": "Grace",
        "surname": "Boundary",
        "email": email,
        "password": password
    })

    # Login
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    cookie_header = login_res.headers.get("set-cookie", "")
    match = re.search(r"refresh_token=([^;]+)", cookie_header)
    refresh_token = match.group(1)

    # First Refresh (marks token as used, issues Child Token)
    refresh_res1 = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh_token})
    assert refresh_res1.status_code == 200
    cookie_header1 = refresh_res1.headers.get("set-cookie", "")
    match1 = re.search(r"refresh_token=([^;]+)", cookie_header1)
    child_token = match1.group(1)

    # Second Refresh with SAME original token (within grace period) -> should return Child Token
    refresh_res2 = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh_token})
    assert refresh_res2.status_code == 200
    cookie_header2 = refresh_res2.headers.get("set-cookie", "")
    match2 = re.search(r"refresh_token=([^;]+)", cookie_header2)
    assert match2.group(1) == child_token

    # Now backdate the original token's rotated_at past 30 seconds
    payload = decode_token(refresh_token)
    jti = uuid.UUID(payload["jti"])
    repo = RefreshTokenRepository(db_session)
    db_token = await repo.get_by_jti(jti)
    db_token.rotated_at = datetime.now(timezone.utc) - timedelta(seconds=35)
    await db_session.commit()

    # Third Refresh with SAME original token (past grace period) -> should trigger 401 reuse attack revoke
    refresh_res3 = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh_token})
    assert refresh_res3.status_code == 401
    assert "session compromised" in refresh_res3.json()["detail"]

    # Verify family is revoked
    db_token = await repo.get_by_jti(jti)
    assert db_token.revoked_at is not None

    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_logout_router_success(client: AsyncClient):
    from unittest.mock import AsyncMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis
    import re

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    app.dependency_overrides[get_redis] = lambda: mock_redis

    email = "logout.router@example.com"
    password = "StrongPassword123!"

    # Register
    await client.post("/api/v1/auth/register", json={
        "name": "Logout",
        "surname": "Router",
        "email": email,
        "password": password
    })

    # Login
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    data = login_res.json()
    access_token = data["access_token"]
    cookie_header = login_res.headers.get("set-cookie", "")
    match = re.search(r"refresh_token=([^;]+)", cookie_header)
    refresh_token = match.group(1)

    # Call /logout
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.post(
        "/api/v1/auth/logout",
        headers=headers,
        cookies={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    assert response.json()["detail"] == "Successfully logged out"

    new_cookie_header = response.headers.get("set-cookie", "")
    assert "refresh_token=" in new_cookie_header

    mock_redis.set.assert_called()

    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_logout_all_router_success(client: AsyncClient):
    from unittest.mock import AsyncMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    app.dependency_overrides[get_redis] = lambda: mock_redis

    email = "logoutall.router@example.com"
    password = "StrongPassword123!"

    # Register
    await client.post("/api/v1/auth/register", json={
        "name": "LogoutAll",
        "surname": "Router",
        "email": email,
        "password": password
    })

    # Login
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    data = login_res.json()
    access_token = data["access_token"]

    # Call /logout-all
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.post("/api/v1/auth/logout-all", headers=headers)

    assert response.status_code == 200
    assert response.json()["detail"] == "Successfully logged out from all devices"

    new_cookie_header = response.headers.get("set-cookie", "")
    assert "refresh_token=" in new_cookie_header

    mock_redis.set.assert_called()

    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient):
    from unittest.mock import AsyncMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    app.dependency_overrides[get_redis] = lambda: mock_redis

    email = "me.router@example.com"
    password = "StrongPassword123!"

    # Register
    await client.post("/api/v1/auth/register", json={
        "name": "Me",
        "surname": "Router",
        "email": email,
        "password": password
    })

    # Login
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    data = login_res.json()
    access_token = data["access_token"]

    # Get Profile
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 200
    profile = response.json()
    assert profile["email"] == email
    assert profile["name"] == "Me"

    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    from unittest.mock import AsyncMock
    from src.main import app
    from src.domains.auth.dependencies import get_redis

    # Missing token
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401

    # Invalid token
    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401

    # Blacklisted token
    mock_redis = AsyncMock()
    mock_redis.get.return_value = b"1"
    app.dependency_overrides[get_redis] = lambda: mock_redis

    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer some_token"})
    assert response.status_code == 401

    app.dependency_overrides.pop(get_redis, None)

