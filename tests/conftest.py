import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from unittest.mock import patch
from taskiq import InMemoryBroker

# Initialize InMemoryBroker for tests and patch globally before loading main application
test_broker = InMemoryBroker()
test_result_backend = test_broker.result_backend

broker_patch = patch("src.core.taskiq.broker", test_broker)
result_backend_patch = patch("src.core.taskiq.result_backend", test_result_backend)

broker_patch.start()
result_backend_patch.start()

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
    and inject our isolated transaction `db_session`, while preserving the
    Unit of Work event-dispatching lifecycle.
    """
    async def override_get_db():
        from src.db.database import get_event_publisher
        from src.core.events.dispatcher import EventDispatcher
        
        # Resolve the active event publisher (which may be overridden in tests)
        override = app.dependency_overrides.get(get_event_publisher)
        if override:
            import inspect
            if inspect.iscoroutinefunction(override):
                publisher = await override()
            else:
                publisher = override()
        else:
            publisher = await get_event_publisher()
            
        dispatcher = EventDispatcher(publisher)
        dispatcher.setup_session(db_session)
        try:
            yield db_session
            
            # Combine dynamically intercepted commit events with any remaining events
            events_to_publish = getattr(db_session, "_events_to_publish", [])
            events_to_publish.extend(dispatcher.extract_events(db_session))
            
            if db_session.is_active:
                await db_session.commit()
            
            await dispatcher.publish_events(events_to_publish)
        except Exception as e:
            if db_session.is_active:
                await db_session.rollback()
            raise e
        
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac
        
    app.dependency_overrides.clear()
