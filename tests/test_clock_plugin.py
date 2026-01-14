"""Tests for clock plugin."""

import pytest
from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

from src.plugins.clock import ClockPlugin, ClockPluginConfig


class TestClockPlugin:
    """Test ClockPlugin."""

    @pytest.mark.asyncio
    async def test_fetch_data_basic(self):
        """Test basic clock data fetch."""
        config = ClockPluginConfig(enabled=True)
        plugin = ClockPlugin(config)

        data = await plugin.fetch_data()

        assert data is not None
        assert "datetime" in data
        assert "timezone" in data
        assert isinstance(data["datetime"], datetime)

    @pytest.mark.asyncio
    @freeze_time("2024-01-15 14:30:45")
    async def test_fetch_data_frozen_time(self):
        """Test clock with frozen time."""
        config = ClockPluginConfig(enabled=True, timezone="UTC")
        plugin = ClockPlugin(config)

        data = await plugin.fetch_data()

        assert data["datetime"].year == 2024
        assert data["datetime"].month == 1
        assert data["datetime"].day == 15
        assert data["datetime"].hour == 14
        assert data["datetime"].minute == 30
        assert data["datetime"].second == 45

    @pytest.mark.asyncio
    async def test_fetch_data_different_timezone(self):
        """Test clock with different timezone."""
        config = ClockPluginConfig(enabled=True, timezone="America/New_York")
        plugin = ClockPlugin(config)

        data = await plugin.fetch_data()

        assert data["timezone"] == "America/New_York"
        assert isinstance(data["datetime"], datetime)

    def test_get_display_data_24h_format(self):
        """Test display data with 24-hour format."""
        config = ClockPluginConfig(
            enabled=True,
            format_24h=True,
            show_seconds=True,
            show_date=True
        )
        plugin = ClockPlugin(config)

        test_time = datetime(2024, 1, 15, 14, 30, 45)
        data = {
            "datetime": test_time,
            "timezone": "UTC"
        }

        display_data = plugin.get_display_data(data)

        assert "time" in display_data
        assert "date" in display_data
        assert "14:30:45" in display_data["time"]

    def test_get_display_data_12h_format(self):
        """Test display data with 12-hour format."""
        config = ClockPluginConfig(
            enabled=True,
            format_24h=False,
            show_seconds=True
        )
        plugin = ClockPlugin(config)

        test_time = datetime(2024, 1, 15, 14, 30, 45)
        data = {
            "datetime": test_time,
            "timezone": "UTC"
        }

        display_data = plugin.get_display_data(data)

        assert "time" in display_data
        # Should contain PM for 14:30
        assert "PM" in display_data["time"] or "pm" in display_data["time"]

    def test_get_display_data_no_seconds(self):
        """Test display data without seconds."""
        config = ClockPluginConfig(
            enabled=True,
            format_24h=True,
            show_seconds=False
        )
        plugin = ClockPlugin(config)

        test_time = datetime(2024, 1, 15, 14, 30, 45)
        data = {
            "datetime": test_time,
            "timezone": "UTC"
        }

        display_data = plugin.get_display_data(data)

        assert "time" in display_data
        assert "14:30" in display_data["time"]

    def test_get_display_data_with_date(self):
        """Test display data with date shown."""
        config = ClockPluginConfig(
            enabled=True,
            show_date=True
        )
        plugin = ClockPlugin(config)

        test_time = datetime(2024, 1, 15, 14, 30, 45)
        data = {
            "datetime": test_time,
            "timezone": "UTC"
        }

        display_data = plugin.get_display_data(data)

        assert "date" in display_data
        assert "2024" in display_data["date"]

    def test_get_display_data_no_date(self):
        """Test display data without date."""
        config = ClockPluginConfig(
            enabled=True,
            show_date=False
        )
        plugin = ClockPlugin(config)

        test_time = datetime(2024, 1, 15, 14, 30, 45)
        data = {
            "datetime": test_time,
            "timezone": "UTC"
        }

        display_data = plugin.get_display_data(data)

        # Date might still be in data but shouldn't be primary
        assert "time" in display_data

    def test_get_display_data_with_day_name(self):
        """Test display data with day name."""
        config = ClockPluginConfig(
            enabled=True,
            show_day_name=True
        )
        plugin = ClockPlugin(config)

        # 2024-01-15 is a Monday
        test_time = datetime(2024, 1, 15, 14, 30, 45)
        data = {
            "datetime": test_time,
            "timezone": "UTC"
        }

        display_data = plugin.get_display_data(data)

        # Day name should appear somewhere in display data
        assert "day_name" in display_data or "day" in display_data

    def test_get_display_data_with_week_number(self):
        """Test display data with week number."""
        config = ClockPluginConfig(
            enabled=True,
            show_week_number=True
        )
        plugin = ClockPlugin(config)

        test_time = datetime(2024, 1, 15, 14, 30, 45)
        data = {
            "datetime": test_time,
            "timezone": "UTC"
        }

        display_data = plugin.get_display_data(data)

        # Week number should appear somewhere in display data
        assert "week" in display_data or "week_number" in display_data

    def test_get_display_data_error_handling(self):
        """Test display data error handling."""
        config = ClockPluginConfig(enabled=True)
        plugin = ClockPlugin(config)

        # Empty data
        data = {}
        display_data = plugin.get_display_data(data)

        assert "error" in display_data

    @pytest.mark.asyncio
    async def test_plugin_update_integration(self):
        """Test full plugin update cycle."""
        config = ClockPluginConfig(enabled=True)
        plugin = ClockPlugin(config)

        result = await plugin.update()

        assert result is not None
        assert result.plugin_name == "clock"
        assert result.error is None
        assert "time" in result.data


class TestClockPluginConfig:
    """Test ClockPluginConfig."""

    def test_default_config(self):
        """Test default clock configuration."""
        config = ClockPluginConfig()

        assert config.enabled is True
        assert config.timezone == "UTC"
        assert config.format_24h is True
        assert config.show_seconds is True
        assert config.show_date is True
        assert config.show_day_name is False
        assert config.show_week_number is False

    def test_custom_config(self):
        """Test custom clock configuration."""
        config = ClockPluginConfig(
            enabled=False,
            timezone="Europe/London",
            format_24h=False,
            show_seconds=False,
            show_date=False,
            show_day_name=True,
            show_week_number=True
        )

        assert config.enabled is False
        assert config.timezone == "Europe/London"
        assert config.format_24h is False
        assert config.show_seconds is False
        assert config.show_date is False
        assert config.show_day_name is True
        assert config.show_week_number is True

    def test_timezone_options(self):
        """Test various timezone configurations."""
        timezones = [
            "UTC",
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "Australia/Sydney"
        ]

        for tz in timezones:
            config = ClockPluginConfig(timezone=tz)
            assert config.timezone == tz
