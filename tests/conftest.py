import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.main import app
from src.core.config import settings
from src.db.database import get_db

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """
    Creates a session-scoped SQLAlchemy engine.
    """
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=False,
        future=True
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture()
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides an isolated database session by using the Transaction Rollback pattern.
    Each test gets its own transaction which is rolled back at the end.
    """
    connection = await db_engine.connect()
    transaction = await connection.begin()
    
    # Tie the session to the single connection we opened
    session = AsyncSession(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    
    yield session
    
    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an httpx.AsyncClient configured to bypass FastAPI dependencies
    and inject our isolated transaction `db_session`.
    """
    async def override_get_db():
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac
        
    app.dependency_overrides.clear()
