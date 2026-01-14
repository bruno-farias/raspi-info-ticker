"""Tests for currency plugin."""

import pytest
from aioresponses import aioresponses

from src.plugins.currency import CurrencyPlugin, CurrencyPluginConfig


class TestCurrencyPlugin:
    """Test CurrencyPlugin."""

    @pytest.mark.asyncio
    async def test_fetch_data_success(self):
        """Test successful currency data fetch."""
        mock_response = {
            "data": {
                "EUR": 0.85,
                "GBP": 0.73,
                "JPY": 110.25
            }
        }

        config = CurrencyPluginConfig(
            enabled=True,
            api_key="test_key",
            base_currency="USD",
            target_currencies=["EUR", "GBP", "JPY"]
        )
        plugin = CurrencyPlugin(config)

        with aioresponses() as mock:
            mock.get(
                "https://api.freecurrencyapi.com/v1/latest",
                payload=mock_response
            )

            data = await plugin.fetch_data()

            assert data is not None
            assert "data" in data
            assert "EUR" in data["data"]
            assert data["data"]["EUR"] == 0.85

    @pytest.mark.asyncio
    async def test_fetch_data_no_api_key(self):
        """Test fetching without API key."""
        config = CurrencyPluginConfig(
            enabled=True,
            api_key="",
            base_currency="USD"
        )
        plugin = CurrencyPlugin(config)

        with pytest.raises(ValueError, match="API key not configured"):
            await plugin.fetch_data()

    @pytest.mark.asyncio
    async def test_fetch_data_custom_base(self):
        """Test fetching with custom base currency."""
        mock_response = {
            "data": {
                "USD": 1.18,
                "GBP": 0.86,
                "JPY": 130.50
            }
        }

        config = CurrencyPluginConfig(
            enabled=True,
            api_key="test_key",
            base_currency="EUR",
            target_currencies=["USD", "GBP", "JPY"]
        )
        plugin = CurrencyPlugin(config)

        with aioresponses() as mock:
            mock.get(
                "https://api.freecurrencyapi.com/v1/latest",
                payload=mock_response
            )

            data = await plugin.fetch_data()

            assert data is not None
            assert "data" in data

    def test_get_display_data(self):
        """Test formatting currency data for display."""
        config = CurrencyPluginConfig(
            enabled=True,
            api_key="test_key",
            base_currency="USD",
            target_currencies=["EUR", "GBP"],
            decimal_places=4
        )
        plugin = CurrencyPlugin(config)

        data = {
            "data": {
                "EUR": 0.8523,
                "GBP": 0.7345
            }
        }

        display_data = plugin.get_display_data(data)

        assert "base_currency" in display_data
        assert display_data["base_currency"] == "USD"
        assert "rates" in display_data
        assert "EUR" in display_data["rates"]
        assert "GBP" in display_data["rates"]

    def test_get_display_data_with_rounding(self):
        """Test display data with decimal rounding."""
        config = CurrencyPluginConfig(
            enabled=True,
            api_key="test_key",
            base_currency="USD",
            target_currencies=["EUR"],
            decimal_places=2
        )
        plugin = CurrencyPlugin(config)

        data = {
            "data": {
                "EUR": 0.852345
            }
        }

        display_data = plugin.get_display_data(data)

        assert "rates" in display_data
        # Rate should be rounded to 2 decimal places
        assert display_data["rates"]["EUR"] == 0.85

    def test_get_display_data_error_handling(self):
        """Test display data error handling."""
        config = CurrencyPluginConfig(
            enabled=True,
            api_key="test_key"
        )
        plugin = CurrencyPlugin(config)

        # Empty data
        data = {}
        display_data = plugin.get_display_data(data)

        assert "error" in display_data

    def test_get_display_data_missing_rates(self):
        """Test display data with missing rates."""
        config = CurrencyPluginConfig(
            enabled=True,
            api_key="test_key",
            target_currencies=["EUR", "GBP", "JPY"]
        )
        plugin = CurrencyPlugin(config)

        # Only EUR available
        data = {
            "data": {
                "EUR": 0.85
            }
        }

        display_data = plugin.get_display_data(data)

        assert "rates" in display_data
        assert "EUR" in display_data["rates"]

    @pytest.mark.asyncio
    async def test_plugin_update_integration(self):
        """Test full plugin update cycle."""
        mock_response = {
            "data": {
                "EUR": 0.85,
                "GBP": 0.73
            }
        }

        config = CurrencyPluginConfig(
            enabled=True,
            api_key="test_key",
            target_currencies=["EUR", "GBP"]
        )
        plugin = CurrencyPlugin(config)

        with aioresponses() as mock:
            mock.get(
                "https://api.freecurrencyapi.com/v1/latest",
                payload=mock_response
            )

            result = await plugin.update()

            assert result is not None
            assert result.plugin_name == "currency"
            assert result.error is None
            assert "rates" in result.data


class TestCurrencyPluginConfig:
    """Test CurrencyPluginConfig."""

    def test_default_config(self):
        """Test default currency configuration."""
        config = CurrencyPluginConfig()

        assert config.enabled is True
        assert config.base_currency == "USD"
        assert "EUR" in config.target_currencies
        assert "GBP" in config.target_currencies
        assert "JPY" in config.target_currencies
        assert config.decimal_places == 4
        assert config.show_change is True

    def test_custom_config(self):
        """Test custom currency configuration."""
        config = CurrencyPluginConfig(
            enabled=False,
            api_key="custom_key",
            base_currency="EUR",
            target_currencies=["USD", "CHF", "CAD"],
            decimal_places=2,
            show_change=False
        )

        assert config.enabled is False
        assert config.api_key == "custom_key"
        assert config.base_currency == "EUR"
        assert len(config.target_currencies) == 3
        assert "USD" in config.target_currencies
        assert config.decimal_places == 2
        assert config.show_change is False

    def test_multiple_target_currencies(self):
        """Test configuration with many target currencies."""
        currencies = ["EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "INR"]

        config = CurrencyPluginConfig(
            api_key="test_key",
            target_currencies=currencies
        )

        assert len(config.target_currencies) == len(currencies)
        for currency in currencies:
            assert currency in config.target_currencies

    def test_decimal_places_validation(self):
        """Test decimal places configuration."""
        for decimal_places in [0, 2, 4, 6, 8]:
            config = CurrencyPluginConfig(decimal_places=decimal_places)
            assert config.decimal_places == decimal_places
