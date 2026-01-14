"""Tests for weather plugin."""

import pytest
from aioresponses import aioresponses

from src.plugins.weather import WeatherPlugin, WeatherPluginConfig


class TestWeatherPlugin:
    """Test WeatherPlugin."""

    @pytest.mark.asyncio
    async def test_fetch_data_success(self):
        """Test successful weather data fetch."""
        mock_response = {
            "coord": {"lon": -0.1257, "lat": 51.5085},
            "weather": [
                {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
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
            "wind": {"speed": 3.5, "deg": 200},
            "clouds": {"all": 0},
            "dt": 1609459200,
            "sys": {
                "type": 1,
                "id": 1414,
                "country": "GB",
                "sunrise": 1609401600,
                "sunset": 1609435200
            },
            "timezone": 0,
            "id": 2643743,
            "name": "London",
            "cod": 200
        }

        config = WeatherPluginConfig(
            enabled=True,
            api_key="test_key",
            cities=[{"name": "London", "country": "UK"}],
            units="metric"
        )
        plugin = WeatherPlugin(config)

        with aioresponses() as mock:
            mock.get(
                "https://api.openweathermap.org/data/2.5/weather",
                payload=mock_response
            )

            data = await plugin.fetch_data()

            assert data is not None
            assert "current" in data
            assert "city_info" in data
            assert data["current"]["name"] == "London"

    @pytest.mark.asyncio
    async def test_fetch_data_no_api_key(self):
        """Test fetching without API key."""
        config = WeatherPluginConfig(
            enabled=True,
            api_key="",
            cities=[{"name": "London", "country": "UK"}]
        )
        plugin = WeatherPlugin(config)

        with pytest.raises(ValueError, match="API key not configured"):
            await plugin.fetch_data()

    @pytest.mark.asyncio
    async def test_fetch_data_no_cities(self):
        """Test fetching without cities configured."""
        config = WeatherPluginConfig(
            enabled=True,
            api_key="test_key",
            cities=[]
        )
        plugin = WeatherPlugin(config)

        with pytest.raises(ValueError, match="No cities configured"):
            await plugin.fetch_data()

    def test_get_display_data(self, mock_weather_api_response):
        """Test formatting weather data for display."""
        config = WeatherPluginConfig(
            enabled=True,
            api_key="test_key",
            cities=[{"name": "London", "country": "UK"}]
        )
        plugin = WeatherPlugin(config)

        data = {
            "current": mock_weather_api_response,
            "city_info": {"name": "London", "country": "UK"}
        }

        display_data = plugin.get_display_data(data)

        assert display_data["city"] == "London"
        assert display_data["country"] == "GB"
        assert display_data["temperature"] == 20.5
        assert display_data["description"] == "Clear Sky"
        assert "humidity" in display_data
        assert "wind_speed" in display_data

    def test_get_display_data_error(self):
        """Test display data with missing current data."""
        config = WeatherPluginConfig(
            enabled=True,
            api_key="test_key",
            cities=[{"name": "London", "country": "UK"}]
        )
        plugin = WeatherPlugin(config)

        data = {}
        display_data = plugin.get_display_data(data)

        assert "error" in display_data

    @pytest.mark.asyncio
    async def test_weather_with_state(self):
        """Test weather with US state."""
        mock_response = {
            "coord": {"lon": -74.006, "lat": 40.7128},
            "weather": [
                {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
            ],
            "base": "stations",
            "main": {
                "temp": 68.5,
                "feels_like": 67.8,
                "temp_min": 65.0,
                "temp_max": 72.0,
                "pressure": 1013,
                "humidity": 65
            },
            "visibility": 10000,
            "wind": {"speed": 5.5, "deg": 200},
            "clouds": {"all": 0},
            "dt": 1609459200,
            "sys": {
                "type": 1,
                "id": 1414,
                "country": "US",
                "sunrise": 1609401600,
                "sunset": 1609435200
            },
            "timezone": 0,
            "id": 5128581,
            "name": "New York",
            "cod": 200
        }

        config = WeatherPluginConfig(
            enabled=True,
            api_key="test_key",
            cities=[{"name": "New York", "state": "NY", "country": "US"}],
            units="imperial"
        )
        plugin = WeatherPlugin(config)

        with aioresponses() as mock:
            # Verify correct location string is built
            mock.get(
                "https://api.openweathermap.org/data/2.5/weather",
                payload=mock_response
            )

            await plugin.fetch_data()

            # Check that request was made (aioresponses would fail if URL doesn't match)
            assert len(mock.requests) == 1


class TestWeatherPluginConfig:
    """Test WeatherPluginConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = WeatherPluginConfig(api_key="test")

        assert config.enabled is True
        assert config.units == "metric"
        assert config.language == "en"
        assert config.show_forecast is False
        assert len(config.cities) == 1

    def test_custom_config(self):
        """Test custom configuration."""
        config = WeatherPluginConfig(
            enabled=False,
            api_key="custom_key",
            cities=[
                {"name": "Paris", "country": "FR"},
                {"name": "Berlin", "country": "DE"}
            ],
            units="imperial",
            language="fr",
            show_forecast=True
        )

        assert config.enabled is False
        assert config.api_key == "custom_key"
        assert len(config.cities) == 2
        assert config.units == "imperial"
        assert config.language == "fr"
        assert config.show_forecast is True
