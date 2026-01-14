"""Tests for configuration management."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import yaml

from src.config.manager import ConfigManager
from src.config.schemas import (
    AppConfig,
    DisplayConfig,
    DisplayMode,
    PluginConfigs,
    WeatherConfig,
    CurrencyConfig,
    CryptoConfig,
    ClockConfig
)


class TestConfigManager:
    """Test ConfigManager."""

    def test_singleton_pattern(self):
        """Test that ConfigManager is a singleton."""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        assert manager1 is manager2

    def test_default_config_path(self):
        """Test default configuration path."""
        manager = ConfigManager()
        assert manager.config_path.name == "config.yaml"
        assert "config" in str(manager.config_path)

    def test_custom_config_path(self):
        """Test custom configuration path."""
        custom_path = Path("/tmp/custom_config.yaml")
        manager = ConfigManager(config_path=custom_path)
        assert manager.config_path == custom_path

    def test_load_config_creates_default(self, tmp_path):
        """Test loading creates default config if not exists."""
        config_file = tmp_path / "config.yaml"
        manager = ConfigManager(config_path=config_file)

        # Load config - should create default
        config = manager.load_config()

        assert config is not None
        assert isinstance(config, AppConfig)
        assert config_file.exists()

    def test_load_config_from_file(self, tmp_path):
        """Test loading config from existing file."""
        config_file = tmp_path / "config.yaml"

        # Create test config
        test_config = {
            "display": {
                "mode": "epaper"
            },
            "plugins": {
                "weather": {
                    "enabled": True,
                    "api_key": "test_key",
                    "cities": [{"name": "London", "country": "UK"}]
                },
                "currency": {
                    "enabled": False,
                    "api_key": "dummy"
                },
                "crypto": {"enabled": False},
                "clock": {"enabled": True}
            }
        }

        config_file.write_text(yaml.dump(test_config))

        manager = ConfigManager(config_path=config_file)
        config = manager.load_config()

        assert config.display.mode == DisplayMode.EPAPER
        assert config.plugins.weather.enabled is True
        assert config.plugins.weather.api_key == "test_key"
        assert config.plugins.currency.enabled is False

    def test_get_config_cached(self):
        """Test getting cached config."""
        manager = ConfigManager()

        # Load config first time
        config1 = manager.get_config()

        # Get again - should be cached
        config2 = manager.get_config()

        assert config1 is config2

    def test_reload_config(self, tmp_path):
        """Test reloading config from file."""
        config_file = tmp_path / "config.yaml"

        # Create initial config
        initial_config = {
            "display": {"mode": "epaper"},
            "plugins": {"weather": {"enabled": True, "api_key": "test"}}
        }
        config_file.write_text(yaml.dump(initial_config))

        manager = ConfigManager(config_path=config_file)
        config1 = manager.get_config()
        assert config1.plugins.weather.enabled is True

        # Modify file
        updated_config = {
            "display": {"mode": "terminal"},
            "plugins": {"weather": {"enabled": False, "api_key": "test"}}
        }
        config_file.write_text(yaml.dump(updated_config))

        # Reload
        config2 = manager.reload_config()
        assert config2.display.mode == DisplayMode.TERMINAL
        assert config2.plugins.weather.enabled is False

    def test_validate_config_success(self):
        """Test successful config validation."""
        manager = ConfigManager()
        config = manager.get_config()

        # Should not raise
        is_valid = manager.validate_config(config)
        assert is_valid is True

    def test_get_plugin_config_weather(self):
        """Test getting weather plugin config."""
        manager = ConfigManager()
        config = manager.get_config()

        weather_config = manager.get_plugin_config("weather")

        assert isinstance(weather_config, WeatherConfig)
        assert hasattr(weather_config, "api_key")
        assert hasattr(weather_config, "cities")

    def test_get_plugin_config_currency(self):
        """Test getting currency plugin config."""
        manager = ConfigManager()
        config = manager.get_config()

        currency_config = manager.get_plugin_config("currency")

        assert isinstance(currency_config, CurrencyConfig)
        assert hasattr(currency_config, "api_key")

    def test_get_plugin_config_crypto(self):
        """Test getting crypto plugin config."""
        manager = ConfigManager()
        config = manager.get_config()

        crypto_config = manager.get_plugin_config("crypto")

        assert isinstance(crypto_config, CryptoConfig)

    def test_get_plugin_config_clock(self):
        """Test getting clock plugin config."""
        manager = ConfigManager()
        config = manager.get_config()

        clock_config = manager.get_plugin_config("clock")

        assert isinstance(clock_config, ClockConfig)
        assert hasattr(clock_config, "timezone")

    def test_get_plugin_config_unknown(self):
        """Test getting unknown plugin config."""
        manager = ConfigManager()

        with pytest.raises(ValueError, match="Unknown plugin"):
            manager.get_plugin_config("unknown_plugin")


class TestAppConfig:
    """Test AppConfig schema."""

    def test_default_app_config(self):
        """Test default AppConfig creation."""
        config = AppConfig()

        assert isinstance(config.display, DisplayConfig)
        assert isinstance(config.plugins, PluginConfigs)

    def test_app_config_with_values(self):
        """Test AppConfig with custom values."""
        config = AppConfig(
            display=DisplayConfig(mode=DisplayMode.EPAPER)
        )

        assert config.display.mode == DisplayMode.EPAPER


class TestDisplayConfig:
    """Test DisplayConfig schema."""

    def test_default_display_config(self):
        """Test default DisplayConfig."""
        config = DisplayConfig()

        # Test basic display config exists
        assert hasattr(config, 'mode')

    def test_display_mode_validation(self):
        """Test display mode validation."""
        # Valid modes
        config1 = DisplayConfig(mode=DisplayMode.EPAPER)
        assert config1.mode == DisplayMode.EPAPER

        config2 = DisplayConfig(mode=DisplayMode.TERMINAL)
        assert config2.mode == DisplayMode.TERMINAL

        config3 = DisplayConfig(mode=DisplayMode.ALL)
        assert config3.mode == DisplayMode.ALL


class TestPluginsConfig:
    """Test PluginsConfig schema."""

    def test_default_plugins_config(self):
        """Test default PluginsConfig."""
        config = PluginConfigs()

        assert isinstance(config.weather, WeatherConfig)
        assert isinstance(config.currency, CurrencyConfig)
        assert isinstance(config.crypto, CryptoConfig)
        assert isinstance(config.clock, ClockConfig)

    def test_plugins_enabled_by_default(self):
        """Test that plugins are enabled by default."""
        config = PluginConfigs()

        assert config.weather.enabled is True
        assert config.currency.enabled is True
        assert config.crypto.enabled is True
        assert config.clock.enabled is True


class TestWeatherConfig:
    """Test WeatherConfig schema."""

    def test_default_weather_config(self):
        """Test default WeatherConfig."""
        config = WeatherConfig(api_key="test")

        assert config.enabled is True
        assert config.units == "metric"
        assert config.language == "en"
        assert config.show_forecast is False
        assert len(config.cities) == 1

    def test_weather_config_validation(self):
        """Test weather config validation."""
        config = WeatherConfig(
            api_key="test_key",
            cities=[
                {"name": "London", "country": "UK"},
                {"name": "Paris", "country": "FR"}
            ],
            units="imperial",
            show_forecast=True
        )

        assert config.api_key == "test_key"
        assert len(config.cities) == 2
        assert config.units == "imperial"
        assert config.show_forecast is True


class TestCurrencyConfig:
    """Test CurrencyConfig schema."""

    def test_default_currency_config(self):
        """Test default CurrencyConfig."""
        config = CurrencyConfig(api_key="test")

        assert config.enabled is True
        assert config.base_currency == "USD"
        assert "EUR" in config.target_currencies
        assert config.decimal_places == 4

    def test_currency_config_validation(self):
        """Test currency config validation."""
        config = CurrencyConfig(
            api_key="test_key",
            base_currency="EUR",
            target_currencies=["USD", "GBP", "JPY"],
            decimal_places=2
        )

        assert config.api_key == "test_key"
        assert config.base_currency == "EUR"
        assert len(config.target_currencies) == 3
        assert config.decimal_places == 2


class TestCryptoConfig:
    """Test CryptoConfig schema."""

    def test_default_crypto_config(self):
        """Test default CryptoConfig."""
        config = CryptoConfig()

        assert config.enabled is True
        assert "bitcoin" in config.cryptocurrencies
        assert config.show_change_24h is True

    def test_crypto_config_validation(self):
        """Test crypto config validation."""
        config = CryptoConfig(
            api_key="test_key",
            cryptocurrencies=["ethereum", "cardano"],
            show_change_24h=False,
            show_change_7d=True
        )

        assert config.api_key == "test_key"
        assert len(config.cryptocurrencies) == 2
        assert config.show_change_24h is False
        assert config.show_change_7d is True


class TestClockConfig:
    """Test ClockConfig schema."""

    def test_default_clock_config(self):
        """Test default ClockConfig."""
        config = ClockConfig()

        assert config.enabled is True
        assert config.timezone == "UTC"
        assert config.format_24h is True
        assert config.show_seconds is True
        assert config.show_date is True

    def test_clock_config_validation(self):
        """Test clock config validation."""
        config = ClockConfig(
            timezone="America/New_York",
            format_24h=False,
            show_seconds=False,
            show_date=False,
            show_day_name=True,
            show_week_number=True
        )

        assert config.timezone == "America/New_York"
        assert config.format_24h is False
        assert config.show_seconds is False
        assert config.show_date is False
        assert config.show_day_name is True
        assert config.show_week_number is True
