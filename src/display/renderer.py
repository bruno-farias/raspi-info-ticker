"""E-ink optimized display renderer for Raspberry Pi Info Ticker.

Inspired by InkyPi's minimalist approach - focuses on crisp, paper-like visuals
with efficient rendering for e-paper displays.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

try:
    import cairosvg
    SVG_SUPPORT = True
except ImportError:
    SVG_SUPPORT = False

from ..plugins import plugin_registry, PluginData
from ..config import config_manager


class EInkRenderer:
    """Specialized renderer for e-ink/e-paper displays with optimizations."""

    # E-ink specific constants
    WHITE = 255
    BLACK = 0
    RED = 127  # For tri-color displays

    def __init__(self, width: int = 250, height: int = 122):
        """
        Initialize e-ink renderer.

        Args:
            width: Display width in pixels
            height: Display height in pixels
        """
        self.width = width
        self.height = height
        self.logger = logging.getLogger("eink_renderer")

        # Font management
        self.fonts = self._load_fonts()

        # Layout configurations for different plugin types
        self.layouts = {
            "clock": self._render_clock_layout,
            "weather": self._render_weather_layout,
            "currency": self._render_currency_layout,
            "crypto": self._render_crypto_layout,
            "calendar": self._render_calendar_layout,
            "news": self._render_news_layout,
            "custom": self._render_custom_layout
        }

        # Display state for optimization
        self.last_render = None
        self.render_count = 0

    def _load_fonts(self) -> Dict[str, ImageFont.FreeTypeFont]:
        """Load optimized fonts for e-ink display."""
        fonts = {}
        font_dir = Path(__file__).parent.parent.parent / "assets" / "fonts"

        # Default font sizes optimized for e-ink clarity
        sizes = {
            "tiny": 10,
            "small": 12,
            "medium": 14,
            "large": 18,
            "huge": 24,
            "title": 28
        }

        # Try to load custom fonts, fallback to defaults
        try:
            font_path = font_dir / "DejaVuSans.ttf"
            if not font_path.exists():
                # Fallback to system font
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

            for name, size in sizes.items():
                fonts[name] = ImageFont.truetype(str(font_path), size)

            # Bold variant for headers
            bold_path = font_dir / "DejaVuSans-Bold.ttf"
            if not bold_path.exists():
                bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

            fonts["header"] = ImageFont.truetype(str(bold_path), 20)

        except Exception as e:
            self.logger.warning(f"Failed to load custom fonts: {e}")
            # Fallback to default font
            for name in sizes:
                fonts[name] = ImageFont.load_default()

        return fonts

    def _load_weather_icon(self, icon_code: str) -> Optional[Image.Image]:
        """
        Load weather icon from assets/weather directory.

        Args:
            icon_code: OpenWeatherMap icon code (e.g., "01d", "10n")

        Returns:
            PIL Image of the weather icon, or None if not found
        """
        icon_dir = Path(__file__).parent.parent.parent / "assets" / "weather"
        icon_path = icon_dir / f"{icon_code}@2x.svg"

        if not icon_path.exists():
            self.logger.warning(f"Weather icon not found: {icon_path}")
            return None

        try:
            if SVG_SUPPORT:
                # Convert SVG to PNG in memory with white background
                import io
                png_data = cairosvg.svg2png(url=str(icon_path), background_color='white')
                icon_image = Image.open(io.BytesIO(png_data))
            else:
                self.logger.warning("cairosvg not available, skipping weather icon")
                return None

            # Convert to grayscale for e-ink
            icon_image = icon_image.convert('L')

            # Apply threshold to make it pure black and white
            # Dark pixels (< threshold) become black (0), light pixels become white (255)
            threshold = 128
            icon_image = icon_image.point(lambda x: 0 if x < threshold else 255, mode='1')

            return icon_image

        except Exception as e:
            self.logger.error(f"Error loading weather icon {icon_code}: {e}")
            return None

    def render_plugin(self, plugin_data: PluginData) -> Image.Image:
        """
        Render plugin data optimized for e-ink display.

        Args:
            plugin_data: Plugin data to render

        Returns:
            PIL Image optimized for e-ink
        """
        # Create base image (1-bit for monochrome e-ink)
        image = Image.new('1', (self.width, self.height), self.WHITE)
        draw = ImageDraw.Draw(image)

        # Get appropriate layout renderer
        plugin_name = plugin_data.plugin_name
        layout_func = self.layouts.get(plugin_name, self._render_custom_layout)

        # Render with error handling
        try:
            layout_func(draw, plugin_data)
        except Exception as e:
            self.logger.error(f"Error rendering {plugin_name}: {e}")
            self._render_error(draw, plugin_name, str(e))

        # Apply e-ink optimizations
        image = self._optimize_for_eink(image)

        self.render_count += 1
        self.last_render = datetime.now()

        return image

    def render_composite(self, plugins_data: List[PluginData],
                        layout: str = "grid") -> Image.Image:
        """
        Render multiple plugins in a composite layout.

        Args:
            plugins_data: List of plugin data to render
            layout: Layout type (grid, list, dashboard)

        Returns:
            Composite image for e-ink display
        """
        image = Image.new('1', (self.width, self.height), self.WHITE)
        draw = ImageDraw.Draw(image)

        if layout == "grid":
            self._render_grid_layout(draw, plugins_data)
        elif layout == "list":
            self._render_list_layout(draw, plugins_data)
        elif layout == "dashboard":
            self._render_dashboard_layout(draw, plugins_data)
        else:
            self._render_list_layout(draw, plugins_data)

        return self._optimize_for_eink(image)

    def _render_clock_layout(self, draw: ImageDraw.Draw, data: PluginData):
        """Render minimalist clock layout."""
        clock_data = data.data

        # Large time display (centered)
        time_str = clock_data.get("time", "00:00")
        font = self.fonts["title"]

        # Calculate center position
        bbox = draw.textbbox((0, 0), time_str, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2 - 10

        draw.text((x, y), time_str, font=font, fill=self.BLACK)

        # Date below (smaller, centered)
        if clock_data.get("date"):
            date_str = clock_data["date"]
            if clock_data.get("day_name"):
                date_str = f"{clock_data['day_name']}, {date_str}"

            font = self.fonts["medium"]
            bbox = draw.textbbox((0, 0), date_str, font=font)
            text_width = bbox[2] - bbox[0]

            x = (self.width - text_width) // 2
            y = y + text_height + 10

            draw.text((x, y), date_str, font=font, fill=self.BLACK)

    def _render_weather_layout(self, draw: ImageDraw.Draw, data: PluginData):
        """Render clean weather layout inspired by InkyPi."""
        weather = data.data

        # City name (top left)
        city = f"{weather.get('city', 'Unknown')}"
        draw.text((10, 5), city, font=self.fonts["header"], fill=self.BLACK)

        # Weather icon (top right)
        icon_code = weather.get("icon", "01d")
        weather_icon = self._load_weather_icon(icon_code)
        if weather_icon:
            # Scale icon to fit nicely (40x40 pixels)
            icon_size = 40
            weather_icon = weather_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            # Position in top right
            icon_x = self.width - icon_size - 10
            icon_y = 5
            # Draw the icon pixel by pixel (for 1-bit compatibility)
            image = draw.im
            for x in range(icon_size):
                for y in range(icon_size):
                    pixel = weather_icon.getpixel((x, y))
                    if pixel == 0:  # Black pixel
                        image.putpixel((icon_x + x, icon_y + y), 0)

        # Temperature (large, prominent)
        temp = weather.get("temperature", 0)
        unit = "°C" if weather.get("units") == "metric" else "°F"
        temp_str = f"{temp:.0f}{unit}"

        draw.text((10, 30), temp_str, font=self.fonts["huge"], fill=self.BLACK)

        # Weather description
        desc = weather.get("description", "")
        if desc:
            draw.text((10, 65), desc, font=self.fonts["medium"], fill=self.BLACK)

        # Additional details (right side, below icon)
        details_x = self.width - 90
        details_y = 55

        # Min/Max temps
        temp_min = weather.get("temp_min", 0)
        temp_max = weather.get("temp_max", 0)
        draw.text((details_x, details_y), f"↓{temp_min:.0f}° ↑{temp_max:.0f}°",
                 font=self.fonts["small"], fill=self.BLACK)

        # Humidity
        humidity = weather.get("humidity", 0)
        draw.text((details_x, details_y + 15), f"💧 {humidity}%",
                 font=self.fonts["small"], fill=self.BLACK)

        # Wind
        wind = weather.get("wind_speed", 0)
        draw.text((details_x, details_y + 30), f"🌬 {wind}m/s",
                 font=self.fonts["small"], fill=self.BLACK)

    def _render_currency_layout(self, draw: ImageDraw.Draw, data: PluginData):
        """Render clean currency display."""
        currency_data = data.data

        # Title
        draw.text((10, 5), "Exchange Rates", font=self.fonts["header"], fill=self.BLACK)

        # Base currency
        base = currency_data.get("base_currency", "USD")
        draw.text((10, 28), f"Base: {base}", font=self.fonts["small"], fill=self.BLACK)

        # Rates in a clean table format
        y_offset = 45
        pairs = currency_data.get("pairs", [])

        for i, pair_data in enumerate(pairs[:4]):  # Limit to 4 for space
            pair = pair_data.get("pair", "")
            rate = pair_data.get("rate", 0)

            # Currency pair
            draw.text((10, y_offset), pair, font=self.fonts["medium"], fill=self.BLACK)

            # Rate (right-aligned)
            rate_str = f"{rate:.4f}"
            bbox = draw.textbbox((0, 0), rate_str, font=self.fonts["medium"])
            text_width = bbox[2] - bbox[0]
            draw.text((self.width - text_width - 50, y_offset), rate_str,
                     font=self.fonts["medium"], fill=self.BLACK)

            # Change indicator (if available)
            if "change_indicator" in pair_data:
                change = pair_data["change_indicator"]
                draw.text((self.width - 40, y_offset), change,
                         font=self.fonts["small"], fill=self.BLACK)

            y_offset += 18

    def _render_crypto_layout(self, draw: ImageDraw.Draw, data: PluginData):
        """Render cryptocurrency prices."""
        crypto_data = data.data

        # Title
        draw.text((10, 5), "Crypto Prices", font=self.fonts["header"], fill=self.BLACK)

        # Coins
        y_offset = 30
        coins = crypto_data.get("coins", [])

        for coin in coins[:3]:  # Limit display
            name = coin.get("symbol", "").upper()
            prices = coin.get("prices", {})

            # Coin name
            draw.text((10, y_offset), name, font=self.fonts["medium"], fill=self.BLACK)

            # USD price (if available)
            if "USD" in prices:
                price_info = prices["USD"]
                price_str = price_info.get("formatted", "N/A")
                draw.text((60, y_offset), price_str, font=self.fonts["medium"], fill=self.BLACK)

                # Change indicator
                change = price_info.get("change_24h_formatted", "")
                if change:
                    draw.text((160, y_offset), change, font=self.fonts["small"], fill=self.BLACK)

            y_offset += 25

    def _render_calendar_layout(self, draw: ImageDraw.Draw, data: PluginData):
        """Render calendar/agenda layout (future feature)."""
        # Placeholder for calendar rendering
        draw.text((10, 10), "Calendar", font=self.fonts["header"], fill=self.BLACK)
        draw.text((10, 40), "No events today", font=self.fonts["medium"], fill=self.BLACK)

    def _render_news_layout(self, draw: ImageDraw.Draw, data: PluginData):
        """Render news headlines (future feature)."""
        # Placeholder for news rendering
        draw.text((10, 10), "News", font=self.fonts["header"], fill=self.BLACK)
        draw.text((10, 40), "No headlines available", font=self.fonts["medium"], fill=self.BLACK)

    def _render_custom_layout(self, draw: ImageDraw.Draw, data: PluginData):
        """Render custom plugin data."""
        # Generic rendering for unknown plugins
        draw.text((10, 10), data.title, font=self.fonts["header"], fill=self.BLACK)

        y_offset = 35
        for key, value in data.data.items():
            if y_offset > self.height - 20:
                break

            text = f"{key}: {value}"
            draw.text((10, y_offset), text, font=self.fonts["small"], fill=self.BLACK)
            y_offset += 15

    def _render_grid_layout(self, draw: ImageDraw.Draw, plugins_data: List[PluginData]):
        """Render plugins in a grid layout."""
        # 2x2 grid for small displays
        grid_w = self.width // 2
        grid_h = self.height // 2

        positions = [
            (0, 0), (grid_w, 0),
            (0, grid_h), (grid_w, grid_h)
        ]

        for i, plugin_data in enumerate(plugins_data[:4]):
            if i >= len(positions):
                break

            x, y = positions[i]

            # Draw border
            draw.rectangle([x, y, x + grid_w - 1, y + grid_h - 1],
                          outline=self.BLACK, width=1)

            # Render mini version of plugin
            self._render_mini_plugin(draw, plugin_data, x + 2, y + 2,
                                    grid_w - 4, grid_h - 4)

    def _render_list_layout(self, draw: ImageDraw.Draw, plugins_data: List[PluginData]):
        """Render plugins in a vertical list."""
        y_offset = 5
        item_height = self.height // min(4, len(plugins_data))

        for plugin_data in plugins_data[:4]:
            # Divider line
            if y_offset > 5:
                draw.line([(5, y_offset), (self.width - 5, y_offset)],
                         fill=self.BLACK, width=1)

            # Plugin content
            self._render_mini_plugin(draw, plugin_data, 10, y_offset + 2,
                                    self.width - 20, item_height - 4)

            y_offset += item_height

    def _render_dashboard_layout(self, draw: ImageDraw.Draw, plugins_data: List[PluginData]):
        """Render a dashboard with prioritized layout."""
        if not plugins_data:
            return

        # First plugin gets top half (priority)
        main_plugin = plugins_data[0]
        self._render_mini_plugin(draw, main_plugin, 5, 5,
                                self.width - 10, self.height // 2 - 10)

        # Remaining plugins share bottom half
        if len(plugins_data) > 1:
            draw.line([(5, self.height // 2), (self.width - 5, self.height // 2)],
                     fill=self.BLACK, width=1)

            bottom_width = (self.width - 10) // min(3, len(plugins_data) - 1)
            for i, plugin_data in enumerate(plugins_data[1:4]):
                x = 5 + (i * bottom_width)
                self._render_mini_plugin(draw, plugin_data, x, self.height // 2 + 5,
                                        bottom_width - 2, self.height // 2 - 10)

    def _render_mini_plugin(self, draw: ImageDraw.Draw, plugin_data: PluginData,
                           x: int, y: int, width: int, height: int):
        """Render a miniature version of a plugin."""
        # Title
        draw.text((x, y), plugin_data.title[:15], font=self.fonts["small"], fill=self.BLACK)

        # Key info only
        y_offset = y + 15

        if plugin_data.plugin_name == "clock":
            time_str = plugin_data.data.get("time", "")
            draw.text((x, y_offset), time_str, font=self.fonts["medium"], fill=self.BLACK)

        elif plugin_data.plugin_name == "weather":
            temp = plugin_data.data.get("temperature", 0)
            unit = "°C" if plugin_data.data.get("units") == "metric" else "°F"
            draw.text((x, y_offset), f"{temp:.0f}{unit}", font=self.fonts["medium"], fill=self.BLACK)

        elif plugin_data.plugin_name == "currency":
            pairs = plugin_data.data.get("pairs", [])
            if pairs:
                first_pair = pairs[0]
                text = f"{first_pair.get('pair', '')}: {first_pair.get('rate', 0):.2f}"
                draw.text((x, y_offset), text, font=self.fonts["tiny"], fill=self.BLACK)

        else:
            # Generic: show first data item
            for key, value in list(plugin_data.data.items())[:1]:
                text = f"{value}"[:width // 6]  # Rough character limit
                draw.text((x, y_offset), text, font=self.fonts["tiny"], fill=self.BLACK)

    def _render_error(self, draw: ImageDraw.Draw, plugin_name: str, error: str):
        """Render error message."""
        draw.text((10, 10), f"Error: {plugin_name}", font=self.fonts["header"], fill=self.BLACK)
        draw.text((10, 35), error[:100], font=self.fonts["small"], fill=self.BLACK)

    def _optimize_for_eink(self, image: Image.Image) -> Image.Image:
        """
        Apply e-ink specific optimizations.

        Args:
            image: Source image

        Returns:
            Optimized image for e-ink display
        """
        # Ensure pure black and white (no grays)
        if image.mode != '1':
            # Convert to grayscale first if needed
            if image.mode != 'L':
                image = image.convert('L')

            # Apply threshold to create pure B&W
            threshold = 128
            image = image.point(lambda p: 255 if p > threshold else 0, mode='1')

        # Could add dithering here if needed for photos
        # But for info display, clean B&W is better

        return image

    def create_splash_screen(self, message: str = "Raspi Info Ticker") -> Image.Image:
        """Create a splash screen for startup."""
        image = Image.new('1', (self.width, self.height), self.WHITE)
        draw = ImageDraw.Draw(image)

        # Center the message
        font = self.fonts["large"]
        bbox = draw.textbbox((0, 0), message, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2

        draw.text((x, y), message, font=font, fill=self.BLACK)

        # Version info
        version = "v2.0"
        font = self.fonts["small"]
        bbox = draw.textbbox((0, 0), version, font=font)
        text_width = bbox[2] - bbox[0]

        x = (self.width - text_width) // 2
        y = self.height - 20

        draw.text((x, y), version, font=font, fill=self.BLACK)

        return image

    def create_status_screen(self, status: Dict[str, Any]) -> Image.Image:
        """Create a status/diagnostic screen."""
        image = Image.new('1', (self.width, self.height), self.WHITE)
        draw = ImageDraw.Draw(image)

        draw.text((10, 5), "System Status", font=self.fonts["header"], fill=self.BLACK)

        y_offset = 30

        # Show key status items
        items = [
            f"Plugins: {status.get('plugin_count', 0)} active",
            f"Uptime: {status.get('uptime', 'Unknown')}",
            f"Memory: {status.get('memory_usage', 'Unknown')}",
            f"Temp: {status.get('temperature', 'Unknown')}",
            f"Network: {status.get('network', 'Unknown')}",
            f"Renders: {self.render_count}"
        ]

        for item in items:
            draw.text((10, y_offset), item, font=self.fonts["small"], fill=self.BLACK)
            y_offset += 15

        return image