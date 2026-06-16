from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.domains.auth.service import AuthService


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency factory for obtaining an AuthService instance."""
    return AuthService(db)
