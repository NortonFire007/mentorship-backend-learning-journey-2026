from typing import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.core.config import settings
from src.core.events.base import EventPublisher
from src.core.events.dispatcher import EventDispatcher
from src.core.events.taskiq_publisher import TaskiqRabbitMQEventPublisher
from src.core.taskiq import rabbitmq_broker

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=settings.DEBUG,
    pool_size=10,          
    max_overflow=20,    
    pool_timeout=30,     
    pool_pre_ping=True,  
    pool_recycle=3600,   
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Factory dependency to retrieve the configured EventPublisher (ABC)
async def get_event_publisher() -> EventPublisher:
    """
    Dependency factory that returns the active EventPublisher provider.
    """
    return TaskiqRabbitMQEventPublisher(rabbitmq_broker)


async def get_db(
    publisher: EventPublisher = Depends(get_event_publisher)
) -> AsyncGenerator[AsyncSession, None]:
    """
    Unified Unit of Work and Transaction Boundary.
    Automatically manages sessions, rollbacks, pre-commit event extraction, and post-commit dispatch.
    """
    async with AsyncSessionLocal() as session:
        dispatcher = EventDispatcher(publisher)
        try:
            yield session
            
            events_to_publish = dispatcher.extract_events(session)
            
            await session.commit()
            
            await dispatcher.publish_events(events_to_publish)
            
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


@asynccontextmanager
async def db_transaction(
    publisher: EventPublisher | None = None
) -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for DB transactions, designed for background workers (TaskIQ).
    Replicates the pre-commit event extraction and post-commit dispatch of get_db().
    """
    if publisher is None:
        publisher = await get_event_publisher()
        
    async with AsyncSessionLocal() as session:
        dispatcher = EventDispatcher(publisher)
        try:
            yield session
            
            events_to_publish = dispatcher.extract_events(session)

            await session.commit()

            await dispatcher.publish_events(events_to_publish)
            
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()
