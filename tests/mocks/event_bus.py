from typing import List, Type, Tuple
from src.core.events.base import Event, EventPublisher

class MockEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.published_events: List[Event] = []
        self.published_records: List[Tuple[str, Event]] = []

    async def publish(self, routing_key: str, event: Event) -> None:
        """
        Record the published event and its routing key in memory.
        """
        self.published_events.append(event)
        self.published_records.append((routing_key, event))

    def assert_published(self, event_type: Type[Event]) -> None:
        """
        Assert that an event of the specified type was published.
        """
        found = any(isinstance(event, event_type) for event in self.published_events)
        assert found, f"Expected event of type {event_type.__name__} to be published, but it was not."

    def assert_published_with_key(self, routing_key: str, event_type: Type[Event]) -> None:
        """
        Assert that an event of the specified type was published with the given routing key.
        """
        found = any(
            rk == routing_key and isinstance(ev, event_type)
            for rk, ev in self.published_records
        )
        assert found, f"Expected event of type {event_type.__name__} to be published with routing key '{routing_key}', but it was not."

    def clear(self) -> None:
        """
        Clear all recorded events.
        """
        self.published_events.clear()
        self.published_records.clear()
