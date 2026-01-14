"""Shared fixtures for tests."""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, AsyncMock

from src.plugins import plugin_registry, PluginRegistry
from src.config import config_manager


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """Mock application configuration."""
    return {
        "app_name": "Test Ticker",
        "version": "2.0.0",
        "debug": True,
        "log_level": "DEBUG",
        "display": {
            "mode": "epaper",
            "refresh_interval": 15,
            "cycle_interval": 10,
            "epaper_model": "epd2in13_V4",
        },
        "plugins": {
            "weather": {
                "enabled": True,
                "api_key": "test_weather_key",
                "cities": [
                    {"name": "London", "country": "UK"}
                ],
                "units": "metric",
                "update_interval": 300,
                "cache_ttl": 600,
                "priority": 1,
            },
            "currency": {
                "enabled": True,
                "api_key": "test_currency_key",
                "base_currency": "USD",
                "target_currencies": ["EUR", "GBP"],
                "decimal_places": 4,
                "update_interval": 60,
                "cache_ttl": 300,
                "priority": 2,
            },
            "crypto": {
                "enabled": True,
                "api_key": None,
                "provider": "coingecko",
                "cryptocurrencies": ["bitcoin", "ethereum"],
                "vs_currencies": ["usd"],
                "show_change_24h": True,
                "show_change_7d": False,
                "update_interval": 30,
                "cache_ttl": 60,
                "priority": 3,
            },
            "clock": {
                "enabled": True,
                "timezone": None,
                "format_24h": True,
                "show_date": True,
                "show_seconds": True,
                "show_day_name": False,
                "show_week_number": False,
                "update_interval": 1,
                "cache_ttl": 0,
                "priority": 0,
            },
        },
    }


@pytest.fixture
def fresh_plugin_registry():
    """Provide a fresh plugin registry for each test."""
    # Create a new registry
    registry = PluginRegistry()

    # Discover plugins
    from pathlib import Path
    plugin_dir = Path(__file__).parent.parent / "src" / "plugins"
    registry.discover_plugins(plugin_dir)

    yield registry

    # Cleanup
    registry.plugins.clear()
    registry.plugin_classes.clear()


@pytest.fixture
def mock_weather_api_response():
    """Mock weather API response."""
    return {
        "coord": {"lon": -0.1257, "lat": 51.5085},
        "weather": [
            {
                "id": 800,
                "main": "Clear",
                "description": "clear sky",
                "icon": "01d"
            }
        ],
        "base": "stations",
        "main": {
            "temp": 20.5,
            "feels_like": 19.8,
            "temp_min": 18.0,
            "temp_max": 22.0,
            "pressure": 1013,
            "humidity": 65
        },
        "visibility": 10000,
        "wind": {
            "speed": 4.5,
            "deg": 180
        },
        "clouds": {
            "all": 10
        },
        "dt": 1634567890,
        "sys": {
            "type": 2,
            "id": 2019646,
            "country": "GB",
            "sunrise": 1634537890,
            "sunset": 1634577890
        },
        "timezone": 3600,
        "id": 2643743,
        "name": "London",
        "cod": 200
    }


@pytest.fixture
def mock_currency_api_response():
    """Mock currency API response."""
    return {
        "data": {
            "EUR": 0.85,
            "GBP": 0.73,
            "JPY": 110.5
        }
    }


@pytest.fixture
def mock_crypto_api_response():
    """Mock crypto API response."""
    return {
        "bitcoin": {
            "usd": 45000.50,
            "usd_24h_change": 2.5,
            "usd_7d_change": -1.2
        },
        "ethereum": {
            "usd": 3200.75,
            "usd_24h_change": 3.1,
            "usd_7d_change": 5.4
        }
    }


@pytest.fixture
def mock_epaper_display():
    """Mock e-paper display."""
    mock = MagicMock()
    mock.width = 122
    mock.height = 250
    mock.init = MagicMock()
    mock.Clear = MagicMock()
    mock.display = MagicMock()
    mock.displayPartBaseImage = MagicMock()
    mock.displayPartial = MagicMock()
    mock.sleep = MagicMock()
    mock.getbuffer = MagicMock(return_value=b'test_buffer')
    return mock


@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Clean up singleton instances between tests."""
    yield
    # Reset plugin registry
    if hasattr(plugin_registry, 'plugins'):
        plugin_registry.plugins.clear()
    if hasattr(plugin_registry, 'plugin_classes'):
        plugin_registry.plugin_classes.clear()
    if hasattr(plugin_registry, '_instance_counter'):
        plugin_registry._instance_counter.clear()
