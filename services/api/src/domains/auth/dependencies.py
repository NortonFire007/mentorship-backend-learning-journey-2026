import uuid
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from src.db.database import get_db
from src.core.security.redis_auth import get_redis, is_blacklisted
from src.core.security.jwt import decode_token
from src.domains.auth.service import AuthService
from src.domains.users.repository import UserRepository
from src.domains.users.models import User

reusable_oauth2 = HTTPBearer()


def get_auth_service(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> AuthService:
    """Dependency factory for obtaining an AuthService instance."""
    dummy_hash = getattr(request.app.state, "dummy_hash", None)
    return AuthService(db, dummy_hash=dummy_hash)


async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(reusable_oauth2),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    """
    FastAPI dependency that validates the bearer token, checks Redis blacklist,
    and returns the authenticated user database object.
    """
    payload = decode_token(token.credentials)

    # Validate token type is access
    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Check access token blacklist
    if await is_blacklisted(redis, jti, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is blacklisted",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )

    return user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency that asserts the authenticated user has verified their email address.
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User email is not verified",
        )
    return current_user
