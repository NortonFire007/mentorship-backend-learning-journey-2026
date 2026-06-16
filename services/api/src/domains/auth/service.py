import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from src.core.config import settings
from src.core.security.jwt import generate_jti, encode_access_token, encode_refresh_token
from src.core.security.password import verify_password, generate_dummy_hash
from src.core.security.redis_auth import (
    get_login_attempts,
    increment_login_attempts,
    clear_login_attempts,
)
from src.domains.users.repository import UserRepository
from src.domains.users.models import User
from src.domains.users.schemas import UserCreate
from src.domains.auth.schemas import RegisterRequest, TokenPair
from src.domains.auth.repository import RefreshTokenRepository


class AuthService:
    def __init__(self, session: AsyncSession, dummy_hash: str | None = None):
        self.session = session
        self.user_repository = UserRepository(session)
        self.dummy_hash = dummy_hash

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

    async def issue_token_pair(
        self,
        user_id: uuid.UUID,
        jti_r: uuid.UUID,
        family_id: uuid.UUID,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        """
        Generate access and refresh tokens, persist the refresh token in the database.
        """
        jti_a = generate_jti()
        access_token = encode_access_token(user_id, jti_a)
        refresh_token = encode_refresh_token(user_id, jti_r, family_id)

        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        refresh_token_repo = RefreshTokenRepository(self.session)
        await refresh_token_repo.create(
            jti=jti_r,
            family_id=family_id,
            user_id=user_id,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.session.flush()

        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def login(
        self,
        email: str,
        password: str,
        redis_client: Redis,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        """
        Authenticate a user by email and password.
        Validates credentials, checks lockout, and issues access/refresh tokens.
        """
        attempts = await get_login_attempts(redis_client, email)
        if attempts >= settings.MAX_LOGIN_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        user = await self.user_repository.get_by_email(email)
        if not user:
            # Timing attack defense
            dummy = self.dummy_hash or generate_dummy_hash()
            await verify_password(password, dummy)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        if user.auth_provider != "local":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="This account uses social login"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )

        is_valid = await verify_password(password, user.password_hash or "")
        if not is_valid:
            await increment_login_attempts(redis_client, email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Successful login, reset attempts counter
        await clear_login_attempts(redis_client, email)

        jti_r = generate_jti()
        family_id = generate_jti()

        token_pair = await self.issue_token_pair(
            user_id=user.id,
            jti_r=jti_r,
            family_id=family_id,
            user_agent=user_agent,
            ip_address=ip_address
        )

        await self.session.commit()
        return token_pair
