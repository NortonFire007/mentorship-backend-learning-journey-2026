import asyncio
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# OWASP minimum recommendations for Argon2id:
# time_cost = 2, memory_cost = 65536 KB, parallelism = 1, hash_len = 32, salt_len = 16
ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    salt_len=16
)


def _hash_password_sync(plain: str) -> str:
    """Synchronous password hashing."""
    return ph.hash(plain)


async def hash_password(plain: str) -> str:
    """
    Asynchronously hash a password using Argon2id.
    Runs in a separate thread to prevent blocking the event loop.
    """
    return await asyncio.to_thread(_hash_password_sync, plain)


def _verify_password_sync(plain: str, hashed: str) -> bool:
    """Synchronous password verification."""
    try:
        # verify returns True or raises VerifyMismatchError
        ph.verify(hashed, plain)
        # Check if the hash is outdated (can check, but verify returns True if valid)
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        return False


async def verify_password(plain: str, hashed: str) -> bool:
    """
    Asynchronously verify a password against its hash.
    Runs in a separate thread to prevent blocking the event loop.
    """
    return await asyncio.to_thread(_verify_password_sync, plain, hashed)


def generate_dummy_hash() -> str:
    """
    Generate a dummy hash on application startup.
    Used for timing attack mitigation.
    """
    return ph.hash("dummy_password_for_timing_safety")
