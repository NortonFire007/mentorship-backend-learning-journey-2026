from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.domains.users.repository import UserRepository
from src.domains.users.service import UserService

def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)

def get_user_service(
    repository: UserRepository = Depends(get_user_repository),
    session: AsyncSession = Depends(get_db),
) -> UserService:
    return UserService(repository=repository, session=session)
