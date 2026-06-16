from fastapi import APIRouter, Depends, status, Request, Response, Cookie, HTTPException
from redis.asyncio import Redis
from src.core.config import settings
from src.domains.auth.schemas import RegisterRequest, LoginRequest, TokenResponse
from src.domains.auth.service import AuthService
from src.domains.auth.dependencies import get_auth_service, get_redis
from src.domains.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user account.
    Returns 409 if the email is already in use, or 422 if validation fails.
    """
    return await service.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    request: Request,
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service),
    redis: Redis = Depends(get_redis),
):
    """
    Authenticate a user and issue access and refresh tokens.
    Refresh token is set as an HttpOnly cookie.
    """
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    token_pair = await service.login(
        email=data.email,
        password=data.password,
        redis_client=redis,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    response.set_cookie(
        key="refresh_token",
        value=token_pair.refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/auth",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )

    return TokenResponse(
        access_token=token_pair.access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    request: Request,
    refresh_token: str | None = Cookie(None),
    service: AuthService = Depends(get_auth_service),
    redis: Redis = Depends(get_redis),
):
    """
    Rotate refresh token and issue a new access token.
    Refresh token is read from and written back to HttpOnly cookie.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing",
        )

    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    token_pair = await service.refresh(
        refresh_token_str=refresh_token,
        redis_client=redis,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    response.set_cookie(
        key="refresh_token",
        value=token_pair.refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/auth",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )

    return TokenResponse(
        access_token=token_pair.access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
