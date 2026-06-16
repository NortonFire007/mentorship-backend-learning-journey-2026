from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.users.repository import UserRepository
from src.domains.users.models import User
from src.domains.users.schemas import UserCreate
from src.domains.auth.schemas import RegisterRequest


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repository = UserRepository(session)

    async def register(self, data: RegisterRequest) -> User:
        """
        Register a new user with email and password.
        Uses UserRepository to create the user, which hashes the password.
        """
        existing_user = await self.user_repository.get_by_email(data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered"
            )

        user_create = UserCreate(
            name=data.name,
            surname=data.surname,
            email=data.email,
            password=data.password
        )

        user = await self.user_repository.create(user_create)
        
        # Set auth_provider explicitly to local
        user.auth_provider = "local"
        
        await self.session.commit()
        await self.session.refresh(user)
        return user
