import uuid
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from src.core.config import settings
from src.core.security.jwt import generate_jti, encode_access_token, encode_refresh_token, decode_token
from src.core.security.password import verify_password, generate_dummy_hash
from src.core.security.redis_auth import (
    get_login_attempts,
    increment_login_attempts,
    clear_login_attempts,
    is_blacklisted,
    acquire_refresh_lock,
    get_pending_refresh,
    set_pending_refresh,
    blacklist_token,
)
from src.domains.users.repository import UserRepository
from src.domains.users.models import User
from src.domains.users.schemas import UserCreate
from src.domains.auth.schemas import RegisterRequest, TokenPair
from src.domains.auth.repository import RefreshTokenRepository
from src.domains.auth.models import RefreshToken


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

    async def refresh(
        self,
        refresh_token_str: str,
        redis_client: Redis,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        """
        Rotate refresh token and issue a new access token.
        Detects reuse attacks and handles concurrent race conditions.
        """
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        jti_str = payload.get("jti")
        family_id_str = payload.get("family_id")
        user_id_str = payload.get("sub")

        if not jti_str or not family_id_str or not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        jti = uuid.UUID(jti_str)
        family_id = uuid.UUID(family_id_str)
        user_id = uuid.UUID(user_id_str)

        if await is_blacklisted(redis_client, jti_str, "refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is blacklisted",
            )

        redis_ok = True
        try:
            await redis_client.ping()  # type: ignore
        except Exception:
            redis_ok = False

        if redis_ok:
            lock_acquired = await acquire_refresh_lock(redis_client, jti_str)
            if not lock_acquired:
                for _ in range(5):
                    await asyncio.sleep(0.2)
                    pending = await get_pending_refresh(redis_client, jti_str)
                    if pending:
                        return TokenPair(
                            access_token=pending["access_token"],
                            refresh_token=pending["refresh_token"]
                        )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Concurrent refresh timeout",
                )

        refresh_token_repo = RefreshTokenRepository(self.session)
        db_token = await refresh_token_repo.get_by_jti(jti)
        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        if db_token.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        if db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )

        if db_token.is_used:
            rotated_at = db_token.rotated_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            grace_period = timedelta(seconds=settings.REFRESH_GRACE_PERIOD_SECONDS)

            if now - rotated_at > grace_period:
                # Reuse attack! Invalidate family in DB
                await refresh_token_repo.revoke_family(family_id)
                await self.session.commit()

                # Blacklist all family tokens in Redis if Redis is available
                if redis_ok:
                    family_jtis = await refresh_token_repo.get_jtis_by_family(family_id)
                    for f_jti in family_jtis:
                        await blacklist_token(redis_client, str(f_jti), "refresh", 30 * 24 * 3600)

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Security alert: session compromised",
                )
            else:
                # Within grace period, return child token
                child = await refresh_token_repo.get_child_by_family(family_id)
                if not child:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token family",
                    )
                jti_a = generate_jti()
                access_token = encode_access_token(user_id, jti_a)
                refresh_token = encode_refresh_token(user_id, child.jti, family_id)
                return TokenPair(access_token=access_token, refresh_token=refresh_token)

        # Normal rotation path
        now_rotated = datetime.now(timezone.utc)
        await refresh_token_repo.mark_used(jti, now_rotated)

        # Blacklist old JTI if Redis is available
        if redis_ok:
            ttl_seconds = int((db_token.expires_at.replace(tzinfo=timezone.utc) - now_rotated).total_seconds())
            await blacklist_token(redis_client, jti_str, "refresh", ttl_seconds)

        new_jti = generate_jti()
        token_pair = await self.issue_token_pair(
            user_id=user_id,
            jti_r=new_jti,
            family_id=family_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # Cache the pending result if Redis is available
        if redis_ok:
            await set_pending_refresh(
                redis_client,
                jti_str,
                {"access_token": token_pair.access_token, "refresh_token": token_pair.refresh_token}
            )

        await self.session.commit()
        return token_pair
