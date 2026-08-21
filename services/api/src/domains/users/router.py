import uuid
from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from src.domains.users.schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
    UserWithSubscriptionsRead,
    UserActiveCountRead,
    UserPasswordChange,
    TelegramLinkResponse,
)
from src.domains.users.service import UserService
from src.domains.users.dependencies import get_user_service, get_user_profile_access, get_user_profile_edit_access
from src.domains.users.models import User
from src.domains.auth.dependencies import get_current_superuser, get_redis
from src.core.config import settings

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_in: UserCreate, 
    service: UserService = Depends(get_user_service),
    current_superuser: User = Depends(get_current_superuser),
):
    """
    Register a new user in the system.
    Returns 409 Conflict if email is already taken.
    """
    return await service.create_user(user_in)

@router.get("/stats/active-counts", response_model=list[UserActiveCountRead])
async def get_active_subscription_counts_endpoint(
    service: UserService = Depends(get_user_service),
    current_superuser: User = Depends(get_current_superuser),
):
    """
    Retrieve all users along with the count of their active subscriptions.
    """
    return await service.get_active_subscription_counts()

@router.get("/", response_model=list[UserWithSubscriptionsRead])
async def list_users_endpoint(
    service: UserService = Depends(get_user_service),
    current_superuser: User = Depends(get_current_superuser),
):
    """
    Retrieve a list of all users.
    """
    return await service.get_all_users_with_subscriptions()

@router.get("/mcp-token")
async def get_mcp_token_endpoint(
    current_superuser: User = Depends(get_current_superuser),
) -> dict[str, str]:
    """
    Retrieve the static MCP_API_KEY.
    Requires superuser privileges.
    """
    return {"mcp_token": settings.MCP_API_KEY}

@router.get("/{user_id}", response_model=UserWithSubscriptionsRead)

async def get_user_endpoint(
    user_id: uuid.UUID = Depends(get_user_profile_access),
    service: UserService = Depends(get_user_service),
):
    """
    Retrieve user profile details by ID, including their subscriptions.
    Returns 404 if user not found.
    """
    return await service.get_user_by_id_with_subscriptions(user_id)

@router.patch("/{user_id}", response_model=UserRead)
async def update_user_endpoint(
    user_in: UserUpdate,
    user_id: uuid.UUID = Depends(get_user_profile_edit_access),
    service: UserService = Depends(get_user_service),
):
    """
    Partially update user profile (e.g., preferred currency or telegram ID).
    """
    return await service.update_user(user_id, user_in)

@router.post("/{user_id}/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password_endpoint(
    password_data: UserPasswordChange,
    user_id: uuid.UUID = Depends(get_user_profile_edit_access),
    service: UserService = Depends(get_user_service),
    redis: Redis = Depends(get_redis),
):
    """
    Change the user's password.
    Requires entering the correct old password.
    Revokes all active sessions for this user.
    """
    await service.change_password(user_id, password_data, redis_client=redis)


@router.post("/{user_id}/telegram/link-start", response_model=TelegramLinkResponse)
async def generate_telegram_link_endpoint(
    user_id: uuid.UUID = Depends(get_user_profile_edit_access),
    service: UserService = Depends(get_user_service),
    redis: Redis = Depends(get_redis),
):
    """
    Generate a Telegram deep linking URL for the specified user.
    Only the account owner or a superuser can call this endpoint.
    """
    # Ensure user exists (raises 404 if not found)
    await service.get_user_by_id(user_id)
    
    link = await service.generate_telegram_link(user_id, redis)
    return TelegramLinkResponse(link=link, expires_in_seconds=900)

