import re
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    """Schema for a registration request."""
    name: str
    surname: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class LoginRequest(BaseModel):
    """Schema for a login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema returned on successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class TokenPair(BaseModel):
    """Internal schema representing a generated token pair."""
    access_token: str
    refresh_token: str
