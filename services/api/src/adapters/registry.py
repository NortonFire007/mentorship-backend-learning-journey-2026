from typing import Dict, Type
from src.adapters.base import BasePriceAdapter

_adapters_registry: Dict[str, Type[BasePriceAdapter]] = {}


def register_adapter(name: str, adapter_cls: Type[BasePriceAdapter]) -> None:
    """Register an adapter class by provider name."""
    _adapters_registry[name] = adapter_cls


def get_adapter(provider_name: str) -> BasePriceAdapter:
    """
    Get an instance of the adapter registered under provider_name.
    Raises ValueError if provider_name is unknown.
    """
    if provider_name not in _adapters_registry:
        raise ValueError(f"Unknown price provider: {provider_name}")
    
    adapter_cls = _adapters_registry[provider_name]
    return adapter_cls()
