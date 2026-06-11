from typing import List
from src.core.events.base import Event

class EventRecordableMixin:
    """
    Mixin adding event collection capability to entities.
    """

    def record_event(self, event: Event) -> None:
        """
        Record a new event on this entity.
        """
        if not hasattr(self, "_domain_events"):
            self._domain_events = []
        self._domain_events.append(event)

    def collect_events(self) -> List[Event]:
        """
        Collect and clear recorded events.
        """
        if not hasattr(self, "_domain_events"):
            return []
        events = list(self._domain_events)
        self._domain_events.clear()
        return events
