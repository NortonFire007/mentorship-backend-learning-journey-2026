from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import ClassVar, Literal


@dataclass
class PriceResult:
    provider: str
    origin: str | None
    destination: str
    travel_type: str
    price: Decimal
    currency: str
    departure_date: date | None
    return_date: date | None
    deep_link: str
    image_url: str | None = None


class BasePriceAdapter(ABC):
    execution_mode: ClassVar[Literal["sync", "async_webhook", "async_poll"]]

    @abstractmethod
    async def fetch_prices(self, *args, **kwargs) -> list[PriceResult]:
        """Fetch prices from the provider."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check the health of the connection/credentials to the provider."""
        pass
