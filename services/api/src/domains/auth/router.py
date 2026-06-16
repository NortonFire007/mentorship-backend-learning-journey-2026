from fastapi import APIRouter, Depends, status
from src.domains.auth.schemas import RegisterRequest
from src.domains.auth.service import AuthService
from src.domains.auth.dependencies import get_auth_service
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
