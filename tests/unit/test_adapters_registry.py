from typing import ClassVar, Literal
import pytest
from src.adapters.base import BasePriceAdapter, PriceResult
from src.adapters.exceptions import (
    AdapterError,
    AuthError,
    ParseError,
    RateLimitError,
    TimeoutError,
)
from src.adapters.registry import get_adapter, register_adapter


class DummyAdapter(BasePriceAdapter):
    execution_mode: ClassVar[Literal["sync", "async_webhook", "async_poll"]] = "sync"

    async def fetch_prices(self, *args, **kwargs) -> list[PriceResult]:
        return []

    async def health_check(self) -> bool:
        return True


def test_cannot_instantiate_base_price_adapter():
    """Verify that BasePriceAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        # BasePriceAdapter is abstract and has abstract methods, so this raises TypeError
        BasePriceAdapter()  # type: ignore


def test_get_adapter_unknown_raises_value_error():
    """Verify that get_adapter with an unknown provider raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        get_adapter("unknown")
    assert "Unknown price provider: unknown" in str(exc_info.value)


def test_register_and_get_adapter_success():
    """Verify that a registered adapter is correctly retrieved by get_adapter."""
    register_adapter("dummy", DummyAdapter)
    adapter = get_adapter("dummy")
    assert isinstance(adapter, DummyAdapter)
    assert adapter.execution_mode == "sync"


def test_exception_hierarchy():
    """Verify that all custom adapter exception classes inherit from AdapterError."""
    assert issubclass(RateLimitError, AdapterError)
    assert issubclass(TimeoutError, AdapterError)
    assert issubclass(AuthError, AdapterError)
    assert issubclass(ParseError, AdapterError)
    assert issubclass(AdapterError, Exception)
