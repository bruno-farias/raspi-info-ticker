"""Display runner for headless e-paper mode."""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ..config import config_manager
from ..plugins import plugin_registry
from ..services.display_service import DisplayService


class DisplayRunner:
    """Runner for e-paper display mode."""

    def __init__(self):
        """Initialize display runner."""
        self.logger = logging.getLogger("display_runner")
        self.config = None
        self.display_service = None
        self.running = False
        self.current_plugin_index = 0

    async def initialize(self):
        """Initialize the display runner."""
        # Load configuration
        self.config = config_manager.load(create_if_missing=True)

        # Initialize display service (from original code)
        self.display_service = DisplayService(simulation_mode=False)
        self.display_service.initialize_display()

        # Discover and initialize plugins
        plugin_registry.discover_plugins()

        # Create plugin instances
        if self.config.plugins.weather.enabled:
            plugin_registry.create_plugin("weather", self.config.plugins.weather)

        if self.config.plugins.currency.enabled:
            plugin_registry.create_plugin("currency", self.config.plugins.currency)

        if self.config.plugins.crypto.enabled:
            plugin_registry.create_plugin("crypto", self.config.plugins.crypto)

        if self.config.plugins.clock.enabled:
            plugin_registry.create_plugin("clock", self.config.plugins.clock)

        # Initialize all plugins
        await plugin_registry.initialize_all()

        self.logger.info("Display runner initialized")

    async def run(self):
        """Run the display loop."""
        await self.initialize()
        self.running = True

        try:
            while self.running:
                await self.update_display()
                await asyncio.sleep(self.config.display.refresh_interval)
        except KeyboardInterrupt:
            self.logger.info("Display runner interrupted")
        except Exception as e:
            self.logger.error(f"Display runner error: {e}")
        finally:
            await self.cleanup()

    async def update_display(self):
        """Update the e-paper display with current plugin data."""
        enabled_plugins = plugin_registry.get_enabled_plugins()

        if not enabled_plugins:
            self.logger.warning("No enabled plugins")
            return

        # Get current plugin
        plugin = enabled_plugins[self.current_plugin_index]

        try:
            # Get plugin data
            plugin_data = await plugin.update()

            # Convert to display format compatible with original display service
            screen_data = self._convert_to_screen_data(plugin, plugin_data)

            # Display on e-paper
            self.display_service.display_screen_with_smart_refresh(screen_data)

            self.logger.info(f"Displayed {plugin.name} on e-paper")

        except Exception as e:
            self.logger.error(f"Error displaying {plugin.name}: {e}")

        # Move to next plugin
        self.current_plugin_index = (self.current_plugin_index + 1) % len(enabled_plugins)

    def _convert_to_screen_data(self, plugin, plugin_data) -> Dict[str, Any]:
        """Convert plugin data to format expected by display service."""
        # Format compatible with original DisplayService
        screen_data = {
            'title': plugin_data.title,
            'rates_data': {},
            'display_function': lambda x: self._format_plugin_display(plugin, x),
            'screen_number': self.current_plugin_index + 1,
            'total_screens': len(plugin_registry.get_enabled_plugins())
        }

        # Add plugin-specific data
        if plugin.name == "weather":
            screen_data['show_logo'] = True
            screen_data['logo_type'] = 'weather'
            weather_data = plugin_data.data
            screen_data['rates_data'] = {
                'city': weather_data.get('city', 'Unknown'),
                'temperature': weather_data.get('temperature', 0),
                'weather_description': weather_data.get('description', ''),
                'temp_min': weather_data.get('temp_min', 0),
                'temp_max': weather_data.get('temp_max', 0),
                'humidity': weather_data.get('humidity', 0),
                'wind_speed': weather_data.get('wind_speed', 0),
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }

        elif plugin.name == "currency":
            screen_data['rates_data'] = {
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
            # Add currency pairs
            for pair_data in plugin_data.data.get('pairs', []):
                pair = pair_data.get('pair', '')
                rate = pair_data.get('rate', 0)
                if pair:
                    screen_data['rates_data'][pair] = rate

        elif plugin.name == "crypto":
            screen_data['show_logo'] = True
            screen_data['logo_type'] = 'btc'
            screen_data['rates_data'] = {
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
            # Add crypto prices
            for coin in plugin_data.data.get('coins', []):
                symbol = coin.get('symbol', '')
                prices = coin.get('prices', {})
                for currency, price_data in prices.items():
                    key = f"{symbol}/{currency}"
                    screen_data['rates_data'][key] = price_data.get('value', 0)

        elif plugin.name == "clock":
            clock_data = plugin_data.data
            screen_data['rates_data'] = {
                'time': clock_data.get('time', 'N/A'),
                'date': clock_data.get('date', 'N/A'),
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }

        else:
            # Generic plugin data
            screen_data['rates_data'] = plugin_data.data

        return screen_data

    def _format_plugin_display(self, plugin, rates_data) -> Dict[str, Any]:
        """Format plugin data for display."""
        if plugin.name == "weather":
            # Return weather display format
            return {
                "left_lines": [
                    f"{rates_data.get('city', 'Unknown')}: {rates_data.get('temperature', 0)}°C",
                    f"{rates_data.get('weather_description', 'Unknown')}"
                ],
                "right_details": [
                    f"Range: {rates_data.get('temp_min', 0)}°C - {rates_data.get('temp_max', 0)}°C",
                    f"Humidity: {rates_data.get('humidity', 0)}%",
                    f"Wind: {rates_data.get('wind_speed', 0)}m/s"
                ]
            }

        else:
            # Default format for other plugins
            lines = []
            for key, value in rates_data.items():
                if key not in ['timestamp', 'base_currency'] and value is not None:
                    lines.append(f"{key}: {value}")
            return lines

    async def cleanup(self):
        """Cleanup resources."""
        self.running = False

        # Cleanup plugins
        await plugin_registry.cleanup_all()

        # Cleanup display
        if self.display_service:
            self.display_service.cleanup()

        self.logger.info("Display runner cleaned up")