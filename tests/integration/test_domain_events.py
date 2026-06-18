import pytest
from src.main import app
from src.db.database import get_event_publisher
from src.core.events.events import SubscriptionCreatedEvent
from src.core.enums import TravelType, CurrencyEnum
from src.domains.subscriptions.schemas import SubscriptionCreate
from src.domains.subscriptions.repository import SubscriptionRepository
from src.core.events.dispatcher import EventDispatcher
from src.core.events.mixin import EventRecordableMixin
from tests.factories import UserFactory
from tests.mocks.event_bus import MockEventPublisher

@pytest.fixture()
def mock_publisher():
    """
    Fixture providing a MockEventPublisher and registering it as a FastAPI dependency override.
    """
    publisher = MockEventPublisher()
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    yield publisher
    app.dependency_overrides.pop(get_event_publisher, None)


@pytest.mark.asyncio
async def test_create_subscription_publishes_event(verified_user_client, db_session, mock_publisher):
    """
    Asserts that creating a subscription via API successfully extracts and
    dispatches the SubscriptionCreatedEvent via the MockEventPublisher.
    """
    user = verified_user_client.user
    
    # Call the POST subscription endpoint
    payload = {
        "origin": "NYC",
        "destination": "PAR",
        "travel_type": TravelType.FLIGHT.value,
        "max_price": "450.00",
        "currency": CurrencyEnum.USD.value,
    }
    
    response = await verified_user_client.post("/api/v1/subscriptions/", json=payload)
    assert response.status_code == 201
    
    # Assert that MockEventPublisher received the event
    mock_publisher.assert_published(SubscriptionCreatedEvent)
    mock_publisher.assert_published_with_key("subscriptions.subscription.created", SubscriptionCreatedEvent)
    
    # Verify event values match what was created
    event = mock_publisher.published_events[0]
    assert event.user_id == user.id
    assert event.destination == "PAR"
    assert event.subscription_id is not None
 
 
@pytest.mark.asyncio
async def test_database_rollback_discards_events(db_session, mock_publisher):
    """
    Asserts that database rollbacks safely discard recorded domain events
    without dispatching them to the event publisher.
    """
    user = await UserFactory.acreate(db_session)
    
    repository = SubscriptionRepository(db_session)
    sub_data = SubscriptionCreate(
        origin="NYC",
        destination="LON",
        travel_type=TravelType.FLIGHT,
        max_price=500.0,
        currency=CurrencyEnum.USD,
        start_date=None,
        end_date=None,
        duration_days=None,
    )
    subscription = await repository.create(sub_data, user.id)
    
    dispatcher = EventDispatcher(mock_publisher)
    events = dispatcher.extract_events(db_session)
    assert len(events) == 1
    
    await db_session.rollback()
    
    # Assert that no events were published to the mock publisher since we rolled back
    assert len(mock_publisher.published_events) == 0
