import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.domains.users.schemas import UserCreate, UserRead, UserUpdate
from src.domains.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_in: UserCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user in the system.
    Returns 409 Conflict if email is already taken.
    """
    service = UserService(db)
    return await service.create_user(user_in)

@router.get("/{user_id}", response_model=UserRead)
async def get_user_endpoint(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve user profile details by ID.
    Returns 404 if user not found.
    """
    service = UserService(db)
    return await service.get_user_by_id(user_id)

@router.patch("/{user_id}", response_model=UserRead)
async def update_user_endpoint(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Partially update user profile (e.g., preferred currency or telegram ID).
    """
    service = UserService(db)
    return await service.update_user(user_id, user_in)
