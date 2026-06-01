import uuid
import dataclasses
from datetime import datetime
from taskiq import AsyncKicker
from taskiq_aio_pika import AioPikaBroker
from src.core.events.base import Event, EventPublisher

class TaskiqRabbitMQEventPublisher(EventPublisher):
    def __init__(self, broker: AioPikaBroker) -> None:
        self.broker = broker

    async def publish(self, routing_key: str, event: Event) -> None:
        """
        Publish an event using the TaskIQ AioPikaBroker by kicking a task.
        Converts the dataclass event to a JSON-serializable dictionary.
        """
        event_dict = dataclasses.asdict(event)
        
        # Ensure datetime and other complex fields are JSON-serializable
        for key, value in event_dict.items():
            if isinstance(value, datetime):
                event_dict[key] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                event_dict[key] = str(value)

        kicker = AsyncKicker(
            broker=self.broker,
            task_name=routing_key,
        )
        await kicker.kiq(event_dict)
