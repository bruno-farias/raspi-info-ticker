"""Currency exchange rate plugin for the info ticker."""

import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .base import BasePlugin, PluginConfig


class CurrencyPluginConfig(PluginConfig):
    """Configuration for currency plugin."""
    api_key: str = Field(..., description="Currency API key")
    base_currency: str = Field(default="USD", description="Base currency")
    target_currencies: List[str] = Field(
        default=["EUR", "GBP", "JPY", "BRL"],
        description="Currencies to track"
    )
    show_change: bool = Field(default=True, description="Show 24h change")
    decimal_places: int = Field(default=4, description="Decimal places for rates")


class CurrencyPlugin(BasePlugin):
    """Plugin for fetching and displaying currency exchange rates."""

    name = "currency"
    version = "1.0.0"
    description = "Currency Exchange Rates"
    author = "System"

    def __init__(self, config: Optional[CurrencyPluginConfig] = None):
        """Initialize currency plugin."""
        super().__init__(config or CurrencyPluginConfig())
        self.base_url = "https://api.freecurrencyapi.com/v1"

    def get_config_schema(self) -> type[BaseModel]:
        """Get configuration schema."""
        return CurrencyPluginConfig

    async def fetch_data(self) -> Dict[str, Any]:
        """Fetch currency data from API."""
        if not self.config.api_key:
            raise ValueError("Currency API key not configured")

        async with aiohttp.ClientSession() as session:
            # Fetch latest rates
            params = {
                "apikey": self.config.api_key,
                "base_currency": self.config.base_currency,
                "currencies": ",".join(self.config.target_currencies)
            }

            async with session.get(f"{self.base_url}/latest", params=params) as response:
                response.raise_for_status()
                latest_data = await response.json()

            # Fetch historical rates for change calculation if enabled
            historical_data = None
            if self.config.show_change:
                # Get yesterday's date
                from datetime import datetime, timedelta
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

                hist_params = {
                    "apikey": self.config.api_key,
                    "date": yesterday,
                    "base_currency": self.config.base_currency,
                    "currencies": ",".join(self.config.target_currencies)
                }

                try:
                    async with session.get(f"{self.base_url}/historical", params=hist_params) as response:
                        response.raise_for_status()
                        historical_data = await response.json()
                except Exception as e:
                    self.logger.warning(f"Failed to fetch historical data: {e}")

        return {
            "latest": latest_data,
            "historical": historical_data,
            "base_currency": self.config.base_currency,
            "target_currencies": self.config.target_currencies
        }

    def get_display_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format currency data for display."""
        latest = data.get("latest", {})
        historical = data.get("historical", {})

        if not latest or "data" not in latest:
            return {"error": "No currency data available"}

        latest_rates = latest.get("data", {})
        historical_rates = historical.get("data", {}) if historical else {}

        display = {
            "base_currency": self.config.base_currency,
            "rates": {},
            "changes": {},
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

        for currency in self.config.target_currencies:
            if currency in latest_rates:
                # Get the rate
                rate = latest_rates[currency]
                display["rates"][currency] = round(rate, self.config.decimal_places)

                # Calculate change if historical data is available
                if currency in historical_rates and self.config.show_change:
                    old_rate = historical_rates[currency]
                    if old_rate > 0:
                        change_percent = ((rate - old_rate) / old_rate) * 100
                        display["changes"][currency] = round(change_percent, 2)

        # Add formatted pairs for easy display
        display["pairs"] = []
        for currency, rate in display["rates"].items():
            pair_data = {
                "pair": f"{self.config.base_currency}/{currency}",
                "rate": rate,
                "formatted": f"{self.config.base_currency}/{currency}: {rate}"
            }

            if currency in display["changes"]:
                change = display["changes"][currency]
                if change > 0:
                    pair_data["change_indicator"] = f"↑ +{change}%"
                elif change < 0:
                    pair_data["change_indicator"] = f"↓ {change}%"
                else:
                    pair_data["change_indicator"] = f"= {change}%"
                pair_data["formatted"] += f" {pair_data['change_indicator']}"

            display["pairs"].append(pair_data)

        return display

    def get_widget_layout(self) -> Dict[str, Any]:
        """Get widget layout preferences."""
        return {
            "type": "currency",
            "min_width": 25,
            "min_height": 4 + len(self.config.target_currencies),
            "expandable": True,
            "resizable": True
        }

    def supports_interaction(self) -> bool:
        """Currency plugin supports currency selection."""
        return True

    async def handle_interaction(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Handle user interactions.

        Supported actions:
        - change_base: Change base currency
        - add_currency: Add target currency
        - remove_currency: Remove target currency
        - toggle_change: Toggle showing 24h change
        """
        if action == "change_base":
            new_base = params.get("currency")
            if new_base and len(new_base) == 3:
                self.config.base_currency = new_base.upper()
                # Clear cache to force refresh
                self._last_data = None
                self._last_update = None
                return {"success": True, "base_currency": self.config.base_currency}
            else:
                return {"success": False, "error": "Invalid currency code"}

        elif action == "add_currency":
            currency = params.get("currency")
            if currency and len(currency) == 3:
                currency = currency.upper()
                if currency not in self.config.target_currencies:
                    self.config.target_currencies.append(currency)
                    # Clear cache to force refresh
                    self._last_data = None
                    self._last_update = None
                    return {"success": True, "target_currencies": self.config.target_currencies}
                else:
                    return {"success": False, "error": "Currency already in list"}
            else:
                return {"success": False, "error": "Invalid currency code"}

        elif action == "remove_currency":
            currency = params.get("currency")
            if currency and currency.upper() in self.config.target_currencies:
                self.config.target_currencies.remove(currency.upper())
                # Clear cache to force refresh
                self._last_data = None
                self._last_update = None
                return {"success": True, "target_currencies": self.config.target_currencies}
            else:
                return {"success": False, "error": "Currency not in list"}

        elif action == "toggle_change":
            self.config.show_change = not self.config.show_change
            # Clear cache to force refresh if enabling
            if self.config.show_change:
                self._last_data = None
                self._last_update = None
            return {"success": True, "show_change": self.config.show_change}

        elif action == "set_currencies":
            currencies = params.get("currencies", [])
            if currencies and all(len(c) == 3 for c in currencies):
                self.config.target_currencies = [c.upper() for c in currencies]
                # Clear cache to force refresh
                self._last_data = None
                self._last_update = None
                return {"success": True, "target_currencies": self.config.target_currencies}
            else:
                return {"success": False, "error": "Invalid currency list"}

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    def get_popular_currencies(self) -> List[str]:
        """Get list of popular currencies."""
        return [
            "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
            "CNY", "INR", "KRW", "SGD", "HKD", "NOK", "SEK", "DKK",
            "PLN", "CZK", "HUF", "RON", "BGN", "HRK", "RUB", "TRY",
            "BRL", "MXN", "ARS", "CLP", "COP", "PEN", "UYU", "ZAR"
        ]