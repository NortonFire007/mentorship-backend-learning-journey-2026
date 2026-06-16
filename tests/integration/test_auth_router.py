import pytest
from httpx import AsyncClient


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
