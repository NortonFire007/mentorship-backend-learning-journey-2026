import base64
import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import date
from typing import ClassVar, Literal
import httpx

from src.core.config import settings
from src.core.enums import TravelType, CurrencyEnum
from src.adapters.base import BasePriceAdapter, PriceResult
from src.adapters.exceptions import AuthError, TimeoutError, AdapterError, ParseError
from src.domains.subscriptions.models import Subscription

logger = logging.getLogger(__name__)


class ApifyAirbnbAdapter(BasePriceAdapter):
    execution_mode: ClassVar[Literal["sync", "async_webhook", "async_poll"]] = "async_webhook"
    provider_name: ClassVar[str] = "apify_airbnb"

    async def dispatch(self, subscription: Subscription) -> str:
        """
        Dispatches an actor run to Apify.
        """
        if not settings.APIFY_API_TOKEN:
            raise AuthError("Apify API token is not configured.")

        # Build webhook config
        webhooks = [
            {
                "eventTypes": ["ACTOR.RUN.SUCCEEDED", "ACTOR.RUN.FAILED"],
                "requestUrl": f"{settings.BASE_URL}/api/v1/webhooks/apify?token={settings.APIFY_WEBHOOK_SECRET}"
            }
        ]
        webhooks_str = json.dumps(webhooks)
        webhooks_b64 = base64.b64encode(webhooks_str.encode("utf-8")).decode("utf-8")

        actor_input = {
            "locationQueries": [subscription.destination],
            "maxListings": settings.APIFY_MAX_LISTINGS,
            "skipDetailPages": True
        }
        if subscription.start_date:
            actor_input["checkIn"] = subscription.start_date.isoformat()
        if subscription.end_date:
            actor_input["checkOut"] = subscription.end_date.isoformat()

        url = f"https://api.apify.com/v2/acts/{settings.APIFY_ACTOR_ID}/runs?webhooks={webhooks_b64}"
        headers = {
            "Authorization": f"Bearer {settings.APIFY_API_TOKEN}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=actor_input, headers=headers)
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request to Apify timed out: {e}")
        except httpx.RequestError as e:
            raise AdapterError(f"HTTP request error: {e}")

        if response.status_code == 401:
            raise AuthError(f"Unauthorized: Apify returned status {response.status_code}")
        elif response.status_code >= 400:
            raise AdapterError(f"Apify API returned error status {response.status_code}: {response.text}")

        try:
            res_data = response.json()
            run_id = res_data["data"]["id"]
            return run_id
        except (KeyError, ValueError, TypeError) as e:
            raise ParseError(f"Failed to parse Apify response: {e}")

    async def fetch_dataset(self, dataset_id: str) -> list[PriceResult]:
        """
        Fetches dataset items from Apify.
        """
        if not settings.APIFY_API_TOKEN:
            raise AuthError("Apify API token is not configured.")

        url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json"
        headers = {
            "Authorization": f"Bearer {settings.APIFY_API_TOKEN}"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request to Apify timed out: {e}")
        except httpx.RequestError as e:
            raise AdapterError(f"HTTP request error: {e}")

        if response.status_code == 401:
            raise AuthError(f"Unauthorized: Apify returned status {response.status_code}")
        elif response.status_code >= 400:
            raise AdapterError(f"Apify API returned error status {response.status_code}: {response.text}")

        try:
            items = response.json()
            if not isinstance(items, list):
                raise ParseError("Expected a JSON list of dataset items.")
        except ValueError as e:
            raise ParseError(f"Invalid JSON returned from Apify dataset: {e}")

        results = []
        for item in items:
            try:
                price_val = item.get("price")
                currency_val = item.get("currency")
                url_val = item.get("url")
                dest_val = item.get("location") or item.get("city")

                if price_val is None or not currency_val or not url_val or not dest_val:
                    logger.warning(f"Skipping malformed dataset item: {item}")
                    continue

                try:
                    currency_normalized = CurrencyEnum(currency_val.upper())
                except ValueError:
                    logger.warning(f"Skipping item due to unsupported currency: {currency_val}")
                    continue

                try:
                    price_decimal = Decimal(str(price_val))
                except (InvalidOperation, ValueError):
                    logger.warning(f"Skipping item due to invalid price: {price_val}")
                    continue

                # Map dates if present
                departure_date = None
                return_date = None
                for date_key in ("checkIn", "start_date", "departure_date"):
                    if item.get(date_key):
                        try:
                            departure_date = date.fromisoformat(item[date_key])
                            break
                        except ValueError:
                            pass
                for date_key in ("checkOut", "end_date", "return_date"):
                    if item.get(date_key):
                        try:
                            return_date = date.fromisoformat(item[date_key])
                            break
                        except ValueError:
                            pass

                results.append(
                    PriceResult(
                        provider=self.provider_name,
                        origin=None,
                        destination=dest_val,
                        travel_type=TravelType.HOTEL,
                        price=price_decimal,
                        currency=currency_normalized,
                        departure_date=departure_date,
                        return_date=return_date,
                        deep_link=url_val,
                        image_url=item.get("thumbnail")
                    )
                )
            except Exception as e:
                logger.warning(f"Unexpected error parsing dataset item: {e}. Item: {item}")

        return results

    async def fetch_prices(self, *args, **kwargs) -> list[PriceResult]:
        raise NotImplementedError("ApifyAirbnbAdapter does not support fetch_prices directly.")

    async def health_check(self) -> bool:
        """
        Verifies Apify API reachability.
        """
        if not settings.APIFY_API_TOKEN:
            return False

        url = "https://api.apify.com/v2/users/me"
        headers = {
            "Authorization": f"Bearer {settings.APIFY_API_TOKEN}"
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=headers)
                return response.status_code == 200
        except Exception:
            return False
