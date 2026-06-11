import inspect
from typing import Dict, List, Callable, Awaitable, Union
from src.core.events.base import Event, EventPublisher

EventHandler = Union[Callable[[Event], Awaitable[None]], Callable[[Event], None]]

class InMemoryEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, routing_key: str, handler: EventHandler) -> None:
        """
        Register a callback handler for a given routing key.
        """
        if routing_key not in self._handlers:
            self._handlers[routing_key] = []
        self._handlers[routing_key].append(handler)

    async def publish(self, routing_key: str, event: Event) -> None:
        """
        Publish an event, invoking all registered handlers synchronously in-process.
        """
        handlers = self._handlers.get(routing_key, [])
        for handler in handlers:
            if inspect.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
