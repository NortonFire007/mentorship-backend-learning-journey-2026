import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from src.core.config import settings

from src.domains.users.repository import UserRepository
from src.domains.users.schemas import UserCreate, UserUpdate, UserPasswordChange
from src.domains.users.models import User
from src.core.security.password import verify_password, hash_password
from src.domains.auth.repository import RefreshTokenRepository
from src.core.security.redis_auth import blacklist_token

class UserService:

    def __init__(self, repository: UserRepository, session: AsyncSession):
        self.repository = repository
        self.session = session

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

    async def change_password(
        self,
        user_id: uuid.UUID,
        password_data: UserPasswordChange,
        redis_client: Redis | None = None,
    ) -> None:
        """
        Change user password after verifying the old password.
        Revokes all active sessions (refresh tokens) for the user.
        """
        user = await self.get_user_by_id(user_id)

        if user.auth_provider != "local":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account uses social login and does not have a password"
            )

        is_valid = await verify_password(password_data.old_password, user.password_hash or "")
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect old password"
            )

        user.password_hash = await hash_password(password_data.new_password)
        
        refresh_token_repo = RefreshTokenRepository(self.session)
        active_tokens = await refresh_token_repo.get_active_by_user(user_id)
        
        if active_tokens:
            await refresh_token_repo.revoke_all_user(user_id)
            
            # If Redis is available, blacklist the JTI of all active refresh tokens
            if redis_client:
                now_ts = int(datetime.now(timezone.utc).timestamp())
                for token in active_tokens:
                    token_jti_str = str(token.jti)
                    token_exp_ts = int(token.expires_at.replace(tzinfo=timezone.utc).timestamp())
                    refresh_ttl = max(0, token_exp_ts - now_ts)
                    if refresh_ttl > 0:
                        await blacklist_token(redis_client, token_jti_str, "refresh", refresh_ttl)
                        
        await self.session.commit()

    async def generate_telegram_link(
        self,
        user_id: uuid.UUID,
        redis_client: Redis,
    ) -> str:
        """
        Generate a deep link for linking the user account to a Telegram chat.
        Stores a UUID token in Redis with a 15-minute TTL.
        """
        token = str(uuid.uuid4())
        await redis_client.set(f"tg_link:{token}", str(user_id), ex=900)
        return f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={token}"


