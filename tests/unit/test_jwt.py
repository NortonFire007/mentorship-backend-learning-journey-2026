import uuid
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from src.core.config import settings
from src.core.security.jwt import (
    generate_jti,
    encode_access_token,
    encode_refresh_token,
    decode_token,
)


def test_generate_jti():
    jti = generate_jti()
    assert isinstance(jti, uuid.UUID)


def test_encode_decode_access_token():
    user_id = uuid.uuid4()
    jti = generate_jti()
    token = encode_access_token(user_id, jti)

    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["jti"] == str(jti)
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_encode_decode_refresh_token():
    user_id = uuid.uuid4()
    jti = generate_jti()
    family_id = uuid.uuid4()
    token = encode_refresh_token(user_id, jti, family_id)

    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["jti"] == str(jti)
    assert payload["family_id"] == str(family_id)
    assert payload["type"] == "refresh"


def test_decode_token_expired():
    user_id = uuid.uuid4()
    jti = generate_jti()

    with patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", -5):
        token = encode_access_token(user_id, jti)

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_decode_token_wrong_secret():
    user_id = uuid.uuid4()
    jti = generate_jti()
    token = encode_access_token(user_id, jti)

    with patch.object(settings, "JWT_SECRET_KEY", "completely_different_secret_key_123456"):
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)

        assert exc_info.value.status_code == 401
        assert "invalid token" in exc_info.value.detail.lower()


def test_decode_token_invalid_format():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not-a-valid-jwt-token-string")

    assert exc_info.value.status_code == 401
    assert "invalid token" in exc_info.value.detail.lower()
