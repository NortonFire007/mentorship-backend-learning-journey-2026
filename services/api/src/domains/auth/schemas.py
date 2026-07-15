from pydantic import BaseModel, EmailStr
from src.core.validators import PasswordStr


class RegisterRequest(BaseModel):
    """Schema for a registration request."""
    name: str
    surname: str
    email: EmailStr
    password: PasswordStr


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
