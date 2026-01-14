"""Tests for crypto plugin."""

import pytest
from aioresponses import aioresponses

from src.plugins.crypto import CryptoPlugin, CryptoPluginConfig


class TestCryptoPlugin:
    """Test CryptoPlugin."""

    @pytest.mark.asyncio
    async def test_fetch_data_success(self):
        """Test successful crypto data fetch."""
        mock_response = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 45000.50,
                "market_cap": 850000000000,
                "market_cap_rank": 1,
                "price_change_percentage_24h": 2.5,
                "price_change_percentage_7d_in_currency": 5.8
            },
            {
                "id": "ethereum",
                "symbol": "eth",
                "name": "Ethereum",
                "current_price": 3000.25,
                "market_cap": 360000000000,
                "market_cap_rank": 2,
                "price_change_percentage_24h": -1.2,
                "price_change_percentage_7d_in_currency": 3.4
            }
        ]

        config = CryptoPluginConfig(
            enabled=True,
            cryptocurrencies=["bitcoin", "ethereum"],
            vs_currency="usd"
        )
        plugin = CryptoPlugin(config)

        with aioresponses() as mock:
            mock.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                payload=mock_response
            )

            data = await plugin.fetch_data()

            assert data is not None
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["id"] == "bitcoin"
            assert data[0]["current_price"] == 45000.50

    @pytest.mark.asyncio
    async def test_fetch_data_single_crypto(self):
        """Test fetching single cryptocurrency."""
        mock_response = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 45000.50,
                "market_cap": 850000000000,
                "market_cap_rank": 1,
                "price_change_percentage_24h": 2.5
            }
        ]

        config = CryptoPluginConfig(
            enabled=True,
            cryptocurrencies=["bitcoin"],
            vs_currency="usd"
        )
        plugin = CryptoPlugin(config)

        with aioresponses() as mock:
            mock.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                payload=mock_response
            )

            data = await plugin.fetch_data()

            assert len(data) == 1
            assert data[0]["id"] == "bitcoin"

    @pytest.mark.asyncio
    async def test_fetch_data_different_currency(self):
        """Test fetching with different vs_currency."""
        mock_response = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 38000.00,
                "market_cap": 720000000000,
                "market_cap_rank": 1,
                "price_change_percentage_24h": 2.5
            }
        ]

        config = CryptoPluginConfig(
            enabled=True,
            cryptocurrencies=["bitcoin"],
            vs_currency="eur"
        )
        plugin = CryptoPlugin(config)

        with aioresponses() as mock:
            mock.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                payload=mock_response
            )

            data = await plugin.fetch_data()

            assert data is not None

    def test_get_display_data(self):
        """Test formatting crypto data for display."""
        config = CryptoPluginConfig(
            enabled=True,
            cryptocurrencies=["bitcoin"],
            vs_currency="usd",
            show_change_24h=True
        )
        plugin = CryptoPlugin(config)

        data = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 45000.50,
                "price_change_percentage_24h": 2.5
            }
        ]

        display_data = plugin.get_display_data(data)

        assert "coins" in display_data
        assert len(display_data["coins"]) == 1
        assert display_data["coins"][0]["name"] == "Bitcoin"
        assert display_data["coins"][0]["price"] == 45000.50

    def test_get_display_data_with_24h_change(self):
        """Test display data with 24h price change."""
        config = CryptoPluginConfig(
            enabled=True,
            show_change_24h=True,
            show_change_7d=False
        )
        plugin = CryptoPlugin(config)

        data = [
            {
                "id": "ethereum",
                "symbol": "eth",
                "name": "Ethereum",
                "current_price": 3000.25,
                "price_change_percentage_24h": -1.2
            }
        ]

        display_data = plugin.get_display_data(data)

        assert "coins" in display_data
        coin = display_data["coins"][0]
        assert "change_24h" in coin
        assert coin["change_24h"] == -1.2

    def test_get_display_data_with_7d_change(self):
        """Test display data with 7d price change."""
        config = CryptoPluginConfig(
            enabled=True,
            show_change_24h=False,
            show_change_7d=True
        )
        plugin = CryptoPlugin(config)

        data = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 45000.50,
                "price_change_percentage_7d_in_currency": 5.8
            }
        ]

        display_data = plugin.get_display_data(data)

        assert "coins" in display_data
        coin = display_data["coins"][0]
        assert "change_7d" in coin
        assert coin["change_7d"] == 5.8

    def test_get_display_data_multiple_coins(self):
        """Test display data with multiple cryptocurrencies."""
        config = CryptoPluginConfig(
            enabled=True,
            cryptocurrencies=["bitcoin", "ethereum", "cardano"]
        )
        plugin = CryptoPlugin(config)

        data = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 45000.50,
                "price_change_percentage_24h": 2.5
            },
            {
                "id": "ethereum",
                "symbol": "eth",
                "name": "Ethereum",
                "current_price": 3000.25,
                "price_change_percentage_24h": -1.2
            },
            {
                "id": "cardano",
                "symbol": "ada",
                "name": "Cardano",
                "current_price": 0.58,
                "price_change_percentage_24h": 3.7
            }
        ]

        display_data = plugin.get_display_data(data)

        assert "coins" in display_data
        assert len(display_data["coins"]) == 3

    def test_get_display_data_error_handling(self):
        """Test display data error handling."""
        config = CryptoPluginConfig(enabled=True)
        plugin = CryptoPlugin(config)

        # Empty data
        data = []
        display_data = plugin.get_display_data(data)

        assert "error" in display_data or "coins" in display_data

    def test_get_display_data_vs_currency(self):
        """Test display data includes vs_currency."""
        config = CryptoPluginConfig(
            enabled=True,
            vs_currency="eur"
        )
        plugin = CryptoPlugin(config)

        data = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 38000.00
            }
        ]

        display_data = plugin.get_display_data(data)

        assert "vs_currency" in display_data
        assert display_data["vs_currency"] == "eur"

    @pytest.mark.asyncio
    async def test_plugin_update_integration(self):
        """Test full plugin update cycle."""
        mock_response = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 45000.50,
                "price_change_percentage_24h": 2.5
            }
        ]

        config = CryptoPluginConfig(
            enabled=True,
            cryptocurrencies=["bitcoin"]
        )
        plugin = CryptoPlugin(config)

        with aioresponses() as mock:
            mock.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                payload=mock_response
            )

            result = await plugin.update()

            assert result is not None
            assert result.plugin_name == "crypto"
            assert result.error is None
            assert "coins" in result.data


