import uuid
from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.search_runs.models import SearchRun
from src.core.enums import SearchRunStatus


class SearchRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, 
        subscription_id: uuid.UUID, 
        provider: str, 
        external_run_id: str | None = None
    ) -> SearchRun:
        """
        Create a new SearchRun record with status = PENDING.
        """
        run = SearchRun(
            subscription_id=subscription_id,
            provider=provider,
            external_run_id=external_run_id,
            status=SearchRunStatus.PENDING,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_by_external_run_id(self, external_run_id: str) -> SearchRun | None:
        """
        Retrieve a SearchRun record by its external run ID.
        """
        result = await self.session.execute(
            select(SearchRun).where(SearchRun.external_run_id == external_run_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, run_id: uuid.UUID) -> SearchRun | None:
        """
        Retrieve a SearchRun record by its ID.
        """
        result = await self.session.execute(
            select(SearchRun).where(SearchRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def list_by_subscription_id(
        self,
        subscription_id: uuid.UUID,
        limit: int = 10
    ) -> list[SearchRun]:
        """
        Retrieve search runs for a specific subscription ordered by created_at descending.
        """
        stmt = (
            select(SearchRun)
            .where(SearchRun.subscription_id == subscription_id)
            .order_by(SearchRun.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


    async def list_stale_pending(self, older_than_minutes: int = 60) -> List[SearchRun]:
        """
        Retrieve all pending search runs created more than `older_than_minutes` ago.
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
        result = await self.session.execute(
            select(SearchRun).where(
                and_(
                    SearchRun.status == SearchRunStatus.PENDING,
                    SearchRun.created_at <= cutoff_time
                )
            )
        )
        return list(result.scalars().all())

    async def update_status(
        self, 
        run: SearchRun, 
        status: SearchRunStatus, 
        completed_at: datetime | None = None
    ) -> SearchRun:
        """
        Update the status and completion time of a search run.
        """
        run.status = status
        if completed_at is not None:
            run.completed_at = completed_at
        elif status in (SearchRunStatus.COMPLETED, SearchRunStatus.FAILED):
            run.completed_at = datetime.now(timezone.utc)
        
        await self.session.flush()
        return run
