from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.core.security.redis_auth import get_redis
from src.domains.auth.service import AuthService


def get_auth_service(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> AuthService:
    """Dependency factory for obtaining an AuthService instance."""
    dummy_hash = getattr(request.app.state, "dummy_hash", None)
    return AuthService(db, dummy_hash=dummy_hash)
