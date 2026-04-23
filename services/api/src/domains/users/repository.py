import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.users.models import User
from src.domains.users.schemas import UserCreate, UserUpdate

class UserRepository:
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """
        Fetch a user by their unique primary key (UUID).
        """
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        Fetch a user by their unique email address.
        """
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user_data: UserCreate) -> User:
        """
        Create a new User record from validated creation schema.
        """
        user = User(**user_data.model_dump())
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user: User, user_data: UserUpdate) -> User:
        """
        Update an existing User record with partial update data (PATCH).
        """
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await self.session.flush()
        return user
