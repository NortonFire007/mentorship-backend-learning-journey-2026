import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from decimal import Decimal
from datetime import date
import logging

from src.core.config import settings
from src.core.enums import TravelType, CurrencyEnum
from src.adapters.registry import get_adapter
from src.adapters.providers.apify_airbnb import ApifyAirbnbAdapter
from src.adapters.exceptions import AuthError, TimeoutError, AdapterError, ParseError
from src.domains.subscriptions.models import Subscription


@pytest.mark.asyncio
async def test_get_adapter_apify_airbnb():
    """Verify that registry returns ApifyAirbnbAdapter instance."""
    adapter = get_adapter("apify_airbnb")
    assert isinstance(adapter, ApifyAirbnbAdapter)
    assert adapter.execution_mode == "async_webhook"
    assert adapter.provider_name == "apify_airbnb"


@pytest.mark.asyncio
async def test_dispatch_success():
    """Verify successful actor dispatch returns run ID and sends correct inputs."""
    sub = Subscription(
        destination="Paris, France",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 10)
    )

    adapter = ApifyAirbnbAdapter()
    
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"data": {"id": "run-12345"}}

    with patch("src.core.config.settings.APIFY_API_TOKEN", "token123"), \
         patch("src.core.config.settings.APIFY_WEBHOOK_SECRET", "secret123"), \
         patch("src.core.config.settings.BASE_URL", "http://testserver"), \
         patch("src.core.config.settings.APIFY_MAX_LISTINGS", 10), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        mock_post.return_value = mock_response
        run_id = await adapter.dispatch(sub)
        
        assert run_id == "run-12345"
        mock_post.assert_called_once()
        
        # Verify call arguments
        url_arg = mock_post.call_args[0][0]
        assert "runs?webhooks=" in url_arg
        
        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer token123"
        
        json_body = mock_post.call_args[1]["json"]
        assert json_body["locationQueries"] == ["Paris, France"]
        assert json_body["checkIn"] == "2026-07-01"
        assert json_body["checkOut"] == "2026-07-10"
        assert json_body["skipDetailPages"] is True
        assert json_body["maxListings"] == 10


@pytest.mark.asyncio
async def test_dispatch_unauthorized():
    """Verify dispatch raises AuthError on 401."""
    sub = Subscription(destination="Rome")
    adapter = ApifyAirbnbAdapter()

    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("src.core.config.settings.APIFY_API_TOKEN", "invalid-token"), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        mock_post.return_value = mock_response
        with pytest.raises(AuthError) as exc_info:
            await adapter.dispatch(sub)
        assert "Unauthorized" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dispatch_timeout():
    """Verify dispatch raises TimeoutError on httpx Timeout."""
    sub = Subscription(destination="Rome")
    adapter = ApifyAirbnbAdapter()

    with patch("src.core.config.settings.APIFY_API_TOKEN", "token"), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        mock_post.side_effect = httpx.TimeoutException("Timeout")
        with pytest.raises(TimeoutError):
            await adapter.dispatch(sub)


@pytest.mark.asyncio
async def test_fetch_dataset_success():
    """Verify fetch_dataset maps items correctly including thumbnail."""
    adapter = ApifyAirbnbAdapter()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "price": 120.50,
            "currency": "EUR",
            "location": "Berlin",
            "url": "https://airbnb.com/rooms/1",
            "thumbnail": "https://img.com/1.jpg"
        },
        {
            "price": 85.00,
            "currency": "USD",
            "city": "Rome",
            "url": "https://airbnb.com/rooms/2",
            "thumbnail": None
        }
    ]

    with patch("src.core.config.settings.APIFY_API_TOKEN", "token"), \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        
        mock_get.return_value = mock_response
        results = await adapter.fetch_dataset("dataset-123")
        
        assert len(results) == 2
        
        assert results[0].price == Decimal("120.50")
        assert results[0].currency == CurrencyEnum.EUR
        assert results[0].travel_type == TravelType.HOTEL
        assert results[0].destination == "Berlin"
        assert results[0].deep_link == "https://airbnb.com/rooms/1"
        assert results[0].image_url == "https://img.com/1.jpg"
        
        assert results[1].price == Decimal("85.00")
        assert results[1].currency == CurrencyEnum.USD
        assert results[1].travel_type == TravelType.HOTEL
        assert results[1].destination == "Rome"
        assert results[1].deep_link == "https://airbnb.com/rooms/2"
        assert results[1].image_url is None


@pytest.mark.asyncio
async def test_fetch_dataset_empty():
    """Verify fetch_dataset handles empty dataset gracefully returning empty list."""
    adapter = ApifyAirbnbAdapter()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch("src.core.config.settings.APIFY_API_TOKEN", "token"), \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        
        mock_get.return_value = mock_response
        results = await adapter.fetch_dataset("dataset-empty")
        assert results == []


@pytest.mark.asyncio
async def test_fetch_dataset_skips_malformed(caplog):
    """Verify fetch_dataset skips malformed items and emits warning."""
    adapter = ApifyAirbnbAdapter()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            # Missing price
            "currency": "EUR",
            "location": "Berlin",
            "url": "https://airbnb.com/rooms/1"
        },
        {
            # Missing url
            "price": 120.50,
            "currency": "EUR",
            "location": "Berlin"
        },
        {
            # Unsupported currency
            "price": 120.50,
            "currency": "GBP",
            "location": "Berlin",
            "url": "https://airbnb.com/rooms/1"
        },
        {
            # Valid item
            "price": 85.00,
            "currency": "USD",
            "location": "Rome",
            "url": "https://airbnb.com/rooms/2"
        }
    ]

    with patch("src.core.config.settings.APIFY_API_TOKEN", "token"), \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         caplog.at_level(logging.WARNING):
        
        mock_get.return_value = mock_response
        results = await adapter.fetch_dataset("dataset-malformed")
        
        assert len(results) == 1
        assert results[0].price == Decimal("85.00")
        assert results[0].destination == "Rome"
        
        # Verify warning log was emitted
        assert any("Skipping malformed dataset item" in record.message for record in caplog.records) or \
               any("Skipping item due to unsupported currency" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_health_check_passes():
    """Verify health_check returns True on 200."""
    adapter = ApifyAirbnbAdapter()
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("src.core.config.settings.APIFY_API_TOKEN", "token"), \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        
        mock_get.return_value = mock_response
        assert await adapter.health_check() is True


@pytest.mark.asyncio
async def test_health_check_fails_gracefully():
    """Verify health_check returns False on non-200 or timeout."""
    adapter = ApifyAirbnbAdapter()

    # Case 1: Status 401
    mock_response = MagicMock()
    mock_response.status_code = 401
    with patch("src.core.config.settings.APIFY_API_TOKEN", "token"), \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        assert await adapter.health_check() is False

    # Case 2: Exception raised
    with patch("src.core.config.settings.APIFY_API_TOKEN", "token"), \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection failed")
        assert await adapter.health_check() is False
