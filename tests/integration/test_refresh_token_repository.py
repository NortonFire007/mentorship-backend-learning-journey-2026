import uuid
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.auth.repository import RefreshTokenRepository
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_refresh_token_repository_lifecycle(db_session: AsyncSession):
    repo = RefreshTokenRepository(db_session)
    user = await UserFactory.acreate(db_session)
    user_id = user.id

    jti = uuid.uuid4()
    family_id = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    # 1. Test Create
    token = await repo.create(
        jti=jti,
        family_id=family_id,
        user_id=user_id,
        expires_at=expires_at,
        user_agent="Mozilla/5.0",
        ip_address="127.0.0.1",
    )

    assert token.jti == jti
    assert token.family_id == family_id
    assert token.user_id == user_id
    assert token.user_agent == "Mozilla/5.0"
    assert token.ip_address == "127.0.0.1"
    assert token.is_used is False
    assert token.revoked_at is None

    # 2. Test get_by_jti
    fetched = await repo.get_by_jti(jti)
    assert fetched is not None
    assert fetched.id == token.id

    # 3. Test mark_used
    now = datetime.now(timezone.utc)
    await repo.mark_used(jti, now)
    await db_session.commit()

    # Expire and fetch again to load fresh state from DB
    db_session.expire_all()
    fetched = await repo.get_by_jti(jti)
    assert fetched.is_used is True
    assert fetched.rotated_at is not None

    # 4. Test get_child_by_family (creates new token in same family)
    child_jti = uuid.uuid4()
    child_token = await repo.create(
        jti=child_jti,
        family_id=family_id,
        user_id=user_id,
        expires_at=expires_at,
    )
    await db_session.commit()

    child = await repo.get_child_by_family(family_id)
    assert child is not None
    assert child.jti == child_jti

    # 5. Test get_active_by_user
    active_tokens = await repo.get_active_by_user(user_id)
    assert len(active_tokens) == 1
    assert active_tokens[0].jti == child_jti

    # 6. Test revoke
    await repo.revoke(child_jti)
    await db_session.commit()
    db_session.expire_all()
    
    fetched_child = await repo.get_by_jti(child_jti)
    assert fetched_child.revoked_at is not None

    # 7. Test revoke_family
    t3_jti = uuid.uuid4()
    await repo.create(
        jti=t3_jti,
        family_id=family_id,
        user_id=user_id,
        expires_at=expires_at,
    )
    await db_session.commit()

    await repo.revoke_family(family_id)
    await db_session.commit()
    db_session.expire_all()

    t3 = await repo.get_by_jti(t3_jti)
    assert t3.revoked_at is not None

    # 8. Test revoke_all_user
    new_fam = uuid.uuid4()
    t4_jti = uuid.uuid4()
    await repo.create(
        jti=t4_jti,
        family_id=new_fam,
        user_id=user_id,
        expires_at=expires_at,
    )
    await db_session.commit()

    await repo.revoke_all_user(user_id)
    await db_session.commit()
    db_session.expire_all()

    t4 = await repo.get_by_jti(t4_jti)
    assert t4.revoked_at is not None
