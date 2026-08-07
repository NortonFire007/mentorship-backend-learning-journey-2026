import pytest
import uuid
import html
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import Context, TaskiqDepends
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from src.core.enums import AlertStatus
from src.domains.alerts.tasks import process_alert_created_event
from src.domains.users.models import User
from src.domains.alerts.models import Alert
from tests.factories import UserFactory, SubscriptionFactory, AlertFactory


@pytest.fixture(autouse=True)
def mock_sleep():
    """Mock asyncio.sleep to speed up tests."""
    with patch("asyncio.sleep", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def mock_context():
    """Mock Taskiq Context with a mocked bot singleton in state."""
    ctx = MagicMock(spec=Context)
    ctx.state = MagicMock()
    ctx.state.bot = AsyncMock(spec=Bot)
    return ctx


@pytest.mark.asyncio
async def test_process_alert_created_event_skipped(db_session: AsyncSession, mock_context):
    """
    Test that if a user has no telegram_chat_id, the alert is marked as SKIPPED.
    """
    user = await UserFactory.acreate(db_session, telegram_chat_id=None)
    sub = await SubscriptionFactory.acreate(db_session, user=user)
    alert = await AlertFactory.acreate(db_session, subscription=sub, status=AlertStatus.PENDING)

    event_dict = {
        "event_id": str(uuid.uuid4()),
        "alert_id": str(alert.id),
        "user_id": str(user.id),
    }

    # Execute the task
    await process_alert_created_event(
        event_dict,
        context=mock_context,
        db=db_session
    )

    # Check alert status in DB
    await db_session.refresh(alert)
    assert alert.status == AlertStatus.SKIPPED

    # Ensure no bot message was sent
    mock_context.state.bot.send_message.assert_not_called()
    mock_context.state.bot.send_photo.assert_not_called()


@pytest.mark.asyncio
async def test_process_alert_created_event_sent_text_only(db_session: AsyncSession, mock_context):
    """
    Test successful text-only notification sending when image_url is None.
    """
    user = await UserFactory.acreate(db_session, telegram_chat_id=55555)
    sub = await SubscriptionFactory.acreate(db_session, user=user, destination="Paris")
    alert = await AlertFactory.acreate(db_session, subscription=sub, status=AlertStatus.PENDING, image_url=None, deep_link="http://example.com")

    event_dict = {
        "event_id": str(uuid.uuid4()),
        "alert_id": str(alert.id),
        "user_id": str(user.id),
    }

    await process_alert_created_event(
        event_dict,
        context=mock_context,
        db=db_session
    )

    await db_session.refresh(alert)
    assert alert.status == AlertStatus.SENT

    mock_context.state.bot.send_message.assert_called_once()
    mock_context.state.bot.send_photo.assert_not_called()

    call_args = mock_context.state.bot.send_message.call_args[1]
    assert call_args["chat_id"] == 55555
    assert "Paris" in call_args["text"]
    assert "HTML" == call_args["parse_mode"]
    assert call_args["reply_markup"] is not None


@pytest.mark.asyncio
async def test_process_alert_created_event_sent_with_photo(db_session: AsyncSession, mock_context):
    """
    Test notification sending with photo when image_url is present.
    """
    user = await UserFactory.acreate(db_session, telegram_chat_id=66666)
    sub = await SubscriptionFactory.acreate(db_session, user=user, destination="Tokyo")
    alert = await AlertFactory.acreate(db_session, subscription=sub, status=AlertStatus.PENDING, image_url="http://image.com/tokyo.jpg")

    event_dict = {
        "event_id": str(uuid.uuid4()),
        "alert_id": str(alert.id),
        "user_id": str(user.id),
    }

    await process_alert_created_event(
        event_dict,
        context=mock_context,
        db=db_session
    )

    await db_session.refresh(alert)
    assert alert.status == AlertStatus.SENT

    mock_context.state.bot.send_photo.assert_called_once()
    mock_context.state.bot.send_message.assert_not_called()

    call_args = mock_context.state.bot.send_photo.call_args[1]
    assert call_args["chat_id"] == 66666
    assert call_args["photo"] == "http://image.com/tokyo.jpg"
    assert "Tokyo" in call_args["caption"]
    assert "HTML" == call_args["parse_mode"]


@pytest.mark.asyncio
async def test_process_alert_created_event_html_escaping(db_session: AsyncSession, mock_context):
    """
    Test that dynamic strings are properly escaped to prevent HTML entity parsing errors.
    """
    user = await UserFactory.acreate(db_session, telegram_chat_id=77777)
    # Use characters that require escaping in destination & currency
    sub = await SubscriptionFactory.acreate(db_session, user=user, destination="Cafe <Best> & Bar")
    alert = await AlertFactory.acreate(db_session, subscription=sub, status=AlertStatus.PENDING, image_url=None)

    event_dict = {
        "event_id": str(uuid.uuid4()),
        "alert_id": str(alert.id),
        "user_id": str(user.id),
    }

    await process_alert_created_event(
        event_dict,
        context=mock_context,
        db=db_session
    )

    mock_context.state.bot.send_message.assert_called_once()
    text = mock_context.state.bot.send_message.call_args[1]["text"]
    
    # Destination must be properly escaped
    assert "Cafe &lt;Best&gt; &amp; Bar" in text
    assert "Cafe <Best> & Bar" not in text


@pytest.mark.asyncio
async def test_process_alert_created_event_omits_default_fields(db_session: AsyncSession, mock_context):
    """
    Test that fields containing default values like "string" or empty values are omitted.
    """
    user = await UserFactory.acreate(db_session, telegram_chat_id=77777)
    sub = await SubscriptionFactory.acreate(db_session, user=user, origin="string", destination="Kyiv")
    alert = await AlertFactory.acreate(db_session, subscription=sub, status=AlertStatus.PENDING, image_url=None)

    event_dict = {
        "event_id": str(uuid.uuid4()),
        "alert_id": str(alert.id),
        "user_id": str(user.id),
    }

    await process_alert_created_event(
        event_dict,
        context=mock_context,
        db=db_session
    )

    mock_context.state.bot.send_message.assert_called_once()
    text = mock_context.state.bot.send_message.call_args[1]["text"]

    # Destination should be shown since it is valid
    assert "Destination:" in text
    assert "Kyiv" in text
    
    # Origin was "string", so "From:" line should be omitted
    assert "From:" not in text
    assert "string" not in text


@pytest.mark.asyncio
async def test_process_alert_created_event_forbidden_unlinks_user(db_session: AsyncSession, mock_context):

    """
    Test that if bot raises TelegramForbiddenError (user blocked the bot), 
    the alert status is set to FAILED and user.telegram_chat_id is set to None.
    """
    user = await UserFactory.acreate(db_session, telegram_chat_id=88888)
    sub = await SubscriptionFactory.acreate(db_session, user=user)
    alert = await AlertFactory.acreate(db_session, subscription=sub, status=AlertStatus.PENDING, image_url=None)

    # Set mock bot to raise TelegramForbiddenError
    mock_context.state.bot.send_message.side_effect = TelegramForbiddenError(
        method=MagicMock(), message="Forbidden: bot was blocked by the user"
    )

    event_dict = {
        "event_id": str(uuid.uuid4()),
        "alert_id": str(alert.id),
        "user_id": str(user.id),
    }

    await process_alert_created_event(
        event_dict,
        context=mock_context,
        db=db_session
    )

    # The task should complete gracefully without raising an exception.
    await db_session.refresh(alert)
    await db_session.refresh(user)

    assert alert.status == AlertStatus.FAILED
    assert user.telegram_chat_id is None


@pytest.mark.asyncio
async def test_process_alert_created_event_bad_request_unlinks_user(db_session: AsyncSession, mock_context):
    """
    Test that if bot raises TelegramBadRequest (e.g. invalid chat ID),
    the alert status is set to FAILED and user.telegram_chat_id is set to None.
    """
    user = await UserFactory.acreate(db_session, telegram_chat_id=99999)
    sub = await SubscriptionFactory.acreate(db_session, user=user)
    alert = await AlertFactory.acreate(db_session, subscription=sub, status=AlertStatus.PENDING, image_url=None)

    mock_context.state.bot.send_message.side_effect = TelegramBadRequest(
        method=MagicMock(), message="Bad Request: chat not found"
    )

    event_dict = {
        "event_id": str(uuid.uuid4()),
        "alert_id": str(alert.id),
        "user_id": str(user.id),
    }

    await process_alert_created_event(
        event_dict,
        context=mock_context,
        db=db_session
    )

    await db_session.refresh(alert)
    await db_session.refresh(user)

    assert alert.status == AlertStatus.FAILED
    assert user.telegram_chat_id is None


@pytest.mark.asyncio
async def test_process_alert_created_event_image_url_fallback(db_session: AsyncSession, mock_context):
    """
    Test that if send_photo raises TelegramBadRequest (invalid photo format or URL),
    it falls back to text-only send_message and status becomes SENT.
    """
    user = await UserFactory.acreate(db_session, telegram_chat_id=11111)
    sub = await SubscriptionFactory.acreate(db_session, user=user, destination="Berlin")
    alert = await AlertFactory.acreate(db_session, subscription=sub, status=AlertStatus.PENDING, image_url="http://image.com/bad.png")

    # Mock send_photo to fail, but send_message to succeed
    mock_context.state.bot.send_photo.side_effect = TelegramBadRequest(
        method=MagicMock(), message="Bad Request: wrong file identifier/HTTP URL specified"
    )

    event_dict = {
        "event_id": str(uuid.uuid4()),
        "alert_id": str(alert.id),
        "user_id": str(user.id),
    }

    await process_alert_created_event(
        event_dict,
        context=mock_context,
        db=db_session
    )

    await db_session.refresh(alert)
    assert alert.status == AlertStatus.SENT

    mock_context.state.bot.send_photo.assert_called_once()
    mock_context.state.bot.send_message.assert_called_once()
    
    # Assert fallback message properties
    text = mock_context.state.bot.send_message.call_args[1]["text"]
    assert "Berlin" in text


@pytest.mark.asyncio
async def test_process_alert_created_event_retry_on_flood(db_session: AsyncSession, mock_context):
    """
    Test that if bot raises TelegramRetryAfter (rate limit), it re-raises the exception
    to trigger Taskiq retry mechanism.
    """
    user = await UserFactory.acreate(db_session, telegram_chat_id=22222)
    sub = await SubscriptionFactory.acreate(db_session, user=user)
    alert = await AlertFactory.acreate(db_session, subscription=sub, status=AlertStatus.PENDING, image_url=None)

    mock_context.state.bot.send_message.side_effect = TelegramRetryAfter(
        method=MagicMock(), message="Flood control", retry_after=5
    )

    event_dict = {
        "event_id": str(uuid.uuid4()),
        "alert_id": str(alert.id),
        "user_id": str(user.id),
    }

    with pytest.raises(TelegramRetryAfter):
        await process_alert_created_event(
            event_dict,
            context=mock_context,
            db=db_session
        )


@pytest.mark.asyncio
async def test_process_alert_created_event_idempotency(db_session: AsyncSession, mock_context):
    """
    Test that duplicate events are ignored via the @idempotent_event decorator.
    """
    user = await UserFactory.acreate(db_session, telegram_chat_id=33333)
    sub = await SubscriptionFactory.acreate(db_session, user=user)
    alert = await AlertFactory.acreate(db_session, subscription=sub, status=AlertStatus.PENDING, image_url=None)

    event_id = str(uuid.uuid4())
    event_dict = {
        "event_id": event_id,
        "alert_id": str(alert.id),
        "user_id": str(user.id),
    }

    # Mock Redis client returned by idempotent_event decorator's internal client
    mock_redis = AsyncMock()
    
    stored_keys = {}
    async def mock_set(key, value, **kwargs):
        if kwargs.get("nx"):
            if key in stored_keys:
                return None
            stored_keys[key] = value
            return True
        stored_keys[key] = value
        return True
        
    mock_redis.set.side_effect = mock_set

    with patch("src.core.events.idempotency.redis_client", mock_redis):
        # First execution
        await process_alert_created_event(
            event_dict,
            context=mock_context,
            db=db_session
        )

        # Second execution (duplicate event)
        await process_alert_created_event(
            event_dict,
            context=mock_context,
            db=db_session
        )

    # Ensure DB status is SENT (from first call)
    await db_session.refresh(alert)
    assert alert.status == AlertStatus.SENT

    # Ensure bot only sent message once
    mock_context.state.bot.send_message.assert_called_once()
