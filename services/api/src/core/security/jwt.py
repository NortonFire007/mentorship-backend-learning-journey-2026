import uuid
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, status
from src.core.config import settings


def generate_jti() -> uuid.UUID:
    """Generate a unique JWT ID."""
    return uuid.uuid4()


def encode_access_token(user_id: uuid.UUID, jti: uuid.UUID) -> str:
    """Encode access token with the configured lifetime (default: 15 minutes)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "jti": str(jti),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def encode_refresh_token(user_id: uuid.UUID, jti: uuid.UUID, family_id: uuid.UUID) -> str:
    """Encode refresh token with the configured lifetime (default: 30 days)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "jti": str(jti),
        "family_id": str(family_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode token and check signature/expiry.
    Raises HTTP 401 on expired, invalid signature, or other errors.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
