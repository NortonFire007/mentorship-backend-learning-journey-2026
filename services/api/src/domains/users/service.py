import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.users.repository import UserRepository
from src.domains.users.schemas import UserCreate, UserUpdate
from src.domains.users.models import User

class UserService:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user. Throws exception if email is already registered.
        """
        existing_user = await self.repository.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {user_data.email} already exists"
            )
        
        user = await self.repository.create(user_data)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """
        Retrieve a user profile. Throws 404 if user doesn't exist.
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        return user

    async def update_user(self, user_id: uuid.UUID, user_data: UserUpdate) -> User:
        """
        Partially update user profile. 
        Handles optional email change with uniqueness check.
        """
        user = await self.get_user_by_id(user_id)
        
        if user_data.email and user_data.email != user.email:
             duplicate = await self.repository.get_by_email(user_data.email)
             if duplicate:
                 raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email {user_data.email} is already registered by another user"
                )

        updated_user = await self.repository.update(user, user_data)
        await self.session.commit()
        await self.session.refresh(updated_user)
        return updated_user

    async def get_user_by_id_with_subscriptions(self, user_id: uuid.UUID) -> User:
        """
        Retrieve a user profile with eagerly loaded subscriptions.
        """
        user = await self.repository.get_by_id_with_subscriptions(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        return user

    async def get_all_users_with_subscriptions(self) -> list[User]:
        """
        Retrieve all users with eagerly loaded subscriptions.
        """
        return await self.repository.get_all_with_subscriptions()

    async def get_active_subscription_counts(self) -> list[dict]:
        """
        Retrieve active subscription counts for all users.
        """
        results = await self.repository.get_active_subscription_counts()
        return [
            {
                "id": user.id, 
                "name": user.name, 
                "surname": user.surname, 
                "email": user.email, 
                "active_subscriptions_count": count
            } 
            for user, count in results
        ]

