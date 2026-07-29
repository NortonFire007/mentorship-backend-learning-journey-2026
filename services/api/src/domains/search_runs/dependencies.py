from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.domains.search_runs.repository import SearchRunRepository

def get_search_run_repository(session: AsyncSession = Depends(get_db)) -> SearchRunRepository:
    return SearchRunRepository(session)
