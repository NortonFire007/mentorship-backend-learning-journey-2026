from fastapi import APIRouter, Depends
from src.core.taskiq import result_backend
from taskiq import TaskiqResult
from src.domains.auth.dependencies import get_current_user
from src.domains.users.models import User

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.get("/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get the status and result of a background task.
    """
    if await result_backend.is_result_ready(task_id):
        result: TaskiqResult = await result_backend.get_result(task_id)
        return {
            "task_id": task_id,
            "is_ready": True,
            "is_err": result.is_err,
            "return_value": result.return_value,
            "error": str(result.error) if result.is_err else None,
            "execution_time": result.execution_time
        }
    return {
        "task_id": task_id,
        "is_ready": False
    }
