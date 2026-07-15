import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.domains.users.repository import UserRepository
from src.domains.users.service import UserService
from src.domains.users.models import User
from src.domains.auth.dependencies import get_current_user

def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)

def get_user_service(
    repository: UserRepository = Depends(get_user_repository),
    session: AsyncSession = Depends(get_db),
) -> UserService:
    return UserService(repository=repository, session=session)

async def get_user_profile_access(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> uuid.UUID:
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this user profile"
        )
    return user_id

async def get_user_profile_edit_access(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> uuid.UUID:
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this user profile"
        )
    return user_id
