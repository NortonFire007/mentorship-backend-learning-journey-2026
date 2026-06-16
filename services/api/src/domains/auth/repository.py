import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.auth.models import RefreshToken


class RefreshTokenRepository:
    """
    Repository class for managing database operations for RefreshToken models.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        jti: uuid.UUID,
        family_id: uuid.UUID,
        user_id: uuid.UUID,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshToken:
        """
        Create a new RefreshToken record.
        """
        token = RefreshToken(
            jti=jti,
            family_id=family_id,
            user_id=user_id,
            issued_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
            is_used=False,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_jti(self, jti: uuid.UUID) -> RefreshToken | None:
        """
        Retrieve a RefreshToken by its unique JTI.
        """
        stmt = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_used(self, jti: uuid.UUID, rotated_at: datetime) -> None:
        """
        Mark a token as used and set its rotation timestamp.
        """
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.jti == jti)
            .values(is_used=True, rotated_at=rotated_at)
        )
        await self.session.execute(stmt)

    async def revoke(self, jti: uuid.UUID) -> None:
        """
        Revoke a specific token by JTI.
        """
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.jti == jti)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        """
        Revoke all tokens belonging to the specified family ID.
        """
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)

    async def get_child_by_family(self, family_id: uuid.UUID) -> RefreshToken | None:
        """
        Get the newest non-used and non-revoked token in a family.
        """
        stmt = (
            select(RefreshToken)
            .where(
                (RefreshToken.family_id == family_id)
                & (RefreshToken.is_used == False)
                & (RefreshToken.revoked_at == None)
            )
            .order_by(RefreshToken.issued_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_user(self, user_id: uuid.UUID) -> list[RefreshToken]:
        """
        Retrieve all active (non-used, non-revoked, non-expired) tokens for a user.
        """
        now = datetime.now(timezone.utc)
        stmt = select(RefreshToken).where(
            (RefreshToken.user_id == user_id)
            & (RefreshToken.is_used == False)
            & (RefreshToken.revoked_at == None)
            & (RefreshToken.expires_at > now)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def revoke_all_user(self, user_id: uuid.UUID) -> None:
        """
        Revoke all refresh tokens for a user.
        """
        stmt = (
            update(RefreshToken)
            .where((RefreshToken.user_id == user_id) & (RefreshToken.revoked_at == None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
