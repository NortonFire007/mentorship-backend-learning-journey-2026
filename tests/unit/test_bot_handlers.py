import pytest
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch
from aiogram.filters import CommandObject
from aiogram.types import Message, Chat, User as TGUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.start import start_handler
from src.domains.users.models import User
from tests.factories import UserFactory


def create_mock_message(chat_id: int, text: str = "/start") -> AsyncMock:
    """Helper to build a mock Message object using AsyncMock."""
    message = AsyncMock(spec=Message)
    message.chat = Chat(id=chat_id, type="private")
    message.from_user = TGUser(id=chat_id, is_bot=False, first_name="Test", last_name="User")
    message.text = text
    message.answer = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_bot_start_bare_command():
    """
    Test that a bare /start command (no token) replies with the onboarding message.
    """
    message = create_mock_message(12345)
    command = CommandObject(prefix="/", command="start", args=None)
    
    await start_handler(message, command)
    
    message.answer.assert_called_once()
    response_text = message.answer.call_args[0][0]
    assert "Welcome to the Mentorship Price Alert Bot" in response_text


@pytest.mark.asyncio
async def test_bot_start_expired_token():
    """
    Test that an expired or invalid token replies with an expiry error message.
    """
    message = create_mock_message(12345)
    command = CommandObject(prefix="/", command="start", args="expired_or_invalid_token")
    
    # Mock Redis getdel returning None
    mock_redis = AsyncMock()
    mock_redis.getdel.return_value = None
    
    with patch("src.bot.handlers.start.get_redis_client", return_value=mock_redis):
        await start_handler(message, command)
        
    mock_redis.getdel.assert_called_once_with("tg_link:expired_or_invalid_token")
    message.answer.assert_called_once()
    response_text = message.answer.call_args[0][0]
    assert "expired or has already been used" in response_text


@pytest.mark.asyncio
async def test_bot_start_success(db_session: AsyncSession):
    """
    Test successful account linking using a valid deep link token.
    """
    user = await UserFactory.acreate(db_session, telegram_chat_id=None)
    telegram_chat_id = 987654321
    
    message = create_mock_message(telegram_chat_id)
    command = CommandObject(prefix="/", command="start", args="valid_token")
    
    mock_redis = AsyncMock()
    mock_redis.getdel.return_value = str(user.id)
    
    @asynccontextmanager
    async def mock_db_transaction(publisher=None):
        async with db_session.begin_nested():
            yield db_session

    with patch("src.bot.handlers.start.get_redis_client", return_value=mock_redis), \
         patch("src.bot.handlers.start.db_transaction", side_effect=mock_db_transaction):
        await start_handler(message, command)
        
    mock_redis.getdel.assert_called_once_with("tg_link:valid_token")
    message.answer.assert_called_once()
    response_text = message.answer.call_args[0][0]
    assert "Your account is now connected" in response_text
    
    # Check that telegram_chat_id was persisted in the DB
    await db_session.refresh(user)
    assert user.telegram_chat_id == telegram_chat_id


@pytest.mark.asyncio
async def test_bot_start_already_linked(db_session: AsyncSession):
    """
    Test that linking a Telegram account that is already connected to the same
    user account returns a friendly already-linked message.
    """
    telegram_chat_id = 12121212
    user = await UserFactory.acreate(db_session, telegram_chat_id=telegram_chat_id)
    
    message = create_mock_message(telegram_chat_id)
    command = CommandObject(prefix="/", command="start", args="some_token")
    
    mock_redis = AsyncMock()
    mock_redis.getdel.return_value = str(user.id)
    
    @asynccontextmanager
    async def mock_db_transaction(publisher=None):
        async with db_session.begin_nested():
            yield db_session

    with patch("src.bot.handlers.start.get_redis_client", return_value=mock_redis), \
         patch("src.bot.handlers.start.db_transaction", side_effect=mock_db_transaction):
        await start_handler(message, command)
        
    message.answer.assert_called_once()
    response_text = message.answer.call_args[0][0]
    assert "already linked to this Mentorship account" in response_text


@pytest.mark.asyncio
async def test_bot_start_unique_constraint_violation(db_session: AsyncSession):
    """
    Test that trying to link a Telegram account that is already linked to a
    DIFFERENT Mentorship account triggers an IntegrityError, catches it,
    and returns a clean user-facing error message without crash.
    """
    telegram_chat_id = 55555555
    # User A is already connected to this telegram_chat_id
    user_a = await UserFactory.acreate(db_session, telegram_chat_id=telegram_chat_id)
    # User B is a different user with no chat ID linked
    user_b = await UserFactory.acreate(db_session, telegram_chat_id=None)
    
    # Message comes from the owner of telegram_chat_id
    message = create_mock_message(telegram_chat_id)
    # We attempt to link User B to the Telegram chat
    command = CommandObject(prefix="/", command="start", args="token_for_user_b")
    
    mock_redis = AsyncMock()
    mock_redis.getdel.return_value = str(user_b.id)
    
    @asynccontextmanager
    async def mock_db_transaction(publisher=None):
        async with db_session.begin_nested():
            yield db_session

    with patch("src.bot.handlers.start.get_redis_client", return_value=mock_redis), \
         patch("src.bot.handlers.start.db_transaction", side_effect=mock_db_transaction):
        await start_handler(message, command)
        
    message.answer.assert_called_once()
    response_text = message.answer.call_args[0][0]
    assert "already linked to a different Mentorship account" in response_text
    
    # Verify User B was not updated in the DB
    await db_session.refresh(user_b)
    assert user_b.telegram_chat_id is None