class TestCryptoPluginConfig:
    """Test CryptoPluginConfig."""

    def test_default_config(self):
        """Test default crypto configuration."""
        config = CryptoPluginConfig()

        assert config.enabled is True
        assert "bitcoin" in config.cryptocurrencies
        assert "ethereum" in config.cryptocurrencies
        assert config.vs_currency == "usd"
        assert config.show_change_24h is True
        assert config.show_change_7d is False

    def test_custom_config(self):
        """Test custom crypto configuration."""
        config = CryptoPluginConfig(
            enabled=False,
            api_key="custom_key",
            cryptocurrencies=["cardano", "polkadot", "solana"],
            vs_currency="eur",
            show_change_24h=False,
            show_change_7d=True
        )

        assert config.enabled is False
        assert config.api_key == "custom_key"
        assert len(config.cryptocurrencies) == 3
        assert "cardano" in config.cryptocurrencies
        assert config.vs_currency == "eur"
        assert config.show_change_24h is False
        assert config.show_change_7d is True

    def test_multiple_cryptocurrencies(self):
        """Test configuration with many cryptocurrencies."""
        cryptos = ["bitcoin", "ethereum", "cardano", "polkadot", "solana", "avalanche"]

        config = CryptoPluginConfig(
            cryptocurrencies=cryptos
        )

        assert len(config.cryptocurrencies) == len(cryptos)
        for crypto in cryptos:
            assert crypto in config.cryptocurrencies

    def test_vs_currency_options(self):
        """Test various vs_currency configurations."""
        currencies = ["usd", "eur", "gbp", "jpy", "btc"]

        for currency in currencies:
            config = CryptoPluginConfig(vs_currency=currency)
            assert config.vs_currency == currency
