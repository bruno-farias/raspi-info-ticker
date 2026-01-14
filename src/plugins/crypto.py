"""Cryptocurrency plugin for the info ticker."""

import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .base import BasePlugin, PluginConfig


class CryptoPluginConfig(PluginConfig):
    """Configuration for crypto plugin."""
    api_key: Optional[str] = Field(None, description="API key (optional for some providers)")
    provider: str = Field(default="coingecko", description="API provider")
    cryptocurrencies: List[str] = Field(
        default=["bitcoin", "ethereum"],
        description="Cryptocurrencies to track"
    )
    vs_currencies: List[str] = Field(
        default=["usd", "eur"],
        description="Comparison currencies"
    )
    show_market_cap: bool = Field(default=False, description="Show market cap")
    show_volume: bool = Field(default=False, description="Show 24h volume")
    show_change_24h: bool = Field(default=True, description="Show 24h change")
    show_change_7d: bool = Field(default=False, description="Show 7d change")


class CryptoPlugin(BasePlugin):
    """Plugin for fetching and displaying cryptocurrency data."""

    name = "crypto"
    version = "1.0.0"
    description = "Cryptocurrency Prices"
    author = "System"

    def __init__(self, config: Optional[CryptoPluginConfig] = None):
        """Initialize crypto plugin."""
        super().__init__(config or CryptoPluginConfig())
        self.providers = {
            "coingecko": "https://api.coingecko.com/api/v3",
            "coinmarketcap": "https://pro-api.coinmarketcap.com/v1"
        }

    def get_config_schema(self) -> type[BaseModel]:
        """Get configuration schema."""
        return CryptoPluginConfig

    async def fetch_data(self) -> Dict[str, Any]:
        """Fetch cryptocurrency data from API."""
        provider = self.config.provider.lower()

        if provider == "coingecko":
            return await self._fetch_coingecko()
        elif provider == "coinmarketcap":
            return await self._fetch_coinmarketcap()
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def _fetch_coingecko(self) -> Dict[str, Any]:
        """Fetch data from CoinGecko API."""
        base_url = self.providers["coingecko"]

        async with aiohttp.ClientSession() as session:
            # Prepare parameters
            ids = ",".join(self.config.cryptocurrencies)
            vs_currencies = ",".join(self.config.vs_currencies)

            params = {
                "ids": ids,
                "vs_currencies": vs_currencies,
                "include_market_cap": str(self.config.show_market_cap).lower(),
                "include_24hr_vol": str(self.config.show_volume).lower(),
                "include_24hr_change": str(self.config.show_change_24h).lower(),
                "include_7d_change": str(self.config.show_change_7d).lower()
            }

            # Fetch simple price data
            async with session.get(f"{base_url}/simple/price", params=params) as response:
                response.raise_for_status()
                price_data = await response.json()

            # Fetch coin details for additional info
            coin_details = {}
            if self.config.show_market_cap or self.config.show_volume:
                for coin_id in self.config.cryptocurrencies:
                    try:
                        async with session.get(f"{base_url}/coins/{coin_id}") as response:
                            response.raise_for_status()
                            details = await response.json()
                            coin_details[coin_id] = details
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch details for {coin_id}: {e}")

        return {
            "price_data": price_data,
            "coin_details": coin_details,
            "provider": "coingecko"
        }

    async def _fetch_coinmarketcap(self) -> Dict[str, Any]:
        """Fetch data from CoinMarketCap API."""
        if not self.config.api_key:
            raise ValueError("CoinMarketCap requires an API key")

        base_url = self.providers["coinmarketcap"]

        async with aiohttp.ClientSession() as session:
            headers = {
                "X-CMC_PRO_API_KEY": self.config.api_key
            }

            # Map cryptocurrency names to symbols for CoinMarketCap
            symbol_map = {
                "bitcoin": "BTC",
                "ethereum": "ETH",
                "cardano": "ADA",
                "polkadot": "DOT",
                "chainlink": "LINK"
            }

            symbols = ",".join([symbol_map.get(c, c.upper()) for c in self.config.cryptocurrencies])

            params = {
                "symbol": symbols,
                "convert": ",".join([c.upper() for c in self.config.vs_currencies])
            }

            async with session.get(f"{base_url}/cryptocurrency/quotes/latest",
                                  headers=headers, params=params) as response:
                response.raise_for_status()
                data = await response.json()

        return {
            "data": data.get("data", {}),
            "provider": "coinmarketcap"
        }

    def get_display_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format crypto data for display."""
        provider = data.get("provider", "unknown")

        if provider == "coingecko":
            return self._format_coingecko_data(data)
        elif provider == "coinmarketcap":
            return self._format_coinmarketcap_data(data)
        else:
            return {"error": "Unknown data provider"}

    def _format_coingecko_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format CoinGecko data for display."""
        price_data = data.get("price_data", {})
        coin_details = data.get("coin_details", {})

        if not price_data:
            return {"error": "No price data available"}

        display = {
            "coins": [],
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

        for coin_id in self.config.cryptocurrencies:
            if coin_id not in price_data:
                continue

            coin_data = price_data[coin_id]
            details = coin_details.get(coin_id, {})

            coin_display = {
                "id": coin_id,
                "name": details.get("name", coin_id.title()),
                "symbol": details.get("symbol", coin_id[:3]).upper(),
                "prices": {}
            }

            # Add prices for each vs_currency
            for vs_currency in self.config.vs_currencies:
                if vs_currency in coin_data:
                    price = coin_data[vs_currency]
                    coin_display["prices"][vs_currency.upper()] = {
                        "value": price,
                        "formatted": self._format_price(price, vs_currency)
                    }

                    # Add 24h change if available
                    change_key = f"{vs_currency}_24h_change"
                    if change_key in coin_data:
                        change = coin_data[change_key]
                        coin_display["prices"][vs_currency.upper()]["change_24h"] = round(change, 2)
                        coin_display["prices"][vs_currency.upper()]["change_24h_formatted"] = self._format_change(change)

                    # Add 7d change if available
                    change_7d_key = f"{vs_currency}_7d_change"
                    if change_7d_key in coin_data:
                        change_7d = coin_data[change_7d_key]
                        coin_display["prices"][vs_currency.upper()]["change_7d"] = round(change_7d, 2)
                        coin_display["prices"][vs_currency.upper()]["change_7d_formatted"] = self._format_change(change_7d)

                    # Add market cap if available
                    mcap_key = f"{vs_currency}_market_cap"
                    if mcap_key in coin_data:
                        mcap = coin_data[mcap_key]
                        coin_display["prices"][vs_currency.upper()]["market_cap"] = mcap
                        coin_display["prices"][vs_currency.upper()]["market_cap_formatted"] = self._format_large_number(mcap)

                    # Add 24h volume if available
                    vol_key = f"{vs_currency}_24h_vol"
                    if vol_key in coin_data:
                        vol = coin_data[vol_key]
                        coin_display["prices"][vs_currency.upper()]["volume_24h"] = vol
                        coin_display["prices"][vs_currency.upper()]["volume_24h_formatted"] = self._format_large_number(vol)

            display["coins"].append(coin_display)

        return display

    def _format_coinmarketcap_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format CoinMarketCap data for display."""
        cmc_data = data.get("data", {})

        if not cmc_data:
            return {"error": "No data available"}

        display = {
            "coins": [],
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

        for symbol, coin_data in cmc_data.items():
            coin_display = {
                "id": coin_data.get("slug", symbol.lower()),
                "name": coin_data.get("name", symbol),
                "symbol": symbol,
                "prices": {}
            }

            # Process quotes for each currency
            quotes = coin_data.get("quote", {})
            for vs_currency in self.config.vs_currencies:
                vs_curr_upper = vs_currency.upper()
                if vs_curr_upper in quotes:
                    quote = quotes[vs_curr_upper]
                    coin_display["prices"][vs_curr_upper] = {
                        "value": quote.get("price", 0),
                        "formatted": self._format_price(quote.get("price", 0), vs_currency),
                        "change_24h": round(quote.get("percent_change_24h", 0), 2),
                        "change_24h_formatted": self._format_change(quote.get("percent_change_24h", 0)),
                        "change_7d": round(quote.get("percent_change_7d", 0), 2),
                        "change_7d_formatted": self._format_change(quote.get("percent_change_7d", 0)),
                        "market_cap": quote.get("market_cap", 0),
                        "market_cap_formatted": self._format_large_number(quote.get("market_cap", 0)),
                        "volume_24h": quote.get("volume_24h", 0),
                        "volume_24h_formatted": self._format_large_number(quote.get("volume_24h", 0))
                    }

            display["coins"].append(coin_display)

        return display

    def _format_price(self, price: float, currency: str) -> str:
        """Format price with appropriate currency symbol."""
        symbols = {
            "usd": "$",
            "eur": "€",
            "gbp": "£",
            "jpy": "¥",
            "cny": "¥",
            "krw": "₩",
            "inr": "₹"
        }
        symbol = symbols.get(currency.lower(), currency.upper() + " ")

        if price >= 1000:
            return f"{symbol}{price:,.0f}"
        elif price >= 1:
            return f"{symbol}{price:,.2f}"
        else:
            return f"{symbol}{price:.6f}"

    def _format_change(self, change: float) -> str:
        """Format percentage change with indicator."""
        if change > 0:
            return f"↑ +{change:.2f}%"
        elif change < 0:
            return f"↓ {change:.2f}%"
        else:
            return f"= {change:.2f}%"

    def _format_large_number(self, num: float) -> str:
        """Format large numbers with suffixes."""
        if num >= 1e12:
            return f"${num/1e12:.2f}T"
        elif num >= 1e9:
            return f"${num/1e9:.2f}B"
        elif num >= 1e6:
            return f"${num/1e6:.2f}M"
        elif num >= 1e3:
            return f"${num/1e3:.2f}K"
        else:
            return f"${num:.2f}"

    def get_widget_layout(self) -> Dict[str, Any]:
        """Get widget layout preferences."""
        return {
            "type": "crypto",
            "min_width": 30,
            "min_height": 3 + (len(self.config.cryptocurrencies) * len(self.config.vs_currencies)),
            "expandable": True,
            "resizable": True
        }

    def supports_interaction(self) -> bool:
        """Crypto plugin supports interaction."""
        return True

    async def handle_interaction(self, action: str, params: Dict[str, Any]) -> Any:
        """Handle user interactions."""
        if action == "add_coin":
            coin = params.get("coin", "").lower()
            if coin and coin not in self.config.cryptocurrencies:
                self.config.cryptocurrencies.append(coin)
                self._last_data = None
                self._last_update = None
                return {"success": True, "cryptocurrencies": self.config.cryptocurrencies}
            return {"success": False, "error": "Invalid or duplicate coin"}

        elif action == "remove_coin":
            coin = params.get("coin", "").lower()
            if coin in self.config.cryptocurrencies:
                self.config.cryptocurrencies.remove(coin)
                self._last_data = None
                self._last_update = None
                return {"success": True, "cryptocurrencies": self.config.cryptocurrencies}
            return {"success": False, "error": "Coin not found"}

        elif action == "toggle_metric":
            metric = params.get("metric")
            if metric == "market_cap":
                self.config.show_market_cap = not self.config.show_market_cap
                return {"success": True, "show_market_cap": self.config.show_market_cap}
            elif metric == "volume":
                self.config.show_volume = not self.config.show_volume
                return {"success": True, "show_volume": self.config.show_volume}
            elif metric == "change_24h":
                self.config.show_change_24h = not self.config.show_change_24h
                return {"success": True, "show_change_24h": self.config.show_change_24h}
            elif metric == "change_7d":
                self.config.show_change_7d = not self.config.show_change_7d
                return {"success": True, "show_change_7d": self.config.show_change_7d}
            return {"success": False, "error": "Unknown metric"}

        return {"success": False, "error": f"Unknown action: {action}"}