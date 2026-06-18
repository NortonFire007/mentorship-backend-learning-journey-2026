import uuid
from fastapi import APIRouter, Depends, status
from src.domains.users.schemas import UserCreate, UserRead, UserUpdate, UserWithSubscriptionsRead, UserActiveCountRead
from src.domains.users.service import UserService
from src.domains.users.dependencies import get_user_service
from src.domains.users.models import User
from src.domains.auth.dependencies import get_current_superuser

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

@router.get("/{user_id}", response_model=UserWithSubscriptionsRead)
async def get_user_endpoint(
    user_id: uuid.UUID,
    service: UserService = Depends(get_user_service),
):
    """
    Retrieve user profile details by ID, including their subscriptions.
    Returns 404 if user not found.
    """
    return await service.get_user_by_id_with_subscriptions(user_id)

@router.patch("/{user_id}", response_model=UserRead)
async def update_user_endpoint(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    service: UserService = Depends(get_user_service),
):
    """
    Partially update user profile (e.g., preferred currency or telegram ID).
    """
    return await service.update_user(user_id, user_in)
