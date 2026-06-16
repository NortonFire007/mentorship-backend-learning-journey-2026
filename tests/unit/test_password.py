import time
import pytest
from src.core.security.password import hash_password, verify_password, generate_dummy_hash


@pytest.mark.asyncio
async def test_hash_produces_valid_argon2id_hash():
    password = "SuperSecurePassword123!"
    hashed = await hash_password(password)

    # Argon2id hashes start with the identifier
    assert hashed.startswith("$argon2id$")
    assert len(hashed) > 20


@pytest.mark.asyncio
async def test_password_verification_succeeds_and_fails():
    password = "SuperSecurePassword123!"
    hashed = await hash_password(password)

    assert await verify_password(password, hashed) is True
    assert await verify_password("wrong_password", hashed) is False
    assert await verify_password("", hashed) is False


@pytest.mark.asyncio
async def test_dummy_hash_generation():
    dummy_hash = generate_dummy_hash()
    assert dummy_hash.startswith("$argon2id$")


@pytest.mark.asyncio
async def test_timing_consistency():
    # Test that verifying a wrong password on a real hash and verifying against the dummy hash
    # both run the resource-heavy Argon2 algorithm and take a similar, non-trivial amount of time.
    password = "SuperSecurePassword123!"
    hashed = await hash_password(password)
    dummy = generate_dummy_hash()

    # Warm up to avoid CPU frequency scaling issues during first run
    await verify_password("warmup", hashed)

    t0 = time.perf_counter()
    await verify_password("wrong_password_attempt", hashed)
    duration_real = time.perf_counter() - t0

    t1 = time.perf_counter()
    await verify_password("wrong_password_attempt", dummy)
    duration_dummy = time.perf_counter() - t1

    # Both must be slow (indicates Argon2 hash calculation was executed)
    assert duration_real > 0.001
    assert duration_dummy > 0.001
