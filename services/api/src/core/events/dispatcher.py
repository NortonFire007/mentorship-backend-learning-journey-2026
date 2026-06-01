import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.events.base import EventPublisher, Event
from src.core.events.mixin import EventRecordableMixin

logger = logging.getLogger(__name__)

class EventDispatcher:
    def __init__(self, publisher: EventPublisher):
        self.publisher = publisher

    def extract_events(self, session: AsyncSession) -> List[Event]:
        """
        Scans all dirty/loaded models in a session and extracts events BEFORE commit.
        """
        events_to_publish = []
        all_objects = set(session.identity_map.values()) | set(session.new) | set(session.dirty)
        
        for obj in all_objects:
            if isinstance(obj, EventRecordableMixin):
                events_to_publish.extend(obj.collect_events())
                
        return events_to_publish

    async def publish_events(self, events: List[Event]) -> None:
        """
        Publishes the extracted events AFTER a successful database commit.
        Isolates failures so that one failed publish call does not block others.
        """
        for event in events:
            routing_key = self._get_routing_key(event)
            try:
                await self.publisher.publish(routing_key, event)
            except Exception as e:
                # CRITICAL: Isolate publishing errors. Log failure but continue processing remaining events.
                logger.error(
                    f"Failed to publish event {event.event_id} with key {routing_key}. Error: {str(e)}", 
                    exc_info=True
                )

    def _get_routing_key(self, event: Event) -> str:
        """
        Map event type to a standard routing key.
        """
        name = event.__class__.__name__
        if name == "SubscriptionCreatedEvent":
            return "subscriptions.subscription.created"
        return "events.unknown"
